"""Entry point: generates one compressed week of UI events and sends to Zerobus.

Usage (dry-run, no Zerobus needed):
    python -m scripts.generator.main --dry-run

Usage (live):
    Set env vars: ZEROBUS_SERVER_ENDPOINT, DATABRICKS_WORKSPACE_URL,
                  DATABRICKS_CLIENT_ID, DATABRICKS_CLIENT_SECRET
    python -m scripts.generator.main --catalog dol_ue_demo --schema bronze
"""

from __future__ import annotations

import argparse
import logging
import os
import random
import time
from datetime import datetime, timedelta, timezone

from generator.config import (
    ALL_TABLES,
    CATALOG,
    CLAIMANTS_PER_STATE,
    EMPLOYERS_PER_STATE,
    FRAUD_RATE,
    NEW_CLAIMS_PER_STATE_PER_WEEK,
    SCHEMA,
    SIM_WEEK_DURATION_SECS,
    TABLE_ACCOUNT_CHANGES,
    TABLE_EMPLOYER_RESPONSES,
    TABLE_EXT_ACH_RETURNS,
    TABLE_EXT_BANK_VERIFICATION,
    TABLE_EXT_DEATH_RECORDS,
    TABLE_EXT_HUB_SIGNALS,
    TABLE_EXT_INCARCERATION,
    TABLE_EXT_NEW_HIRES,
    TABLE_EXT_OTHER_BENEFITS,
    TABLE_INITIAL_CLAIMS,
    TABLE_PAYMENTS,
    TABLE_WEEKLY_CERTS,
)
from generator.events import (
    generate_employer_responses,
    generate_ext_ach_returns,
    generate_ext_bank_verification,
    generate_ext_death_records,
    generate_ext_hub_signals,
    generate_ext_incarceration,
    generate_ext_new_hires,
    generate_ext_other_benefits,
    generate_initial_claims,
    generate_payments,
    generate_weekly_certifications,
)
from generator.population import generate_population
from generator.profiles import STATE_CODES
from generator.scenarios import ScenarioMixer
from generator.zerobus_client import MultiTableClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="UI Claims Synthetic Data Generator")
    p.add_argument("--catalog", default=os.environ.get("DOL_CATALOG", CATALOG))
    p.add_argument("--schema", default=os.environ.get("DOL_SCHEMA", SCHEMA))
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--fraud-rate", type=float, default=FRAUD_RATE)
    p.add_argument("--sim-duration", type=int, default=SIM_WEEK_DURATION_SECS,
                    help="Wall-clock seconds for one simulated week")
    p.add_argument("--claimants-per-state", type=int, default=CLAIMANTS_PER_STATE)
    p.add_argument("--employers-per-state", type=int, default=EMPLOYERS_PER_STATE)
    p.add_argument("--new-claims-per-state", type=int, default=NEW_CLAIMS_PER_STATE_PER_WEEK)
    p.add_argument("--dry-run", action="store_true",
                    help="Print events to stdout instead of sending to Zerobus")
    p.add_argument("--zerobus-endpoint", default=os.environ.get("ZEROBUS_SERVER_ENDPOINT", ""))
    p.add_argument("--workspace-url", default=os.environ.get("DATABRICKS_WORKSPACE_URL", ""))
    p.add_argument("--client-id", default=os.environ.get("DATABRICKS_CLIENT_ID", ""))
    p.add_argument("--client-secret", default=os.environ.get("DATABRICKS_CLIENT_SECRET", ""))
    p.add_argument("--secret-scope", default="", help="Databricks secret scope to read credentials from")
    return p.parse_args()


def _sleep_phase(phase_name: str, phase_fraction: float, total_duration: int) -> None:
    secs = total_duration * phase_fraction
    if secs > 0:
        logger.info("Phase '%s' complete — sleeping %.1fs to simulate passage of time", phase_name, secs)
        time.sleep(secs)


def run(args: argparse.Namespace) -> None:
    # Override config module globals so fqn() picks up CLI args
    import generator.config as cfg
    cfg.CATALOG = args.catalog
    cfg.SCHEMA = args.schema

    if args.secret_scope and not args.client_secret:
        scope = args.secret_scope
        logger.info("Reading client secret from Databricks secret scope: %s", scope)
        try:
            from pyspark.dbutils import DBUtils
            from pyspark.sql import SparkSession
            spark = SparkSession.builder.getOrCreate()
            dbutils = DBUtils(spark)
            args.client_secret = dbutils.secrets.get(scope, "zerobus-client-secret")
        except Exception as e:
            logger.warning("pyspark.dbutils failed (%s), trying databricks-sdk", e)
            from databricks.sdk import WorkspaceClient
            w = WorkspaceClient()
            resp = w.secrets.get_secret(scope, "zerobus-client-secret")
            args.client_secret = resp.value

    if args.zerobus_endpoint:
        cfg.ZEROBUS_SERVER_ENDPOINT = args.zerobus_endpoint
    if args.workspace_url:
        cfg.DATABRICKS_WORKSPACE_URL = args.workspace_url
    if args.client_id:
        cfg.DATABRICKS_CLIENT_ID = args.client_id
    if args.client_secret:
        cfg.DATABRICKS_CLIENT_SECRET = args.client_secret

    rng = random.Random(args.seed)
    now = datetime.now(timezone.utc)
    week_start = now - timedelta(days=7)
    week_ending = now

    logger.info("=== UI Claims Generator ===")
    logger.info("Catalog: %s.%s", args.catalog, args.schema)
    logger.info("Seed: %d | Fraud rate: %.2f | Sim duration: %ds", args.seed, args.fraud_rate, args.sim_duration)
    logger.info("States: %s", ", ".join(STATE_CODES))
    logger.info("Dry run: %s", args.dry_run)

    # 1. Generate seed population
    logger.info("--- Phase 0: Generating seed population ---")
    pop = generate_population(
        seed=args.seed,
        employers_per_state=args.employers_per_state,
        claimants_per_state=args.claimants_per_state,
        sim_date=now,
    )
    logger.info("Population: %d employers, %d claimants, %d wage records",
                len(pop.employers), len(pop.claimants), len(pop.wage_records))

    mixer = ScenarioMixer(fraud_rate=args.fraud_rate, seed=args.seed + 1)

    logger.info("Zerobus endpoint: %s", cfg.ZEROBUS_SERVER_ENDPOINT)
    logger.info("Workspace URL: %s", cfg.DATABRICKS_WORKSPACE_URL)
    logger.info("Client ID: %s", cfg.DATABRICKS_CLIENT_ID)
    logger.info("Client secret set: %s", bool(cfg.DATABRICKS_CLIENT_SECRET))

    with MultiTableClient(ALL_TABLES, dry_run=args.dry_run) as client:

        # 2. Initial claims
        logger.info("--- Phase 1: Initial Claims ---")
        all_claims: list = []
        for state in STATE_CODES:
            claims = generate_initial_claims(
                pop, state, week_start, args.new_claims_per_state, mixer, rng,
            )
            for c in claims:
                client.send(TABLE_INITIAL_CLAIMS, c.to_dict())
            all_claims.extend(claims)
        client.flush_all()
        logger.info("Sent %d initial claims", len(all_claims))

        _sleep_phase("initial_claims", 0.15, args.sim_duration)

        # 3. Employer responses
        logger.info("--- Phase 2: Employer Responses ---")
        responses = generate_employer_responses(all_claims, pop, week_start, rng)
        for r in responses:
            client.send(TABLE_EMPLOYER_RESPONSES, r.to_dict())
        client.flush_all()
        logger.info("Sent %d employer responses", len(responses))

        _sleep_phase("employer_responses", 0.10, args.sim_duration)

        # 4. Weekly certifications
        logger.info("--- Phase 3: Weekly Certifications ---")
        active_claims = [(c.claim_id, c.claimant_id, c.source_state) for c in all_claims]
        # Also add some "previously active" claims from the broader population
        for state in STATE_CODES:
            existing = pop.state_claimants[state][args.new_claims_per_state:]
            for cid in existing[:int(len(existing) * 0.6)]:
                claim_id = f"IC-{state}-PREV-{cid[-5:]}"
                active_claims.append((claim_id, cid, state))

        certs = generate_weekly_certifications(active_claims, week_ending, pop, mixer, rng)
        for cert in certs:
            client.send(TABLE_WEEKLY_CERTS, cert.to_dict())
        client.flush_all()
        logger.info("Sent %d weekly certifications", len(certs))

        _sleep_phase("certifications", 0.20, args.sim_duration)

        # 5. Payments
        logger.info("--- Phase 4: Payments ---")
        payments, account_changes = generate_payments(certs, pop, rng, mixer)
        for p in payments:
            client.send(TABLE_PAYMENTS, p.to_dict())
        for ac in account_changes:
            client.send(TABLE_ACCOUNT_CHANGES, ac.to_dict())
        client.flush_all()
        logger.info("Sent %d payments, %d account changes", len(payments), len(account_changes))

        _sleep_phase("payments", 0.15, args.sim_duration)

        # 6. External feeds
        logger.info("--- Phase 5: External Feeds ---")

        new_hires = generate_ext_new_hires(pop, week_start, rng)
        for nh in new_hires:
            client.send(TABLE_EXT_NEW_HIRES, nh.to_dict())

        death_records = generate_ext_death_records(pop, rng)
        for dr in death_records:
            client.send(TABLE_EXT_DEATH_RECORDS, dr.to_dict())

        incarceration_records = generate_ext_incarceration(pop, rng)
        for ir in incarceration_records:
            client.send(TABLE_EXT_INCARCERATION, ir.to_dict())

        other_benefits = generate_ext_other_benefits(pop, rng, week_start)
        for ob in other_benefits:
            client.send(TABLE_EXT_OTHER_BENEFITS, ob.to_dict())

        hub_signals = generate_ext_hub_signals(all_claims, rng)
        for hs in hub_signals:
            client.send(TABLE_EXT_HUB_SIGNALS, hs.to_dict())

        bank_verifications = generate_ext_bank_verification(payments, pop, rng)
        for bv in bank_verifications:
            client.send(TABLE_EXT_BANK_VERIFICATION, bv.to_dict())

        ach_returns = generate_ext_ach_returns(payments, rng)
        for ar in ach_returns:
            client.send(TABLE_EXT_ACH_RETURNS, ar.to_dict())

        client.flush_all()
        logger.info("External feeds: %d new hires, %d deaths, %d incarceration, %d other benefits, "
                     "%d hub signals, %d bank verifications, %d ACH returns",
                     len(new_hires), len(death_records), len(incarceration_records),
                     len(other_benefits), len(hub_signals), len(bank_verifications), len(ach_returns))

        _sleep_phase("external_feeds", 0.10, args.sim_duration)

        # Summary
        logger.info("=== Generation Complete ===")
        logger.info("Table counts: %s", client.summary())
        logger.info("Fraud scenario mix: %s", mixer.summary())


def main() -> None:
    args = parse_args()
    run(args)


if __name__ == "__main__":
    main()
