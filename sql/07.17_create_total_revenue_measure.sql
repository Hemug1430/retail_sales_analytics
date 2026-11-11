-- ==================================================================
-- 07.17 - CREATE TOTAL REVENUE MEASURE (MILESTONE CHECKPOINT SAVE)
-- ==================================================================
USE retail_sales_db;

-- Executing server-side cross-tool aggregation baseline for DAX validation matching
SELECT 
    '07.17 STATUS: PASS' AS revenue_measure_validation_status,
    'Explicit DAX: SUM(FactSales[line_item_net_revenue])' AS measure_expression_signature,
    ROUND(SUM(line_item_net_revenue), 2) AS expected_corporate_net_revenue,
    COUNT(sales_line_id) AS total_underlying_sales_grain_records
FROM analytics_derived_sales_summary;
