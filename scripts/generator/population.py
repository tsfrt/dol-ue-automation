"""Seed population generator: employers, claimants, and wage records.

Produces deterministic populations given a seed.  Uses Faker for realistic
names/addresses and hashlib for synthetic PII identifiers.
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from faker import Faker

from generator.profiles import PROFILES, StateProfile


@dataclass
class Employer:
    employer_id: str
    fein: str
    state: str
    name: str
    naics: str
    registered_date: datetime
    employee_count: int
    is_fictitious: bool = False


@dataclass
class Claimant:
    claimant_id: str
    ssn_hash: str
    name: str
    dob: datetime
    address_hash: str
    phone_hash: str
    email: str
    email_domain: str
    bank_hash: str
    device_id: str
    ip_address: str
    state: str
    is_synthetic_identity: bool = False
    is_deceased: bool = False
    date_of_death: datetime | None = None
    is_incarcerated: bool = False
    incarceration_start: datetime | None = None


@dataclass
class WageRecord:
    employer_id: str
    claimant_id: str
    ssn_hash: str
    state: str
    year_qtr: str
    wages: float


@dataclass
class Population:
    employers: dict[str, Employer] = field(default_factory=dict)
    claimants: dict[str, Claimant] = field(default_factory=dict)
    wage_records: list[WageRecord] = field(default_factory=list)
    state_claimants: dict[str, list[str]] = field(default_factory=dict)
    state_employers: dict[str, list[str]] = field(default_factory=dict)

    # Pre-built groups for fraud injection
    shared_bank_claimants: list[list[str]] = field(default_factory=list)
    shared_device_claimants: list[list[str]] = field(default_factory=list)
    deceased_claimants: list[str] = field(default_factory=list)
    incarcerated_claimants: list[str] = field(default_factory=list)
    fictitious_employers: list[str] = field(default_factory=list)


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:16]


NAICS_CODES = [
    "722511", "445110", "561320", "236220", "621111",
    "541511", "238220", "423510", "484121", "311812",
    "721110", "531210", "611310", "622110", "441110",
]

SEPARATION_REASONS = [
    "lack_of_work", "lack_of_work", "lack_of_work", "lack_of_work",
    "voluntary_quit", "discharged",
]

DISPOSABLE_DOMAINS = [
    "tempmail.com", "throwaway.email", "guerrillamail.com",
    "mailinator.com", "yopmail.com",
]

NORMAL_DOMAINS = [
    "gmail.com", "yahoo.com", "outlook.com", "hotmail.com",
    "aol.com", "icloud.com", "protonmail.com",
]


def generate_population(
    seed: int,
    employers_per_state: int,
    claimants_per_state: int,
    sim_date: datetime,
) -> Population:
    rng = random.Random(seed)
    fake = Faker()
    Faker.seed(seed)
    fake.seed_instance(seed)

    pop = Population()
    now = sim_date

    for state_code, profile in PROFILES.items():
        pop.state_employers[state_code] = []
        pop.state_claimants[state_code] = []

        # --- Employers ---
        fictitious_count = max(1, int(employers_per_state * 0.005))  # ~0.5%
        for i in range(employers_per_state):
            eid = f"EMP-{state_code}-{i:05d}"
            is_fict = i >= (employers_per_state - fictitious_count)

            if is_fict:
                reg_date = now - timedelta(days=rng.randint(30, 90))
            else:
                reg_date = now - timedelta(days=rng.randint(365, 3650))

            # Zipf-like employee count
            emp_count = max(1, int(rng.paretovariate(1.5)))
            emp_count = min(emp_count, 5000)

            emp = Employer(
                employer_id=eid,
                fein=f"{rng.randint(10,99)}-{rng.randint(1000000,9999999)}",
                state=state_code,
                name=fake.company(),
                naics=rng.choice(NAICS_CODES),
                registered_date=reg_date,
                employee_count=emp_count,
                is_fictitious=is_fict,
            )
            pop.employers[eid] = emp
            pop.state_employers[state_code].append(eid)
            if is_fict:
                pop.fictitious_employers.append(eid)

        # --- Shared identifiers for identity-ring scenario ---
        ring_bank_count = max(2, claimants_per_state // 200)
        ring_device_count = max(3, claimants_per_state // 150)
        shared_banks = [_hash(f"ring-bank-{state_code}-{j}") for j in range(ring_bank_count)]
        shared_devices = [f"DEV-RING-{state_code}-{j:03d}" for j in range(ring_device_count)]
        ring_ip = f"198.51.100.{rng.randint(1,254)}"

        ring_claimant_ids: list[str] = []

        # --- Claimants ---
        deceased_count = max(1, int(claimants_per_state * 0.002))
        incarcerated_count = max(1, int(claimants_per_state * 0.003))
        ring_count = max(5, int(claimants_per_state * 0.015))  # ~1.5% in identity-ring pool

        for i in range(claimants_per_state):
            cid = f"CLM-{state_code}-{i:05d}"
            ssn_hash = _hash(f"ssn-{state_code}-{i}")

            is_ring = i < ring_count
            is_dead = ring_count <= i < ring_count + deceased_count
            is_jail = ring_count + deceased_count <= i < ring_count + deceased_count + incarcerated_count
            is_synthetic = is_ring and rng.random() < 0.3

            if is_ring:
                bank = rng.choice(shared_banks)
                device = rng.choice(shared_devices)
                ip = ring_ip
                domain = rng.choice(DISPOSABLE_DOMAINS) if rng.random() < 0.4 else rng.choice(NORMAL_DOMAINS)
            else:
                bank = _hash(f"bank-{state_code}-{i}")
                device = f"DEV-{state_code}-{i:05d}"
                ip = f"{rng.randint(1,223)}.{rng.randint(0,255)}.{rng.randint(0,255)}.{rng.randint(1,254)}"
                domain = rng.choice(NORMAL_DOMAINS)

            death_date = None
            jail_start = None
            if is_dead:
                death_date = now - timedelta(days=rng.randint(5, 60))
            if is_jail:
                jail_start = now - timedelta(days=rng.randint(10, 120))

            claimant = Claimant(
                claimant_id=cid,
                ssn_hash=ssn_hash,
                name=fake.name(),
                dob=fake.date_of_birth(minimum_age=18, maximum_age=67),
                address_hash=_hash(f"addr-{state_code}-{i}" if not is_ring else f"addr-ring-{state_code}"),
                phone_hash=_hash(f"phone-{state_code}-{i}"),
                email=f"claimant{i}@{domain}",
                email_domain=domain,
                bank_hash=bank,
                device_id=device,
                ip_address=ip,
                state=state_code,
                is_synthetic_identity=is_synthetic,
                is_deceased=is_dead,
                date_of_death=death_date,
                is_incarcerated=is_jail,
                incarceration_start=jail_start,
            )
            pop.claimants[cid] = claimant
            pop.state_claimants[state_code].append(cid)

            if is_ring:
                ring_claimant_ids.append(cid)
            if is_dead:
                pop.deceased_claimants.append(cid)
            if is_jail:
                pop.incarcerated_claimants.append(cid)

        pop.shared_bank_claimants.append(ring_claimant_ids)
        pop.shared_device_claimants.append(ring_claimant_ids)

        # --- Wage records (4 quarters of base period) ---
        employer_ids = pop.state_employers[state_code]
        for cid in pop.state_claimants[state_code]:
            claimant = pop.claimants[cid]
            # Most claimants worked for 1 employer; some worked for 2
            emp_count = 1 if rng.random() < 0.85 else 2
            for _ in range(emp_count):
                eid = rng.choice(employer_ids)
                quarterly_wage = max(500.0, rng.lognormvariate(9.0, 0.7))
                for q_offset in range(4):
                    qtr_date = now - timedelta(days=90 * (q_offset + 1))
                    yr = qtr_date.year
                    qtr = (qtr_date.month - 1) // 3 + 1
                    pop.wage_records.append(WageRecord(
                        employer_id=eid,
                        claimant_id=cid,
                        ssn_hash=claimant.ssn_hash,
                        state=state_code,
                        year_qtr=f"{yr}Q{qtr}",
                        wages=round(quarterly_wage * rng.uniform(0.8, 1.2), 2),
                    ))

    return pop
