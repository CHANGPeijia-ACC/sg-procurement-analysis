-- Amount-weighted supplier concentration per agency: HHI and CR4.
-- Same result as analysis.concentration_by_group(df, ["agency"], min_awards=10).

WITH supplier_totals AS (
    -- one row per agency and supplier
    SELECT
        agency,
        supplier_name,
        SUM(awarded_amt) AS supplier_amt,
        COUNT(*)         AS n_awards
    FROM awards
    GROUP BY agency, supplier_name
),

shares AS (
    -- each supplier's share of its agency's total, in percent, and its rank
    -- inside the agency so that CR4 can add up the four largest
    SELECT
        agency,
        supplier_name,
        supplier_amt,
        n_awards,
        CASE
            WHEN SUM(supplier_amt) OVER (PARTITION BY agency) > 0
            THEN supplier_amt / SUM(supplier_amt) OVER (PARTITION BY agency) * 100
            ELSE 0
        END AS share_pct,
        ROW_NUMBER() OVER (PARTITION BY agency ORDER BY supplier_amt DESC) AS rank_in_agency
    FROM supplier_totals
)

SELECT
    agency,
    SUM(share_pct * share_pct)                                   AS hhi,
    COUNT(*)                                                     AS n_suppliers,
    SUM(supplier_amt)                                            AS total,
    SUM(CASE WHEN rank_in_agency <= 4 THEN share_pct ELSE 0 END) AS cr4,
    SUM(n_awards)                                                AS n_awards
FROM shares
GROUP BY agency
HAVING SUM(n_awards) >= 10
ORDER BY hhi DESC;
