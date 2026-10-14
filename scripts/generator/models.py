"""Event dataclasses for every bronze table.

Each model has a .to_dict() that returns a JSON-safe dict ready for Zerobus.
Timestamps are emitted as epoch microseconds (Delta TIMESTAMP convention).
Ground-truth labels are serialized into a single _ground_truth JSON string.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional


def _ts(dt: datetime) -> int:
    """Convert datetime to epoch microseconds."""
    return int(dt.timestamp() * 1_000_000)


def _now_us() -> int:
    return _ts(datetime.now(timezone.utc))


@dataclass
class GroundTruth:
    is_fraud: bool = False
    is_improper: bool = False
    fraud_scenario: str = ""
    bam_action_code: int = 0  # 0=correct, 10=fraud, 11=nonfraud recoverable, 12=nonfraud nonrecoverable
    root_cause: str = ""
    responsible_party: str = ""  # claimant, employer, agency

    def to_json(self) -> str:
        return json.dumps(asdict(self))


@dataclass
class InitialClaim:
    claim_id: str
    claimant_id: str
    source_state: str
    filed_ts: datetime
    channel: str = "online"
    ip_address: str = ""
    geo_country: str = "US"
    geo_region: str = ""
    device_id: str = ""
    form_fill_secs: int = 0
    separation_reason: str = ""
    last_employer_id: str = ""
    ssn_hash: str = ""
    bank_hash: str = ""
    payment_method: str = "direct_deposit"
    id_check_result: str = "pass"
    email_domain: str = ""
    phone_hash: str = ""
    address_hash: str = ""
    ground_truth: GroundTruth = field(default_factory=GroundTruth)

    def to_dict(self) -> dict:
        return {
            "claim_id": self.claim_id,
            "claimant_id": self.claimant_id,
            "source_state": self.source_state,
            "filed_ts": _ts(self.filed_ts),
            "channel": self.channel,
            "ip_address": self.ip_address,
            "geo_country": self.geo_country,
            "geo_region": self.geo_region,
            "device_id": self.device_id,
            "form_fill_secs": self.form_fill_secs,
            "separation_reason": self.separation_reason,
            "last_employer_id": self.last_employer_id,
            "ssn_hash": self.ssn_hash,
            "bank_hash": self.bank_hash,
            "payment_method": self.payment_method,
            "id_check_result": self.id_check_result,
            "email_domain": self.email_domain,
            "phone_hash": self.phone_hash,
            "address_hash": self.address_hash,
            "_ground_truth": self.ground_truth.to_json(),
            "_ingested_ts": _now_us(),
        }


@dataclass
class EmployerResponse:
    response_id: str
    claim_id: str
    employer_id: str
    source_state: str
    response_ts: datetime
    separation_reason_employer: str = ""
    narrative: str = ""
    ground_truth: GroundTruth = field(default_factory=GroundTruth)

    def to_dict(self) -> dict:
        return {
            "response_id": self.response_id,
            "claim_id": self.claim_id,
            "employer_id": self.employer_id,
            "source_state": self.source_state,
            "response_ts": _ts(self.response_ts),
            "separation_reason_employer": self.separation_reason_employer,
            "narrative": self.narrative,
            "_ground_truth": self.ground_truth.to_json(),
            "_ingested_ts": _now_us(),
        }


@dataclass
class WeeklyCertification:
    cert_id: str
    claim_id: str
    claimant_id: str
    source_state: str
    week_ending: datetime
    earnings_reported: float = 0.0
    hours_worked: int = 0
    work_search_contacts: str = "[]"  # JSON array
    able_available: bool = True
    refused_work: bool = False
    ip_address: str = ""
    device_id: str = ""
    ground_truth: GroundTruth = field(default_factory=GroundTruth)

    def to_dict(self) -> dict:
        return {
            "cert_id": self.cert_id,
            "claim_id": self.claim_id,
            "claimant_id": self.claimant_id,
            "source_state": self.source_state,
            "week_ending": _ts(self.week_ending),
            "earnings_reported": self.earnings_reported,
            "hours_worked": self.hours_worked,
            "work_search_contacts": self.work_search_contacts,
            "able_available": self.able_available,
            "refused_work": self.refused_work,
            "ip_address": self.ip_address,
            "device_id": self.device_id,
            "_ground_truth": self.ground_truth.to_json(),
            "_ingested_ts": _now_us(),
        }


@dataclass
class Payment:
    payment_id: str
    claim_id: str
    claimant_id: str
    source_state: str
    week_ending: datetime
    amount: float = 0.0
    method: str = "direct_deposit"
    bank_hash: str = ""
    issued_ts: Optional[datetime] = None
    status: str = "released"
    ground_truth: GroundTruth = field(default_factory=GroundTruth)

    def to_dict(self) -> dict:
        return {
            "payment_id": self.payment_id,
            "claim_id": self.claim_id,
            "claimant_id": self.claimant_id,
            "source_state": self.source_state,
            "week_ending": _ts(self.week_ending),
            "amount": self.amount,
            "method": self.method,
            "bank_hash": self.bank_hash,
            "issued_ts": _ts(self.issued_ts) if self.issued_ts else _now_us(),
            "status": self.status,
            "_ground_truth": self.ground_truth.to_json(),
            "_ingested_ts": _now_us(),
        }


@dataclass
class AccountChange:
    change_id: str
    claim_id: str
    claimant_id: str
    source_state: str
    change_type: str  # bank, email, phone, password
    change_ts: datetime
    device_id: str = ""
    ground_truth: GroundTruth = field(default_factory=GroundTruth)

    def to_dict(self) -> dict:
        return {
            "change_id": self.change_id,
            "claim_id": self.claim_id,
            "claimant_id": self.claimant_id,
            "source_state": self.source_state,
            "change_type": self.change_type,
            "change_ts": _ts(self.change_ts),
            "device_id": self.device_id,
            "_ground_truth": self.ground_truth.to_json(),
            "_ingested_ts": _now_us(),
        }


@dataclass
class NewHireRecord:
    record_id: str
    ssn_hash: str
    employer_id: str
    employer_state: str
    hire_date: datetime
    report_ts: datetime

    def to_dict(self) -> dict:
        return {
            "record_id": self.record_id,
            "ssn_hash": self.ssn_hash,
            "employer_id": self.employer_id,
            "employer_state": self.employer_state,
            "hire_date": _ts(self.hire_date),
            "report_ts": _ts(self.report_ts),
            "_ingested_ts": _now_us(),
        }


@dataclass
class DeathRecord:
    record_id: str
    ssn_hash: str
    date_of_death: datetime
    source: str = "ssa_dmf"

    def to_dict(self) -> dict:
        return {
            "record_id": self.record_id,
            "ssn_hash": self.ssn_hash,
            "date_of_death": _ts(self.date_of_death),
            "source": self.source,
            "_ingested_ts": _now_us(),
        }


@dataclass
class IncarcerationRecord:
    record_id: str
    ssn_hash: str
    facility_state: str
    booking_date: datetime
    release_date: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "record_id": self.record_id,
            "ssn_hash": self.ssn_hash,
            "facility_state": self.facility_state,
            "booking_date": _ts(self.booking_date),
            "release_date": _ts(self.release_date) if self.release_date else None,
            "_ingested_ts": _now_us(),
        }


@dataclass
class OtherBenefitRecord:
    record_id: str
    ssn_hash: str
    source: str  # workers_comp, pfml, pension, ssdi
    benefit_state: str
    start_date: datetime
    end_date: Optional[datetime] = None
    weekly_amount: float = 0.0

    def to_dict(self) -> dict:
        return {
            "record_id": self.record_id,
            "ssn_hash": self.ssn_hash,
            "source": self.source,
            "benefit_state": self.benefit_state,
            "start_date": _ts(self.start_date),
            "end_date": _ts(self.end_date) if self.end_date else None,
            "weekly_amount": self.weekly_amount,
            "_ingested_ts": _now_us(),
        }


@dataclass
class HubSignal:
    signal_id: str
    identifier_type: str  # ssn, bank, ip, email, phone, device
    identifier_hash: str
    signal_type: str  # suspicious_actor, multistate, bad_reputation
    source_state: str
    signal_ts: datetime

    def to_dict(self) -> dict:
        return {
            "signal_id": self.signal_id,
            "identifier_type": self.identifier_type,
            "identifier_hash": self.identifier_hash,
            "signal_type": self.signal_type,
            "source_state": self.source_state,
            "signal_ts": _ts(self.signal_ts),
            "_ingested_ts": _now_us(),
        }


@dataclass
class BankVerification:
    verification_id: str
    bank_hash: str
    claimant_id: str
    source_state: str
    account_open: bool = True
    owner_match: bool = True
    verification_ts: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "verification_id": self.verification_id,
            "bank_hash": self.bank_hash,
            "claimant_id": self.claimant_id,
            "source_state": self.source_state,
            "account_open": self.account_open,
            "owner_match": self.owner_match,
            "verification_ts": _ts(self.verification_ts) if self.verification_ts else _now_us(),
            "_ingested_ts": _now_us(),
        }


@dataclass
class AchReturn:
    return_id: str
    payment_id: str
    return_code: str  # R03, R17, R23, opt_in
    source_state: str
    return_ts: datetime

    def to_dict(self) -> dict:
        return {
            "return_id": self.return_id,
            "payment_id": self.payment_id,
            "return_code": self.return_code,
            "source_state": self.source_state,
            "return_ts": _ts(self.return_ts),
            "_ingested_ts": _now_us(),
        }
