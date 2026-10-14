"""Generator configuration: catalog/schema targets, table names, timing, fraud rates."""

import os

CATALOG = os.environ.get("DOL_CATALOG", "lanl")
SCHEMA = os.environ.get("DOL_SCHEMA", "dol_ue_bronze")

def fqn(table: str) -> str:
    return f"{CATALOG}.{SCHEMA}.{table}"

# Bronze table names
TABLE_INITIAL_CLAIMS = "initial_claims"
TABLE_EMPLOYER_RESPONSES = "employer_responses"
TABLE_WEEKLY_CERTS = "weekly_certifications"
TABLE_PAYMENTS = "payments"
TABLE_ACCOUNT_CHANGES = "account_changes"
TABLE_EXT_NEW_HIRES = "ext_new_hires"
TABLE_EXT_DEATH_RECORDS = "ext_death_records"
TABLE_EXT_INCARCERATION = "ext_incarceration"
TABLE_EXT_OTHER_BENEFITS = "ext_other_benefits"
TABLE_EXT_HUB_SIGNALS = "ext_hub_signals"
TABLE_EXT_BANK_VERIFICATION = "ext_bank_verification"
TABLE_EXT_ACH_RETURNS = "ext_ach_returns"

ALL_TABLES = [
    TABLE_INITIAL_CLAIMS,
    TABLE_EMPLOYER_RESPONSES,
    TABLE_WEEKLY_CERTS,
    TABLE_PAYMENTS,
    TABLE_ACCOUNT_CHANGES,
    TABLE_EXT_NEW_HIRES,
    TABLE_EXT_DEATH_RECORDS,
    TABLE_EXT_INCARCERATION,
    TABLE_EXT_OTHER_BENEFITS,
    TABLE_EXT_HUB_SIGNALS,
    TABLE_EXT_BANK_VERIFICATION,
    TABLE_EXT_ACH_RETURNS,
]

# Simulation timing
SIM_WEEK_DURATION_SECS = int(os.environ.get("SIM_DURATION", "300"))

# Fraud / improper payment injection rate (share of weekly certifications)
FRAUD_RATE = float(os.environ.get("FRAUD_RATE", "0.08"))

# Scenario weights within the fraud population (must sum to 1.0)
SCENARIO_WEIGHTS = {
    "bye":                  0.30,
    "work_search":          0.30,
    "identity_ring":        0.10,
    "separation_mismatch":  0.10,
    "multistate":           0.05,
    "fictitious_employer":  0.05,
    "incarcerated":         0.03,
    "deceased":             0.02,
    "account_takeover":     0.03,
    "honest_error":         0.02,
}

# Population scale
CLAIMANTS_PER_STATE = int(os.environ.get("CLAIMANTS_PER_STATE", "2000"))
EMPLOYERS_PER_STATE = int(os.environ.get("EMPLOYERS_PER_STATE", "500"))
NEW_CLAIMS_PER_STATE_PER_WEEK = int(os.environ.get("NEW_CLAIMS_PER_STATE", "200"))

# Zerobus connection (env vars, set at deploy time)
ZEROBUS_SERVER_ENDPOINT = os.environ.get("ZEROBUS_SERVER_ENDPOINT", "")
DATABRICKS_WORKSPACE_URL = os.environ.get("DATABRICKS_WORKSPACE_URL", "")
DATABRICKS_CLIENT_ID = os.environ.get("DATABRICKS_CLIENT_ID", "")
DATABRICKS_CLIENT_SECRET = os.environ.get("DATABRICKS_CLIENT_SECRET", "")
