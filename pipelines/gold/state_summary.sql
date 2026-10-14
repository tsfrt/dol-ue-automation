CREATE OR REFRESH MATERIALIZED VIEW lanl.dol_ue_gold.state_summary
CLUSTER BY (source_state)
AS
SELECT
  rp.source_state,

  -- Claim counts
  COUNT(DISTINCT rp.claim_id)                                        AS total_claims,
  COUNT(DISTINCT CASE WHEN rp.risk_score >= 15 THEN rp.claim_id END) AS flagged_claims,
  ROUND(
    COUNT(DISTINCT CASE WHEN rp.risk_score >= 15 THEN rp.claim_id END) * 100.0
    / NULLIF(COUNT(DISTINCT rp.claim_id), 0), 1
  )                                                                   AS flag_rate_pct,

  -- Payment totals
  COUNT(DISTINCT pe.payment_id)                                       AS total_payments,
  ROUND(COALESCE(SUM(pe.amount), 0), 2)                              AS total_payment_amount,
  ROUND(COALESCE(SUM(CASE WHEN rp.risk_score >= 15 THEN pe.amount END), 0), 2)
                                                                      AS flagged_payment_amount,

  -- Detection accuracy (ground truth)
  COUNT(DISTINCT CASE WHEN rp.risk_score >= 15 AND rp.gt_is_fraud THEN rp.claim_id END)
                                                                      AS true_positives,
  COUNT(DISTINCT CASE WHEN rp.gt_is_fraud THEN rp.claim_id END)      AS actual_fraud_count,
  ROUND(
    COUNT(DISTINCT CASE WHEN rp.risk_score >= 15 AND rp.gt_is_fraud THEN rp.claim_id END) * 100.0
    / NULLIF(COUNT(DISTINCT CASE WHEN rp.gt_is_fraud THEN rp.claim_id END), 0), 1
  )                                                                   AS detection_rate_pct,

  -- Top fraud scenario
  MODE(rp.gt_fraud_scenario) FILTER (WHERE rp.gt_fraud_scenario IS NOT NULL AND rp.gt_fraud_scenario != '')
                                                                      AS top_fraud_scenario

FROM lanl.dol_ue_gold.claim_risk_profile rp
LEFT JOIN payments_enriched pe
  ON rp.claim_id = pe.claim_id
GROUP BY rp.source_state;
