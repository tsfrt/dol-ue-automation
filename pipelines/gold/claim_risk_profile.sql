CREATE OR REFRESH MATERIALIZED VIEW lanl.dol_ue_gold.claim_risk_profile
CLUSTER BY (source_state, risk_level)
AS
WITH claim_signals AS (
  SELECT
    ce.claim_id,
    ce.claimant_id,
    ce.source_state,
    ce.filed_date,
    ce.separation_mismatch,
    ce.form_fill_secs,
    ce.gt_is_fraud,
    ce.gt_fraud_scenario,
    ce.gt_bam_action_code,

    -- Certification signals (latest cert per claim)
    cert.work_search_count,
    cert.earnings_reported,
    cert.gt_is_fraud AS cert_gt_is_fraud,
    cert.gt_fraud_scenario AS cert_gt_fraud_scenario,

    -- Payment signals (any payment for this claim)
    pay.has_ach_return,
    pay.bank_owner_match,
    pay.amount AS payment_amount,

    -- Crossmatch alert counts by type
    SUM(CASE WHEN xa.alert_type = 'death_match'          THEN 1 ELSE 0 END) AS death_alerts,
    SUM(CASE WHEN xa.alert_type = 'incarceration_match'  THEN 1 ELSE 0 END) AS incarceration_alerts,
    SUM(CASE WHEN xa.alert_type = 'new_hire_match'       THEN 1 ELSE 0 END) AS new_hire_alerts,
    SUM(CASE WHEN xa.alert_type = 'other_benefit_overlap' THEN 1 ELSE 0 END) AS benefit_overlap_alerts

  FROM claims_enriched ce
  LEFT JOIN certifications_enriched cert
    ON ce.claim_id = cert.claim_id
  LEFT JOIN payments_enriched pay
    ON ce.claim_id = pay.claim_id
  LEFT JOIN crossmatch_alerts xa
    ON ce.claim_id = xa.claim_id
  GROUP BY
    ce.claim_id, ce.claimant_id, ce.source_state, ce.filed_date,
    ce.separation_mismatch, ce.form_fill_secs,
    ce.gt_is_fraud, ce.gt_fraud_scenario, ce.gt_bam_action_code,
    cert.work_search_count, cert.earnings_reported,
    cert.gt_is_fraud, cert.gt_fraud_scenario,
    pay.has_ach_return, pay.bank_owner_match, pay.amount
)

SELECT
  claim_id,
  claimant_id,
  source_state,
  filed_date,
  payment_amount,

  -- Rule-based risk score (0–100, capped)
  LEAST(100,
      CASE WHEN separation_mismatch          THEN 15 ELSE 0 END
    + CASE WHEN work_search_count < 3        THEN 10 ELSE 0 END
    + CASE WHEN has_ach_return               THEN 20 ELSE 0 END
    + CASE WHEN bank_owner_match = FALSE     THEN 15 ELSE 0 END
    + CASE WHEN death_alerts > 0             THEN 25 ELSE 0 END
    + CASE WHEN incarceration_alerts > 0     THEN 20 ELSE 0 END
    + CASE WHEN new_hire_alerts > 0          THEN 15 ELSE 0 END
    + CASE WHEN benefit_overlap_alerts > 0   THEN 10 ELSE 0 END
    + CASE WHEN form_fill_secs < 60          THEN 10 ELSE 0 END
  ) AS risk_score,

  CASE
    WHEN LEAST(100,
        CASE WHEN separation_mismatch        THEN 15 ELSE 0 END
      + CASE WHEN work_search_count < 3      THEN 10 ELSE 0 END
      + CASE WHEN has_ach_return             THEN 20 ELSE 0 END
      + CASE WHEN bank_owner_match = FALSE   THEN 15 ELSE 0 END
      + CASE WHEN death_alerts > 0           THEN 25 ELSE 0 END
      + CASE WHEN incarceration_alerts > 0   THEN 20 ELSE 0 END
      + CASE WHEN new_hire_alerts > 0        THEN 15 ELSE 0 END
      + CASE WHEN benefit_overlap_alerts > 0 THEN 10 ELSE 0 END
      + CASE WHEN form_fill_secs < 60        THEN 10 ELSE 0 END
    ) >= 50 THEN 'critical'
    WHEN LEAST(100,
        CASE WHEN separation_mismatch        THEN 15 ELSE 0 END
      + CASE WHEN work_search_count < 3      THEN 10 ELSE 0 END
      + CASE WHEN has_ach_return             THEN 20 ELSE 0 END
      + CASE WHEN bank_owner_match = FALSE   THEN 15 ELSE 0 END
      + CASE WHEN death_alerts > 0           THEN 25 ELSE 0 END
      + CASE WHEN incarceration_alerts > 0   THEN 20 ELSE 0 END
      + CASE WHEN new_hire_alerts > 0        THEN 15 ELSE 0 END
      + CASE WHEN benefit_overlap_alerts > 0 THEN 10 ELSE 0 END
      + CASE WHEN form_fill_secs < 60        THEN 10 ELSE 0 END
    ) >= 30 THEN 'high'
    WHEN LEAST(100,
        CASE WHEN separation_mismatch        THEN 15 ELSE 0 END
      + CASE WHEN work_search_count < 3      THEN 10 ELSE 0 END
      + CASE WHEN has_ach_return             THEN 20 ELSE 0 END
      + CASE WHEN bank_owner_match = FALSE   THEN 15 ELSE 0 END
      + CASE WHEN death_alerts > 0           THEN 25 ELSE 0 END
      + CASE WHEN incarceration_alerts > 0   THEN 20 ELSE 0 END
      + CASE WHEN new_hire_alerts > 0        THEN 15 ELSE 0 END
      + CASE WHEN benefit_overlap_alerts > 0 THEN 10 ELSE 0 END
      + CASE WHEN form_fill_secs < 60        THEN 10 ELSE 0 END
    ) >= 15 THEN 'medium'
    ELSE 'low'
  END AS risk_level,

  -- Reason codes as comma-separated string
  CONCAT_WS(', ',
    CASE WHEN separation_mismatch          THEN 'separation_mismatch' END,
    CASE WHEN work_search_count < 3        THEN 'work_search_deficient' END,
    CASE WHEN has_ach_return               THEN 'ach_return' END,
    CASE WHEN bank_owner_match = FALSE     THEN 'bank_owner_mismatch' END,
    CASE WHEN death_alerts > 0             THEN 'death_match' END,
    CASE WHEN incarceration_alerts > 0     THEN 'incarceration_match' END,
    CASE WHEN new_hire_alerts > 0          THEN 'new_hire_match' END,
    CASE WHEN benefit_overlap_alerts > 0   THEN 'benefit_overlap' END,
    CASE WHEN form_fill_secs < 60          THEN 'bot_speed_filing' END
  ) AS reason_codes,

  -- Ground truth for model evaluation
  COALESCE(cert_gt_is_fraud, gt_is_fraud) AS gt_is_fraud,
  COALESCE(cert_gt_fraud_scenario, gt_fraud_scenario) AS gt_fraud_scenario,
  gt_bam_action_code

FROM claim_signals;
