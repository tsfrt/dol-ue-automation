"""Fraud and improper-payment scenario injection.

Each inject_* function modifies events and returns ground-truth metadata.
ScenarioMixer assigns scenarios to a population at configured rates.
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from generator.config import SCENARIO_WEIGHTS
from generator.models import (
    AccountChange,
    GroundTruth,
    HubSignal,
    InitialClaim,
    NewHireRecord,
    Payment,
    WeeklyCertification,
)

if TYPE_CHECKING:
    from .population import Claimant, Population


FAKE_COMPANIES = [
    "Acme Staffing LLC", "Blue Ridge Services Inc", "Metro Talent Group",
    "Premier Workforce Solutions", "National Employment Corp",
    "Sunrise Consulting Group", "Eagle HR Partners",
]

FAKE_WORK_SEARCH = [
    {"employer": "N/A", "contact": "online", "date": "2024-01-01", "result": "no_response"},
    {"employer": "Store #999", "contact": "in_person", "date": "2024-01-02", "result": "no_opening"},
]


def inject_identity_ring(
    claims: list[InitialClaim],
    shared_banks: list[str],
    shared_devices: list[str],
    shared_ip: str,
    rng: random.Random,
) -> list[InitialClaim]:
    """Mutate a batch of claims to share bank accounts, devices, and IPs."""
    for claim in claims:
        claim.bank_hash = rng.choice(shared_banks)
        claim.device_id = rng.choice(shared_devices)
        claim.ip_address = shared_ip
        claim.form_fill_secs = rng.randint(15, 45)
        if rng.random() < 0.3:
            claim.id_check_result = "fail"
        claim.ground_truth = GroundTruth(
            is_fraud=True,
            fraud_scenario="identity_ring",
            bam_action_code=10,
            root_cause="identity",
            responsible_party="claimant",
        )
    return claims


def inject_bye(
    cert: WeeklyCertification,
    actual_earnings: float,
    rng: random.Random,
) -> WeeklyCertification:
    """Claimant certifies $0 but is actually working."""
    cert.earnings_reported = 0.0
    cert.hours_worked = 0
    cert.ground_truth = GroundTruth(
        is_fraud=rng.random() < 0.6,
        is_improper=True,
        fraud_scenario="bye",
        bam_action_code=10 if rng.random() < 0.6 else 11,
        root_cause="benefit_year_earnings",
        responsible_party="claimant",
    )
    return cert


def inject_work_search_noncompliance(
    cert: WeeklyCertification,
    required_contacts: int,
    rng: random.Random,
) -> WeeklyCertification:
    """Fake, duplicated, or insufficient work-search contacts."""
    strategy = rng.choice(["too_few", "duplicated", "fabricated"])

    if strategy == "too_few":
        count = max(0, required_contacts - rng.randint(1, required_contacts))
    elif strategy == "duplicated":
        count = required_contacts
    else:
        count = required_contacts

    contacts = []
    base_contact = rng.choice(FAKE_WORK_SEARCH)
    for i in range(count):
        c = dict(base_contact)
        if strategy != "duplicated":
            c["employer"] = rng.choice(FAKE_COMPANIES)
        contacts.append(c)

    cert.work_search_contacts = json.dumps(contacts)
    cert.ground_truth = GroundTruth(
        is_fraud=rng.random() < 0.3,
        is_improper=True,
        fraud_scenario="work_search",
        bam_action_code=11,
        root_cause="work_search",
        responsible_party="claimant",
    )
    return cert


def inject_separation_mismatch(
    claim: InitialClaim,
    rng: random.Random,
) -> tuple[InitialClaim, str]:
    """Claimant says 'lack_of_work' but employer will say otherwise."""
    claim.separation_reason = "lack_of_work"
    employer_reason = rng.choice(["voluntary_quit", "discharged_misconduct", "discharged_attendance"])
    claim.ground_truth = GroundTruth(
        is_improper=True,
        fraud_scenario="separation_mismatch",
        bam_action_code=11,
        root_cause="separation_issues",
        responsible_party="claimant",
    )
    return claim, employer_reason


def inject_multistate(
    cert: WeeklyCertification,
    other_state: str,
    rng: random.Random,
) -> WeeklyCertification:
    """Same claimant claiming in two states for the same week."""
    cert.ground_truth = GroundTruth(
        is_fraud=True,
        fraud_scenario="multistate",
        bam_action_code=10,
        root_cause="identity",
        responsible_party="claimant",
    )
    return cert


def inject_fictitious_employer(
    claim: InitialClaim,
    fictitious_employer_id: str,
    rng: random.Random,
) -> InitialClaim:
    """Claim backed by a fictitious employer's wage records."""
    claim.last_employer_id = fictitious_employer_id
    claim.ground_truth = GroundTruth(
        is_fraud=True,
        fraud_scenario="fictitious_employer",
        bam_action_code=10,
        root_cause="base_period_wages",
        responsible_party="claimant",
    )
    return claim


def inject_incarcerated(
    cert: WeeklyCertification,
    rng: random.Random,
) -> WeeklyCertification:
    """Certification filed while incarcerated."""
    cert.able_available = True  # falsely certifying
    cert.ground_truth = GroundTruth(
        is_fraud=True,
        fraud_scenario="incarcerated",
        bam_action_code=10,
        root_cause="able_available",
        responsible_party="claimant",
    )
    return cert


def inject_deceased(
    payment: Payment,
    rng: random.Random,
) -> Payment:
    """Payment issued after claimant's date of death."""
    payment.ground_truth = GroundTruth(
        is_fraud=True,
        fraud_scenario="deceased",
        bam_action_code=10,
        root_cause="identity",
        responsible_party="claimant",
    )
    return payment


def inject_account_takeover(
    payment: Payment,
    new_device: str,
    rng: random.Random,
) -> tuple[Payment, AccountChange]:
    """Bank change from a new device, followed by a payment."""
    change = AccountChange(
        change_id=f"CHG-{payment.payment_id}",
        claim_id=payment.claim_id,
        claimant_id=payment.claimant_id,
        source_state=payment.source_state,
        change_type="bank",
        change_ts=datetime.now(timezone.utc) - timedelta(hours=rng.randint(1, 12)),
        device_id=new_device,
        ground_truth=GroundTruth(
            is_fraud=True,
            fraud_scenario="account_takeover",
            bam_action_code=10,
            root_cause="identity",
            responsible_party="claimant",
        ),
    )
    payment.ground_truth = GroundTruth(
        is_fraud=True,
        fraud_scenario="account_takeover",
        bam_action_code=10,
        root_cause="identity",
        responsible_party="claimant",
    )
    return payment, change


def inject_honest_error(
    cert: WeeklyCertification,
    actual_earnings: float,
    rng: random.Random,
) -> WeeklyCertification:
    """Small earnings underreport — not fraud, but improper."""
    cert.earnings_reported = round(actual_earnings * rng.uniform(0.3, 0.7), 2)
    cert.hours_worked = rng.randint(4, 15)
    cert.ground_truth = GroundTruth(
        is_fraud=False,
        is_improper=True,
        fraud_scenario="honest_error",
        bam_action_code=11,
        root_cause="benefit_year_earnings",
        responsible_party="claimant",
    )
    return cert


class ScenarioMixer:
    """Assigns fraud/improper scenarios to events at configured rates."""

    def __init__(self, fraud_rate: float, seed: int):
        self.fraud_rate = fraud_rate
        self.rng = random.Random(seed)
        self.weights = SCENARIO_WEIGHTS
        self.scenarios = list(self.weights.keys())
        self.cumulative = []
        total = 0.0
        for s in self.scenarios:
            total += self.weights[s]
            self.cumulative.append(total)
        self.counts: dict[str, int] = {s: 0 for s in self.scenarios}

    def should_inject(self) -> bool:
        return self.rng.random() < self.fraud_rate

    def pick_scenario(self) -> str:
        r = self.rng.random()
        for i, threshold in enumerate(self.cumulative):
            if r <= threshold:
                scenario = self.scenarios[i]
                self.counts[scenario] += 1
                return scenario
        scenario = self.scenarios[-1]
        self.counts[scenario] += 1
        return scenario

    def summary(self) -> dict[str, int]:
        return dict(self.counts)
