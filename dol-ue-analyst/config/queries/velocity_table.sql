-- @param identifier_type_filter STRING
SELECT
  identifier_type,
  identifier_value,
  distinct_claims,
  distinct_states,
  CONCAT_WS(', ', claim_ids) AS claim_ids_str,
  flagged
FROM lanl.dol_ue_gold.velocity_features
WHERE (:identifier_type_filter = 'all' OR identifier_type = :identifier_type_filter)
  AND flagged = true
ORDER BY distinct_claims DESC
LIMIT 500;
