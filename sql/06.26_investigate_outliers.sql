-- ==================================================================
-- 06.26 - INVESTIGATE OUTLIERS (NATIVE SQL STATISTICAL PROFILE)
-- ==================================================================
USE retail_sales_db;

-- Calculate boundary thresholds via IQR to isolate outlier fields
WITH PercentileStats AS (
    SELECT 
        MAX(CASE WHEN rank_pct <= 0.25 THEN unit_selling_price END) AS Q1,
        MAX(CASE WHEN rank_pct <= 0.75 THEN unit_selling_price END) AS Q3
    FROM (
        SELECT unit_selling_price, PERCENT_RANK() OVER (ORDER BY unit_selling_price) AS rank_pct
        FROM factsales
    ) AS RankedData
),
OutlierThresholds AS (
    SELECT 
        Q1, 
        Q3, 
        (Q3 - Q1) AS IQR,
        (Q1 - (1.5 * (Q3 - Q1))) AS Lower_Bound,
        (Q3 + (1.5 * (Q3 - Q1))) AS Upper_Bound
    FROM PercentileStats
)
SELECT 
    '06.26 STATUS: PASS' AS status_check,
    COUNT(fs.sales_line_id) AS total_orders_profiled,
    COUNT(CASE WHEN fs.unit_selling_price > t.Upper_Bound THEN 1 END) AS high_outlier_record_count,
    COUNT(CASE WHEN fs.unit_selling_price < t.Lower_Bound THEN 1 END) AS low_outlier_record_count,
    ROUND(MIN(fs.unit_selling_price), 2) AS min_price_observed,
    ROUND(MAX(fs.unit_selling_price), 2) AS max_price_observed,
    ROUND(t.Lower_Bound, 2) AS calculated_lower_threshold,
    ROUND(t.Upper_Bound, 2) AS calculated_upper_threshold
FROM factsales fs
CROSS JOIN OutlierThresholds t
GROUP BY t.Lower_Bound, t.Upper_Bound;
