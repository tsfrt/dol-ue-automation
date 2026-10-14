CREATE OR REFRESH MATERIALIZED VIEW crossmatch_alerts
CLUSTER BY (source_state, alert_type)
AS

-- Death match: claimant filed after date of death
SELECT
  ce.claim_id,
  ce.claimant_id,
  ce.source_state,
  'death_match' AS alert_type,
  CONCAT('Deceased ', CAST(dr.date_of_death AS STRING), ' via ', dr.source) AS alert_detail,
  dr.source AS alert_source,
  dr.date_of_death AS alert_ts
FROM claims_enriched ce
INNER JOIN lanl.dol_ue_bronze.ext_death_records dr
  ON ce.ssn_hash = dr.ssn_hash

UNION ALL

-- Incarceration match: claimant filed while incarcerated
SELECT
  ce.claim_id,
  ce.claimant_id,
  ce.source_state,
  'incarceration_match' AS alert_type,
  CONCAT('Booked ', CAST(ir.booking_date AS STRING), ' in ', ir.facility_state) AS alert_detail,
  ir.facility_state AS alert_source,
  ir.booking_date AS alert_ts
FROM claims_enriched ce
INNER JOIN lanl.dol_ue_bronze.ext_incarceration ir
  ON ce.ssn_hash = ir.ssn_hash
WHERE ir.release_date IS NULL
   OR ce.filed_ts BETWEEN ir.booking_date AND ir.release_date

UNION ALL

-- New hire match: claimant was hired during or after claim filing
SELECT
  ce.claim_id,
  ce.claimant_id,
  ce.source_state,
  'new_hire_match' AS alert_type,
  CONCAT('Hired at ', nh.employer_id, ' in ', nh.employer_state) AS alert_detail,
  nh.employer_state AS alert_source,
  nh.hire_date AS alert_ts
FROM claims_enriched ce
INNER JOIN lanl.dol_ue_bronze.ext_new_hires nh
  ON ce.ssn_hash = nh.ssn_hash

UNION ALL

-- Other benefit overlap: concurrent benefits that may affect eligibility
SELECT
  ce.claim_id,
  ce.claimant_id,
  ce.source_state,
  'other_benefit_overlap' AS alert_type,
  CONCAT(ob.source, ' $', CAST(ROUND(ob.weekly_amount, 2) AS STRING), '/wk in ', ob.benefit_state) AS alert_detail,
  ob.benefit_state AS alert_source,
  ob.start_date AS alert_ts
FROM claims_enriched ce
INNER JOIN lanl.dol_ue_bronze.ext_other_benefits ob
  ON ce.ssn_hash = ob.ssn_hash
WHERE ob.end_date IS NULL
   OR ce.filed_ts BETWEEN ob.start_date AND ob.end_date;
