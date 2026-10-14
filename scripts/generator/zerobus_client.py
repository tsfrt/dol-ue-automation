"""Multi-table Zerobus Ingest client wrapper.

Manages one gRPC stream per target table, with retry and reconnection.
In dry-run mode, prints events to stdout instead of sending to Zerobus.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

import generator.config as cfg

logger = logging.getLogger(__name__)


class DryRunStream:
    """Stub that logs records instead of sending them."""

    def __init__(self, table_name: str):
        self.table_name = table_name
        self.count = 0

    def send(self, record: dict) -> None:
        self.count += 1
        if self.count <= 3:
            logger.info("[dry-run] %s record %d: %s", self.table_name, self.count, record)
        elif self.count == 4:
            logger.info("[dry-run] %s: suppressing further sample output...", self.table_name)

    def send_batch(self, records: list[dict]) -> None:
        for r in records:
            self.send(r)

    def flush(self) -> None:
        pass

    def close(self) -> None:
        logger.info("[dry-run] %s: %d records total", self.table_name, self.count)


class ZerobusStream:
    """Wraps one Zerobus SDK stream to a single table."""

    def __init__(
        self,
        table_name: str,
        server_endpoint: str,
        workspace_url: str,
        client_id: str,
        client_secret: str,
    ):
        from zerobus.sdk.sync import ZerobusSdk
        from zerobus.sdk.shared import RecordType, StreamConfigurationOptions, TableProperties

        self.table_name = table_name
        self.server_endpoint = server_endpoint
        self.workspace_url = workspace_url
        self.client_id = client_id
        self.client_secret = client_secret

        self.sdk = ZerobusSdk(server_endpoint, workspace_url)
        options = StreamConfigurationOptions(record_type=RecordType.JSON)
        table_props = TableProperties(table_name)
        self.stream = self.sdk.create_stream(client_id, client_secret, table_props, options)
        self.count = 0
        self._batch_count = 0

    def send(self, record: dict, max_retries: int = 3) -> bool:
        for attempt in range(max_retries):
            try:
                self.stream.ingest_record_nowait(record)
                self.count += 1
                self._batch_count += 1
                if self._batch_count >= 100:
                    self.stream.flush()
                    self._batch_count = 0
                return True
            except Exception as e:
                logger.warning("Send to %s attempt %d/%d failed: %s", self.table_name, attempt + 1, max_retries, e)
                err = str(e).lower()
                if "closed" in err or "connection" in err:
                    self._reconnect()
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
        return False

    def send_batch(self, records: list[dict]) -> None:
        for r in records:
            self.send(r)

    def flush(self) -> None:
        if self.stream and self._batch_count > 0:
            self.stream.flush()
            self._batch_count = 0

    def close(self) -> None:
        if self.stream:
            self.flush()
            self.stream.close()
            self.stream = None
        logger.info("Closed stream to %s: %d records sent", self.table_name, self.count)

    def _reconnect(self) -> None:
        from zerobus.sdk.shared import RecordType, StreamConfigurationOptions, TableProperties

        try:
            if self.stream:
                self.stream.close()
        except Exception:
            pass
        options = StreamConfigurationOptions(record_type=RecordType.JSON)
        table_props = TableProperties(self.table_name)
        self.stream = self.sdk.create_stream(self.client_id, self.client_secret, table_props, options)
        self._batch_count = 0
        logger.info("Reconnected stream to %s", self.table_name)


class MultiTableClient:
    """Manages one stream per table.  Supports dry-run mode."""

    def __init__(self, table_names: list[str], dry_run: bool = False):
        self.dry_run = dry_run
        self.streams: dict[str, DryRunStream | ZerobusStream] = {}

        for table in table_names:
            full_name = cfg.fqn(table)
            if dry_run:
                self.streams[table] = DryRunStream(full_name)
            else:
                self.streams[table] = ZerobusStream(
                    table_name=full_name,
                    server_endpoint=cfg.ZEROBUS_SERVER_ENDPOINT,
                    workspace_url=cfg.DATABRICKS_WORKSPACE_URL,
                    client_id=cfg.DATABRICKS_CLIENT_ID,
                    client_secret=cfg.DATABRICKS_CLIENT_SECRET,
                )

    def send(self, table: str, record: dict) -> None:
        stream = self.streams.get(table)
        if stream:
            stream.send(record)

    def send_batch(self, table: str, records: list[dict]) -> None:
        stream = self.streams.get(table)
        if stream:
            stream.send_batch(records)

    def flush_all(self) -> None:
        for stream in self.streams.values():
            stream.flush()

    def close_all(self) -> None:
        for stream in self.streams.values():
            stream.close()

    def summary(self) -> dict[str, int]:
        return {table: s.count for table, s in self.streams.items()}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_all()
        return False
