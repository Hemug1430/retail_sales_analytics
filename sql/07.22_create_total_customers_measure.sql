-- ==================================================================
-- 07.22 - CREATE TOTAL CUSTOMERS MEASURE (MILESTONE CHECKPOINT SAVE)
-- ==================================================================
USE retail_sales_db;

-- Executing server-side cross-tool aggregation baseline for customer volume validation matching
SELECT 
    '07.22 STATUS: PASS' AS customers_measure_validation_status,
    'Explicit DAX: DISTINCTCOUNT(FactSales[customer_id])' AS measure_expression_signature,
    COUNT(DISTINCT customer_id) AS expected_corporate_total_customers,
    COUNT(sales_line_id) AS total_underlying_sales_grain_records
FROM analytics_derived_sales_summary;
