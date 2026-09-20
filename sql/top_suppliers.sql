-- The ten suppliers with the largest total awarded amount.
-- Same result as analysis.top_suppliers(df, 10).
SELECT
    supplier_name,
    SUM(awarded_amt)       AS total_amt,
    COUNT(*)               AS n_awards,
    COUNT(DISTINCT agency) AS n_agencies
FROM awards
GROUP BY supplier_name
ORDER BY total_amt DESC
LIMIT 10;
