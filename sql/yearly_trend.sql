-- Awarded amount, number of awards and distinct suppliers per fiscal year.
-- Same result as analysis.yearly_trend().
SELECT
    fiscal_year,
    SUM(awarded_amt)              AS total_amt,
    COUNT(*)                      AS n_awards,
    COUNT(DISTINCT supplier_name) AS n_suppliers
FROM awards
GROUP BY fiscal_year
ORDER BY fiscal_year;
