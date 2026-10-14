CREATE OR REFRESH STREAMING TABLE certifications_enriched (
  CONSTRAINT valid_cert_id  EXPECT (cert_id IS NOT NULL)  ON VIOLATION DROP ROW,
  CONSTRAINT valid_claim_id EXPECT (claim_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT valid_earnings EXPECT (earnings_reported >= 0)
)
CLUSTER BY (source_state)
AS
SELECT
  wc.cert_id,
  wc.claim_id,
  wc.claimant_id,
  wc.source_state,
  wc.week_ending,
  wc.earnings_reported,
  wc.hours_worked,
  wc.work_search_contacts,
  wc.able_available,
  wc.refused_work,
  wc.ip_address,
  wc.device_id,

  -- Count of work-search contacts reported
  COALESCE(json_array_length(wc.work_search_contacts), 0) AS work_search_count,

  -- Parsed ground truth
  get_json_object(wc._ground_truth, '$.is_fraud') = 'true'    AS gt_is_fraud,
  get_json_object(wc._ground_truth, '$.is_improper') = 'true'  AS gt_is_improper,
  get_json_object(wc._ground_truth, '$.fraud_scenario')        AS gt_fraud_scenario,

  wc._ingested_ts

FROM STREAM(lanl.dol_ue_bronze.weekly_certifications) wc;
