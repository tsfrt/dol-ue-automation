SELECT
  DATE_FORMAT(week_ending, 'yyyy-MM-dd') AS week_ending,
  claims_filed,
  fraud_claims_filed,
  certs_submitted,
  payments_made,
  ROUND(total_paid_amount, 0) AS total_paid_amount,
  ach_returns,
  fraud_payments
FROM lanl.dol_ue_gold.weekly_kpis
ORDER BY week_ending;
