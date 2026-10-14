CREATE OR REFRESH STREAMING TABLE claims_enriched (
  CONSTRAINT valid_claim_id   EXPECT (claim_id IS NOT NULL)    ON VIOLATION DROP ROW,
  CONSTRAINT valid_state      EXPECT (source_state IS NOT NULL) ON VIOLATION DROP ROW
)
CLUSTER BY (source_state)
AS
SELECT
  ic.claim_id,
  ic.claimant_id,
  ic.ssn_hash,
  ic.source_state,
  ic.filed_ts,
  CAST(ic.filed_ts AS DATE) AS filed_date,
  ic.channel,
  ic.ip_address,
  ic.device_id,
  ic.form_fill_secs,
  ic.separation_reason,
  ic.last_employer_id,
  ic.bank_hash,
  ic.payment_method,
  ic.email_domain,
  ic.phone_hash,
  ic.address_hash,

  -- Employer response (static side of stream-static join)
  er.separation_reason_employer,
  er.response_ts AS employer_response_ts,

  -- Separation mismatch: claimant says one thing, employer says another
  CASE
    WHEN er.separation_reason_employer IS NOT NULL
     AND ic.separation_reason != er.separation_reason_employer
    THEN TRUE
    ELSE FALSE
  END AS separation_mismatch,

  -- Parsed ground truth for downstream validation
  get_json_object(ic._ground_truth, '$.is_fraud') = 'true'             AS gt_is_fraud,
  get_json_object(ic._ground_truth, '$.is_improper') = 'true'          AS gt_is_improper,
  get_json_object(ic._ground_truth, '$.fraud_scenario')                AS gt_fraud_scenario,
  CAST(get_json_object(ic._ground_truth, '$.bam_action_code') AS INT)  AS gt_bam_action_code,
  get_json_object(ic._ground_truth, '$.root_cause')                    AS gt_root_cause,

  ic._ingested_ts

FROM STREAM(lanl.dol_ue_bronze.initial_claims) ic
LEFT JOIN lanl.dol_ue_bronze.employer_responses er
  ON ic.claim_id = er.claim_id;
