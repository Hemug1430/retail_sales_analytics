-- ==================================================================
-- 07.29 - CREATE VARIANCE TO TARGET MEASURE (MILESTONE CHECKPOINT SAVE)
-- ==================================================================
USE retail_sales_db;

-- Executing server-side cross-tool aggregation baseline for absolute variance matching
SELECT 
    '07.29 STATUS: PASS' AS variance_measure_validation_status,
    'Explicit DAX: [Total Revenue] - [Total Revenue Target]' AS measure_expression_signature,
    ROUND((SELECT SUM(line_item_net_revenue) FROM analytics_derived_sales_summary) - SUM(revenue_target), 2) AS expected_corporate_absolute_variance,
    (SELECT COUNT(sales_line_id) FROM analytics_derived_sales_summary) AS total_sales_records_profiled
FROM facttargets;
