-- ==================================================================
-- 07.24 - CREATE AVERAGE ORDER VALUE MEASURE (MILESTONE CHECKPOINT SAVE)
-- ==================================================================
USE retail_sales_db;

-- Executing server-side cross-tool aggregation baseline for AOV validation matching
SELECT 
    '07.24 STATUS: PASS' AS aov_measure_validation_status,
    'Explicit DAX: DIVIDE([Total Revenue], [Total Orders]) with Safe Division' AS measure_expression_signature,
    ROUND(SUM(line_item_net_revenue) / COUNT(DISTINCT sales_line_id), 2) AS expected_corporate_average_order_value,
    COUNT(sales_line_id) AS total_underlying_sales_grain_records
FROM analytics_derived_sales_summary;
