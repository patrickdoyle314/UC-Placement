-- State release ranks, year-over-year change and cumulative share, FY2015-FY2025.
--
-- Uses: two CTEs; window functions SUM() OVER (share of the national total, running share),
-- RANK() OVER (rank within each year) and LAG() OVER (change from the year before).
-- Source: the Week 1 table as parquet (python src/measure.py writes it). Run: python src/run_sql.py

WITH state_year AS (
    -- 50 states and DC, one row per state and fiscal year
    SELECT fiscal_year, state, state_name, releases
    FROM read_parquet('data/processed/releases_by_fy_geo.parquet')
    WHERE geo_level = 'state'
      AND state NOT IN ('PR', 'VI')
      AND fiscal_year BETWEEN 2015 AND 2025
),
ranked AS (
    SELECT
        fiscal_year,
        state,
        state_name,
        releases,
        releases::DOUBLE / SUM(releases) OVER (PARTITION BY fiscal_year)        AS share,
        RANK() OVER (PARTITION BY fiscal_year ORDER BY releases DESC)          AS rank_in_year
    FROM state_year
)
SELECT
    fiscal_year,
    state,
    state_name,
    releases,
    ROUND(share, 4)                                                             AS share,
    rank_in_year,
    LAG(rank_in_year) OVER (PARTITION BY state ORDER BY fiscal_year) - rank_in_year
                                                                                AS rank_change,
    ROUND(share - LAG(share) OVER (PARTITION BY state ORDER BY fiscal_year), 4) AS share_change,
    ROUND(SUM(share) OVER (PARTITION BY fiscal_year ORDER BY releases DESC, state
                           ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW), 4)
                                                                                AS cumulative_share
FROM ranked
ORDER BY fiscal_year, rank_in_year, state;
