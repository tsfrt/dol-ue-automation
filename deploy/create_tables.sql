-- Bronze tables for the UI Claims Generator → Zerobus Ingest pipeline.
-- Run this before the first generator job.
-- Using catalog=lanl with schemas dol_ue_bronze / dol_ue_silver / dol_ue_gold.

CREATE SCHEMA IF NOT EXISTS lanl.dol_ue_bronze;
CREATE SCHEMA IF NOT EXISTS lanl.dol_ue_silver;
CREATE SCHEMA IF NOT EXISTS lanl.dol_ue_gold;

-- ============================================================
-- Claim lifecycle tables (streaming from state producers)
-- ============================================================

CREATE TABLE IF NOT EXISTS lanl.dol_ue_bronze.initial_claims (
  claim_id            STRING      NOT NULL,
  claimant_id         STRING      NOT NULL,
  source_state        STRING      NOT NULL,
  filed_ts            TIMESTAMP,
  channel             STRING,
  ip_address          STRING,
  geo_country         STRING,
  geo_region          STRING,
  device_id           STRING,
  form_fill_secs      INT,
  separation_reason   STRING,
  last_employer_id    STRING,
  ssn_hash            STRING,
  bank_hash           STRING,
  payment_method      STRING,
  id_check_result     STRING,
  email_domain        STRING,
  phone_hash          STRING,
  address_hash        STRING,
  _ground_truth       STRING,
  _ingested_ts        TIMESTAMP
)
TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true');

CREATE TABLE IF NOT EXISTS lanl.dol_ue_bronze.employer_responses (
  response_id                 STRING  NOT NULL,
  claim_id                    STRING  NOT NULL,
  employer_id                 STRING,
  source_state                STRING  NOT NULL,
  response_ts                 TIMESTAMP,
  separation_reason_employer  STRING,
  narrative                   STRING,
  _ground_truth               STRING,
  _ingested_ts                TIMESTAMP
)
TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true');

CREATE TABLE IF NOT EXISTS lanl.dol_ue_bronze.weekly_certifications (
  cert_id               STRING  NOT NULL,
  claim_id              STRING  NOT NULL,
  claimant_id           STRING  NOT NULL,
  source_state          STRING  NOT NULL,
  week_ending           TIMESTAMP,
  earnings_reported     DOUBLE,
  hours_worked          INT,
  work_search_contacts  STRING,    -- JSON array
  able_available        BOOLEAN,
  refused_work          BOOLEAN,
  ip_address            STRING,
  device_id             STRING,
  _ground_truth         STRING,
  _ingested_ts          TIMESTAMP
)
TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true');

CREATE TABLE IF NOT EXISTS lanl.dol_ue_bronze.payments (
  payment_id    STRING  NOT NULL,
  claim_id      STRING  NOT NULL,
  claimant_id   STRING  NOT NULL,
  source_state  STRING  NOT NULL,
  week_ending   TIMESTAMP,
  amount        DOUBLE,
  method        STRING,
  bank_hash     STRING,
  issued_ts     TIMESTAMP,
  status        STRING,
  _ground_truth STRING,
  _ingested_ts  TIMESTAMP
)
TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true');

CREATE TABLE IF NOT EXISTS lanl.dol_ue_bronze.account_changes (
  change_id     STRING  NOT NULL,
  claim_id      STRING  NOT NULL,
  claimant_id   STRING  NOT NULL,
  source_state  STRING  NOT NULL,
  change_type   STRING,
  change_ts     TIMESTAMP,
  device_id     STRING,
  _ground_truth STRING,
  _ingested_ts  TIMESTAMP
)
TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true');

-- ============================================================
-- External / cross-match feeds
-- ============================================================

CREATE TABLE IF NOT EXISTS lanl.dol_ue_bronze.ext_new_hires (
  record_id       STRING  NOT NULL,
  ssn_hash        STRING  NOT NULL,
  employer_id     STRING,
  employer_state  STRING,
  hire_date       TIMESTAMP,
  report_ts       TIMESTAMP,
  _ingested_ts    TIMESTAMP
)
TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true');

CREATE TABLE IF NOT EXISTS lanl.dol_ue_bronze.ext_death_records (
  record_id       STRING  NOT NULL,
  ssn_hash        STRING  NOT NULL,
  date_of_death   TIMESTAMP,
  source          STRING,
  _ingested_ts    TIMESTAMP
)
TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true');

CREATE TABLE IF NOT EXISTS lanl.dol_ue_bronze.ext_incarceration (
  record_id       STRING  NOT NULL,
  ssn_hash        STRING  NOT NULL,
  facility_state  STRING,
  booking_date    TIMESTAMP,
  release_date    TIMESTAMP,
  _ingested_ts    TIMESTAMP
)
TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true');

CREATE TABLE IF NOT EXISTS lanl.dol_ue_bronze.ext_other_benefits (
  record_id       STRING  NOT NULL,
  ssn_hash        STRING  NOT NULL,
  source          STRING,
  benefit_state   STRING,
  start_date      TIMESTAMP,
  end_date        TIMESTAMP,
  weekly_amount   DOUBLE,
  _ingested_ts    TIMESTAMP
)
TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true');

CREATE TABLE IF NOT EXISTS lanl.dol_ue_bronze.ext_hub_signals (
  signal_id         STRING  NOT NULL,
  identifier_type   STRING,
  identifier_hash   STRING,
  signal_type       STRING,
  source_state      STRING,
  signal_ts         TIMESTAMP,
  _ingested_ts      TIMESTAMP
)
TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true');

CREATE TABLE IF NOT EXISTS lanl.dol_ue_bronze.ext_bank_verification (
  verification_id   STRING  NOT NULL,
  bank_hash         STRING,
  claimant_id       STRING,
  source_state      STRING,
  account_open      BOOLEAN,
  owner_match       BOOLEAN,
  verification_ts   TIMESTAMP,
  _ingested_ts      TIMESTAMP
)
TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true');

CREATE TABLE IF NOT EXISTS lanl.dol_ue_bronze.ext_ach_returns (
  return_id     STRING  NOT NULL,
  payment_id    STRING,
  return_code   STRING,
  source_state  STRING,
  return_ts     TIMESTAMP,
  _ingested_ts  TIMESTAMP
)
TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true');
