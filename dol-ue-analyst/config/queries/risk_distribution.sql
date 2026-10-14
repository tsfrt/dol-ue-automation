SELECT
  risk_level,
  COUNT(*) AS claim_count,
  ROUND(AVG(risk_score), 1) AS avg_score,
  MAX(risk_score) AS max_score
FROM lanl.dol_ue_gold.claim_risk_profile
GROUP BY risk_level
ORDER BY
  CASE risk_level
    WHEN 'low' THEN 1
    WHEN 'medium' THEN 2
    WHEN 'high' THEN 3
  END;
