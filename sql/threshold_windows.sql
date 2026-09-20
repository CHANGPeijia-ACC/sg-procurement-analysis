-- Tender totals just below and just above the S$90,000 tender threshold, for
-- shrinking windows. Tender level, ETT tenders only, matching README Finding 2.
-- Same counts as analysis.threshold_window_counts() on ETT tender totals.
-- An amount exactly at the threshold counts as above.

WITH tender_totals AS (
    -- awards summed per tender, because the threshold applies to a whole procurement
    SELECT
        tender_no,
        SUM(awarded_amt) AS awarded_amt
    FROM awards
    WHERE procurement_type = 'ETT'
    GROUP BY tender_no
),

windows(window_pct) AS (
    -- the window widths to report
    VALUES (0.10), (0.05), (0.02)
)

SELECT
    90000 AS threshold,
    w.window_pct,
    COUNT(*) FILTER (
        WHERE t.awarded_amt >= 90000 * (1 - w.window_pct) AND t.awarded_amt < 90000
    ) AS n_just_below,
    COUNT(*) FILTER (
        WHERE t.awarded_amt >= 90000 AND t.awarded_amt <= 90000 * (1 + w.window_pct)
    ) AS n_just_above
FROM windows AS w
CROSS JOIN tender_totals AS t
GROUP BY w.window_pct
ORDER BY w.window_pct DESC;
