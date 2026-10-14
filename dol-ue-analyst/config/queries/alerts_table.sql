-- @param alert_type_filter STRING
SELECT
  claim_id,
  claimant_id,
  source_state,
  alert_type,
  alert_detail,
  alert_source,
  DATE_FORMAT(alert_ts, 'yyyy-MM-dd HH:mm') AS alert_ts
FROM lanl.dol_ue_silver.crossmatch_alerts
WHERE (:alert_type_filter = 'all' OR alert_type = :alert_type_filter)
ORDER BY alert_ts DESC;
