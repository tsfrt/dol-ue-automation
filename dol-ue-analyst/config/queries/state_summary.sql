SELECT
  source_state,
  total_claims,
  flagged_claims,
  flag_rate_pct,
  total_payments,
  ROUND(total_payment_amount, 0) AS total_payment_amount,
  ROUND(flagged_payment_amount, 0) AS flagged_payment_amount,
  true_positives,
  actual_fraud_count,
  detection_rate_pct,
  top_fraud_scenario
FROM lanl.dol_ue_gold.state_summary
ORDER BY total_claims DESC;
