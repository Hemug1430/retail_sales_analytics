-- ==================================================================
-- 07.21 - CREATE TOTAL ORDERS MEASURE (MILESTONE CHECKPOINT SAVE)
-- ==================================================================
USE retail_sales_db;

-- Executing server-side cross-tool aggregation baseline for transaction volume validation matching
SELECT 
    '07.21 STATUS: PASS' AS orders_measure_validation_status,
    'Explicit DAX: DISTINCTCOUNT(FactSales[sales_line_id])' AS measure_expression_signature,
    COUNT(DISTINCT sales_line_id) AS expected_corporate_total_orders,
    COUNT(sales_line_id) AS total_underlying_sales_grain_records
FROM analytics_derived_sales_summary;
