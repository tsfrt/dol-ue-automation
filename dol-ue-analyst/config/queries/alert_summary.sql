SELECT
  alert_type,
  source_state,
  COUNT(*) AS alert_count
FROM lanl.dol_ue_silver.crossmatch_alerts
GROUP BY alert_type, source_state
ORDER BY alert_count DESC;
