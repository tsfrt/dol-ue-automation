-- @param state_filter STRING
-- @param risk_filter STRING
SELECT
  claim_id,
  claimant_id,
  source_state,
  DATE_FORMAT(filed_date, 'yyyy-MM-dd') AS filed_date,
  risk_score,
  risk_level,
  reason_codes,
  ROUND(COALESCE(payment_amount, 0), 2) AS payment_amount,
  gt_is_fraud,
  gt_fraud_scenario
FROM lanl.dol_ue_gold.claim_risk_profile
WHERE (:state_filter = 'all' OR source_state = :state_filter)
  AND (:risk_filter = 'all' OR risk_level = :risk_filter)
ORDER BY risk_score DESC
LIMIT 500;
