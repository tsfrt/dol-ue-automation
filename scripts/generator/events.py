"""Lifecycle-ordered event generators for one simulated week.

Produces events in the order they'd naturally occur:
  initial claims → employer responses → weekly certifications →
  payments → external cross-match feeds
"""

from __future__ import annotations

import json
import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from generator.models import (
    AchReturn,
    BankVerification,
    DeathRecord,
    EmployerResponse,
    GroundTruth,
    HubSignal,
    IncarcerationRecord,
    InitialClaim,
    NewHireRecord,
    OtherBenefitRecord,
    Payment,
    WeeklyCertification,
)
from generator.profiles import PROFILES
from generator.scenarios import (
    ScenarioMixer,
    inject_account_takeover,
    inject_bye,
    inject_deceased,
    inject_fictitious_employer,
    inject_honest_error,
    inject_identity_ring,
    inject_incarcerated,
    inject_multistate,
    inject_separation_mismatch,
    inject_work_search_noncompliance,
)

if TYPE_CHECKING:
    from .population import Claimant, Employer, Population

WORK_SEARCH_COMPANIES = [
    "Target", "Walmart", "Home Depot", "CVS", "Kroger",
    "Amazon Warehouse", "FedEx", "UPS", "Costco", "Lowes",
    "Best Buy", "Starbucks", "McDonalds", "Subway", "Publix",
]


def _uid() -> str:
    return uuid.uuid4().hex[:12]


def _random_contacts(count: int, rng: random.Random) -> str:
    contacts = []
    used = set()
    for _ in range(count):
        co = rng.choice(WORK_SEARCH_COMPANIES)
        while co in used and len(used) < len(WORK_SEARCH_COMPANIES):
            co = rng.choice(WORK_SEARCH_COMPANIES)
        used.add(co)
        contacts.append({
            "employer": co,
            "contact": rng.choice(["online", "in_person", "phone", "email"]),
            "date": (datetime.now(timezone.utc) - timedelta(days=rng.randint(0, 6))).strftime("%Y-%m-%d"),
            "result": rng.choice(["applied", "no_response", "interview_scheduled", "no_opening"]),
        })
    return json.dumps(contacts)


def generate_initial_claims(
    pop: "Population",
    state: str,
    week_start: datetime,
    new_claims_count: int,
    mixer: ScenarioMixer,
    rng: random.Random,
) -> list[InitialClaim]:
    profile = PROFILES[state]
    claimant_ids = pop.state_claimants[state]
    claims: list[InitialClaim] = []

    candidates = rng.sample(claimant_ids, min(new_claims_count, len(claimant_ids)))

    separation_mismatches: list[tuple[str, str]] = []  # (claim_id, employer_reason)

    for cid in candidates:
        c = pop.claimants[cid]
        filed_ts = week_start + timedelta(
            hours=rng.randint(0, 120),
            minutes=rng.randint(0, 59),
        )
        emp_ids = pop.state_employers[state]
        employer_id = rng.choice(emp_ids)

        claim = InitialClaim(
            claim_id=f"IC-{state}-{_uid()}",
            claimant_id=cid,
            source_state=state,
            filed_ts=filed_ts,
            channel=rng.choices(["online", "phone", "in_person"], weights=[0.85, 0.10, 0.05])[0],
            ip_address=c.ip_address,
            geo_country="US",
            geo_region=state,
            device_id=c.device_id,
            form_fill_secs=rng.randint(180, 900),
            separation_reason=rng.choices(
                ["lack_of_work", "voluntary_quit", "discharged"],
                weights=[0.70, 0.20, 0.10],
            )[0],
            last_employer_id=employer_id,
            ssn_hash=c.ssn_hash,
            bank_hash=c.bank_hash,
            payment_method="direct_deposit" if rng.random() < 0.9 else "debit_card",
            id_check_result="pass",
            email_domain=c.email_domain,
            phone_hash=c.phone_hash,
            address_hash=c.address_hash,
        )

        if mixer.should_inject():
            scenario = mixer.pick_scenario()

            if scenario == "fictitious_employer" and pop.fictitious_employers:
                fict_emp = rng.choice(pop.fictitious_employers)
                claim = inject_fictitious_employer(claim, fict_emp, rng)
            elif scenario == "separation_mismatch":
                claim, emp_reason = inject_separation_mismatch(claim, rng)
                separation_mismatches.append((claim.claim_id, emp_reason))
            elif scenario == "identity_ring":
                claim.form_fill_secs = rng.randint(15, 45)
                claim.ground_truth = GroundTruth(
                    is_fraud=True,
                    fraud_scenario="identity_ring",
                    bam_action_code=10,
                    root_cause="identity",
                    responsible_party="claimant",
                )

        claims.append(claim)

    return claims


def generate_employer_responses(
    claims: list[InitialClaim],
    pop: "Population",
    week_start: datetime,
    rng: random.Random,
    response_rate: float = 0.80,
) -> list[EmployerResponse]:
    responses: list[EmployerResponse] = []

    for claim in claims:
        if rng.random() > response_rate:
            continue

        delay_hours = rng.randint(24, 168)
        response_ts = claim.filed_ts + timedelta(hours=delay_hours)

        if claim.ground_truth.fraud_scenario == "separation_mismatch":
            emp_reason = rng.choice(["voluntary_quit", "discharged_misconduct"])
            narrative = f"Claimant separated due to {emp_reason.replace('_', ' ')}. Not eligible."
        else:
            emp_reason = claim.separation_reason
            narrative = f"Confirmed: {emp_reason.replace('_', ' ')}."

        responses.append(EmployerResponse(
            response_id=f"ER-{_uid()}",
            claim_id=claim.claim_id,
            employer_id=claim.last_employer_id,
            source_state=claim.source_state,
            response_ts=response_ts,
            separation_reason_employer=emp_reason,
            narrative=narrative,
        ))

    return responses


def generate_weekly_certifications(
    active_claim_ids: list[tuple[str, str, str]],  # (claim_id, claimant_id, state)
    week_ending: datetime,
    pop: "Population",
    mixer: ScenarioMixer,
    rng: random.Random,
    cert_rate: float = 0.75,
) -> list[WeeklyCertification]:
    certs: list[WeeklyCertification] = []

    for claim_id, claimant_id, state in active_claim_ids:
        if rng.random() > cert_rate:
            continue

        profile = PROFILES[state]
        c = pop.claimants[claimant_id]

        contacts = _random_contacts(profile.work_search_contacts, rng)
        earnings = 0.0
        hours = 0
        if rng.random() < 0.15:  # 15% report some part-time earnings
            earnings = round(rng.uniform(50, 400), 2)
            hours = rng.randint(4, 20)

        cert = WeeklyCertification(
            cert_id=f"WC-{state}-{_uid()}",
            claim_id=claim_id,
            claimant_id=claimant_id,
            source_state=state,
            week_ending=week_ending,
            earnings_reported=earnings,
            hours_worked=hours,
            work_search_contacts=contacts,
            able_available=True,
            refused_work=False,
            ip_address=c.ip_address,
            device_id=c.device_id,
        )

        if mixer.should_inject():
            scenario = mixer.pick_scenario()
            actual_earnings = round(rng.uniform(200, 1200), 2)

            if scenario == "bye":
                cert = inject_bye(cert, actual_earnings, rng)
            elif scenario == "work_search":
                cert = inject_work_search_noncompliance(cert, profile.work_search_contacts, rng)
            elif scenario == "multistate":
                other_states = [s for s in PROFILES if s != state]
                cert = inject_multistate(cert, rng.choice(other_states), rng)
            elif scenario == "incarcerated" and claimant_id in set(pop.incarcerated_claimants):
                cert = inject_incarcerated(cert, rng)
            elif scenario == "honest_error":
                cert = inject_honest_error(cert, actual_earnings, rng)
            else:
                cert = inject_work_search_noncompliance(cert, profile.work_search_contacts, rng)

        certs.append(cert)

    return certs


def generate_payments(
    certs: list[WeeklyCertification],
    pop: "Population",
    rng: random.Random,
    mixer: ScenarioMixer,
) -> tuple[list[Payment], list["AccountChange"]]:
    payments: list[Payment] = []
    account_changes: list["AccountChange"] = []

    for cert in certs:
        c = pop.claimants.get(cert.claimant_id)
        if not c:
            continue

        profile = PROFILES[cert.source_state]
        net_earnings = cert.earnings_reported
        wba = min(profile.wba_max, rng.uniform(200, profile.wba_max))
        amount = max(0, round(wba - net_earnings * 0.5, 2))

        if amount <= 0:
            continue

        is_deceased = c.is_deceased and c.date_of_death and cert.week_ending > c.date_of_death
        status = "released"

        payment = Payment(
            payment_id=f"PAY-{cert.source_state}-{_uid()}",
            claim_id=cert.claim_id,
            claimant_id=cert.claimant_id,
            source_state=cert.source_state,
            week_ending=cert.week_ending,
            amount=amount,
            method="direct_deposit" if rng.random() < 0.9 else "debit_card",
            bank_hash=c.bank_hash,
            issued_ts=cert.week_ending + timedelta(hours=rng.randint(24, 72)),
            status=status,
        )

        if is_deceased:
            payment = inject_deceased(payment, rng)
        elif mixer.should_inject():
            scenario = mixer.pick_scenario()
            if scenario == "account_takeover":
                new_device = f"DEV-ATO-{_uid()}"
                payment, change = inject_account_takeover(payment, new_device, rng)
                account_changes.append(change)
            elif scenario == "deceased" and is_deceased:
                payment = inject_deceased(payment, rng)

        if cert.ground_truth.is_fraud or cert.ground_truth.is_improper:
            payment.ground_truth = cert.ground_truth

        payments.append(payment)

    return payments, account_changes


def generate_ext_new_hires(
    pop: "Population",
    week_start: datetime,
    rng: random.Random,
    count_per_state: int = 100,
) -> list[NewHireRecord]:
    records: list[NewHireRecord] = []

    for state in PROFILES:
        claimant_ids = pop.state_claimants[state]
        hired = rng.sample(claimant_ids, min(count_per_state, len(claimant_ids)))
        for cid in hired:
            c = pop.claimants[cid]
            emp_id = rng.choice(pop.state_employers[state])
            hire_date = week_start + timedelta(days=rng.randint(0, 6))
            records.append(NewHireRecord(
                record_id=f"NH-{_uid()}",
                ssn_hash=c.ssn_hash,
                employer_id=emp_id,
                employer_state=state,
                hire_date=hire_date,
                report_ts=hire_date + timedelta(days=rng.randint(1, 14)),
            ))

    return records


def generate_ext_death_records(
    pop: "Population",
    rng: random.Random,
) -> list[DeathRecord]:
    records: list[DeathRecord] = []
    for cid in pop.deceased_claimants:
        c = pop.claimants[cid]
        if c.date_of_death:
            records.append(DeathRecord(
                record_id=f"DR-{_uid()}",
                ssn_hash=c.ssn_hash,
                date_of_death=c.date_of_death,
                source=rng.choice(["ssa_dmf", "state_vital_records"]),
            ))
    return records


def generate_ext_incarceration(
    pop: "Population",
    rng: random.Random,
) -> list[IncarcerationRecord]:
    records: list[IncarcerationRecord] = []
    for cid in pop.incarcerated_claimants:
        c = pop.claimants[cid]
        if c.incarceration_start:
            release = c.incarceration_start + timedelta(days=rng.randint(30, 365)) if rng.random() < 0.5 else None
            records.append(IncarcerationRecord(
                record_id=f"JR-{_uid()}",
                ssn_hash=c.ssn_hash,
                facility_state=c.state,
                booking_date=c.incarceration_start,
                release_date=release,
            ))
    return records


def generate_ext_other_benefits(
    pop: "Population",
    rng: random.Random,
    week_start: datetime,
    count: int = 200,
) -> list[OtherBenefitRecord]:
    records: list[OtherBenefitRecord] = []
    all_claimant_ids = list(pop.claimants.keys())
    chosen = rng.sample(all_claimant_ids, min(count, len(all_claimant_ids)))

    for cid in chosen:
        c = pop.claimants[cid]
        profile = PROFILES[c.state]
        source = rng.choice(["workers_comp", "pfml", "pension", "ssdi"])
        if source == "pfml" and not profile.has_pfml:
            source = "workers_comp"

        records.append(OtherBenefitRecord(
            record_id=f"OB-{_uid()}",
            ssn_hash=c.ssn_hash,
            source=source,
            benefit_state=c.state,
            start_date=week_start - timedelta(days=rng.randint(0, 90)),
            end_date=week_start + timedelta(days=rng.randint(30, 180)) if rng.random() < 0.6 else None,
            weekly_amount=round(rng.uniform(100, 800), 2),
        ))

    return records


def generate_ext_hub_signals(
    claims: list[InitialClaim],
    rng: random.Random,
) -> list[HubSignal]:
    signals: list[HubSignal] = []

    for claim in claims:
        if claim.ground_truth.is_fraud and rng.random() < 0.4:
            signals.append(HubSignal(
                signal_id=f"HS-{_uid()}",
                identifier_type=rng.choice(["ssn", "bank", "ip", "email", "device"]),
                identifier_hash=rng.choice([claim.bank_hash, claim.device_id, claim.ip_address]),
                signal_type=rng.choice(["suspicious_actor", "multistate", "bad_reputation"]),
                source_state=claim.source_state,
                signal_ts=claim.filed_ts + timedelta(minutes=rng.randint(1, 30)),
            ))

    return signals


def generate_ext_bank_verification(
    payments: list[Payment],
    pop: "Population",
    rng: random.Random,
) -> list[BankVerification]:
    records: list[BankVerification] = []

    for pay in payments:
        if rng.random() > 0.05:  # only verify ~5% of payments
            continue

        is_fraud = pay.ground_truth.is_fraud
        records.append(BankVerification(
            verification_id=f"BV-{_uid()}",
            bank_hash=pay.bank_hash,
            claimant_id=pay.claimant_id,
            source_state=pay.source_state,
            account_open=True if not is_fraud else rng.random() < 0.5,
            owner_match=True if not is_fraud else rng.random() < 0.3,
            verification_ts=pay.issued_ts,
        ))

    return records


def generate_ext_ach_returns(
    payments: list[Payment],
    rng: random.Random,
) -> list[AchReturn]:
    records: list[AchReturn] = []

    for pay in payments:
        if pay.ground_truth.is_fraud and rng.random() < 0.15:
            records.append(AchReturn(
                return_id=f"AR-{_uid()}",
                payment_id=pay.payment_id,
                return_code=rng.choice(["R03", "R17", "R23", "opt_in"]),
                source_state=pay.source_state,
                return_ts=pay.issued_ts + timedelta(days=rng.randint(1, 5)) if pay.issued_ts else datetime.now(timezone.utc),
            ))

    return records
