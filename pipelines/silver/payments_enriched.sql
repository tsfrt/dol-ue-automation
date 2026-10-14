CREATE OR REFRESH STREAMING TABLE payments_enriched (
  CONSTRAINT valid_payment_id EXPECT (payment_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT positive_amount  EXPECT (amount > 0)             ON VIOLATION DROP ROW
)
CLUSTER BY (source_state)
AS
SELECT
  p.payment_id,
  p.claim_id,
  p.claimant_id,
  p.source_state,
  p.week_ending,
  p.amount,
  p.method,
  p.bank_hash,
  p.issued_ts,
  p.status,

  -- Bank verification flags (static join)
  bv.account_open  AS bank_account_open,
  bv.owner_match   AS bank_owner_match,

  -- ACH return info (static join)
  ar.return_code   AS ach_return_code,
  ar.return_ts     AS ach_return_ts,
  CASE WHEN ar.return_id IS NOT NULL THEN TRUE ELSE FALSE END AS has_ach_return,

  -- Parsed ground truth
  get_json_object(p._ground_truth, '$.is_fraud') = 'true'    AS gt_is_fraud,
  get_json_object(p._ground_truth, '$.is_improper') = 'true'  AS gt_is_improper,
  get_json_object(p._ground_truth, '$.fraud_scenario')        AS gt_fraud_scenario,

  p._ingested_ts

FROM STREAM(lanl.dol_ue_bronze.payments) p
LEFT JOIN lanl.dol_ue_bronze.ext_bank_verification bv
  ON p.bank_hash = bv.bank_hash
LEFT JOIN lanl.dol_ue_bronze.ext_ach_returns ar
  ON p.payment_id = ar.payment_id;
