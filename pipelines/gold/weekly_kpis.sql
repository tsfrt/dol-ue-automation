CREATE OR REFRESH MATERIALIZED VIEW lanl.dol_ue_gold.weekly_kpis
CLUSTER BY (week_ending)
AS
WITH claim_weeks AS (
  SELECT
    DATE_TRUNC('WEEK', filed_date) AS week_ending,
    COUNT(*)                       AS claims_filed,
    SUM(CASE WHEN gt_is_fraud THEN 1 ELSE 0 END) AS fraud_claims_filed
  FROM claims_enriched
  GROUP BY DATE_TRUNC('WEEK', filed_date)
),
cert_weeks AS (
  SELECT
    CAST(week_ending AS DATE) AS week_ending,
    COUNT(*)                  AS certs_submitted,
    SUM(CASE WHEN gt_is_fraud THEN 1 ELSE 0 END) AS fraud_certs
  FROM certifications_enriched
  GROUP BY CAST(week_ending AS DATE)
),
payment_weeks AS (
  SELECT
    CAST(week_ending AS DATE)  AS week_ending,
    COUNT(*)                   AS payments_made,
    ROUND(SUM(amount), 2)      AS total_paid_amount,
    SUM(CASE WHEN has_ach_return THEN 1 ELSE 0 END) AS ach_returns,
    SUM(CASE WHEN gt_is_fraud THEN 1 ELSE 0 END) AS fraud_payments
  FROM payments_enriched
  GROUP BY CAST(week_ending AS DATE)
)

SELECT
  COALESCE(cw.week_ending, ce.week_ending, pw.week_ending) AS week_ending,
  COALESCE(cw.claims_filed, 0)      AS claims_filed,
  COALESCE(cw.fraud_claims_filed, 0) AS fraud_claims_filed,
  COALESCE(ce.certs_submitted, 0)   AS certs_submitted,
  COALESCE(pw.payments_made, 0)     AS payments_made,
  COALESCE(pw.total_paid_amount, 0) AS total_paid_amount,
  COALESCE(pw.ach_returns, 0)       AS ach_returns,
  COALESCE(pw.fraud_payments, 0)    AS fraud_payments
FROM claim_weeks cw
FULL OUTER JOIN cert_weeks ce  ON cw.week_ending = ce.week_ending
FULL OUTER JOIN payment_weeks pw ON cw.week_ending = pw.week_ending;
