-- 06-software-delivery — flow metrics in SQL.
-- Loads: data/processed/issues.csv -> `issues`
--        (number, state, created_at, closed_at, cycle_days, n_labels, comments, open_age_days)
--        labels also available as nested array `labels` in the raw JSONL.

-- DORA-flavored KPI trio: median + P90 cycle time (BigQuery APPROX_QUANTILES)
SELECT
  COUNT(*) AS closed_issues,
  APPROX_QUANTILES(cycle_days, 100)[OFFSET(50)] AS median_cycle_days,
  APPROX_QUANTILES(cycle_days, 100)[OFFSET(90)] AS p90_cycle_days
FROM issues WHERE state = 'closed';

-- Triage pays: median open age, labeled vs unlabeled
SELECT n_labels > 0 AS labeled,
       COUNT(*) AS open_issues,
       APPROX_QUANTILES(open_age_days, 100)[OFFSET(50)] AS median_open_age_days
FROM issues WHERE state = 'open' GROUP BY labeled;

-- Chatter vs velocity: median cycle by comment band
SELECT
  CASE WHEN comments <= 0 THEN '0'
       WHEN comments <= 2 THEN '1-2'
       WHEN comments <= 10 THEN '3-10'
       ELSE '10+' END AS chat_band,
  COUNT(*) AS issues,
  APPROX_QUANTILES(cycle_days, 100)[OFFSET(50)] AS median_cycle_days
FROM issues WHERE state = 'closed' GROUP BY chat_band ORDER BY chat_band;

-- Label taxonomy (BigQuery UNNEST of raw labels array; SQLite users: preprocess in Python)
-- SELECT l, COUNT(*) AS issues, APPROX_QUANTILES(cycle_days, 100)[OFFSET(50)] AS med_cycle
-- FROM issues, UNNEST(labels) AS l WHERE state = 'closed' GROUP BY l ORDER BY issues DESC;
