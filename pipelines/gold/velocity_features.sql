CREATE OR REFRESH MATERIALIZED VIEW lanl.dol_ue_gold.velocity_features
CLUSTER BY (identifier_type)
AS

-- Bank hash velocity: multiple claims sharing the same bank account
SELECT
  'bank_hash'                              AS identifier_type,
  ce.bank_hash                             AS identifier_value,
  COUNT(DISTINCT ce.claim_id)              AS distinct_claims,
  COUNT(DISTINCT ce.source_state)          AS distinct_states,
  COLLECT_SET(ce.claim_id)                 AS claim_ids,
  CASE WHEN COUNT(DISTINCT ce.claim_id) > 1 THEN TRUE ELSE FALSE END AS flagged
FROM claims_enriched ce
WHERE ce.bank_hash IS NOT NULL AND ce.bank_hash != ''
GROUP BY ce.bank_hash

UNION ALL

-- Device velocity: multiple claims from the same device
SELECT
  'device_id'                              AS identifier_type,
  ce.device_id                             AS identifier_value,
  COUNT(DISTINCT ce.claim_id)              AS distinct_claims,
  COUNT(DISTINCT ce.source_state)          AS distinct_states,
  COLLECT_SET(ce.claim_id)                 AS claim_ids,
  CASE WHEN COUNT(DISTINCT ce.claim_id) > 2 THEN TRUE ELSE FALSE END AS flagged
FROM claims_enriched ce
WHERE ce.device_id IS NOT NULL AND ce.device_id != ''
GROUP BY ce.device_id

UNION ALL

-- IP address velocity: many claims from the same IP
SELECT
  'ip_address'                             AS identifier_type,
  ce.ip_address                            AS identifier_value,
  COUNT(DISTINCT ce.claim_id)              AS distinct_claims,
  COUNT(DISTINCT ce.source_state)          AS distinct_states,
  COLLECT_SET(ce.claim_id)                 AS claim_ids,
  CASE WHEN COUNT(DISTINCT ce.claim_id) > 3 THEN TRUE ELSE FALSE END AS flagged
FROM claims_enriched ce
WHERE ce.ip_address IS NOT NULL AND ce.ip_address != ''
GROUP BY ce.ip_address;
