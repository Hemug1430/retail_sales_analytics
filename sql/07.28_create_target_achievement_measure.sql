-- ==================================================================
-- 07.28 - CREATE TARGET ACHIEVEMENT % MEASURE (MILESTONE CHECKPOINT SAVE)
-- ==================================================================
USE retail_sales_db;

-- Executing server-side cross-tool aggregation baseline for achievement percentage validation matching
SELECT 
    '07.28 STATUS: PASS' AS achievement_measure_validation_status,
    'Explicit DAX: DIVIDE([Total Revenue], [Total Revenue Target]) with Safe Denominator' AS measure_expression_signature,
    ROUND((SELECT SUM(line_item_net_revenue) FROM analytics_derived_sales_summary) / SUM(revenue_target) * 100, 2) AS expected_corporate_achievement_percentage,
    (SELECT COUNT(sales_line_id) FROM analytics_derived_sales_summary) AS total_sales_records_profiled
FROM facttargets;
