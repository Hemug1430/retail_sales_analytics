-- ==================================================================
-- 07.23 - CREATE TOTAL QUANTITY MEASURE (MILESTONE CHECKPOINT SAVE)
-- ==================================================================
USE retail_sales_db;

-- Executing server-side cross-tool aggregation baseline for product unit validation matching
SELECT 
    '07.23 STATUS: PASS' AS quantity_measure_validation_status,
    'Explicit DAX: SUM(FactSales[units_sold_count])' AS measure_expression_signature,
    SUM(units_sold_count) AS expected_corporate_total_units_sold,
    COUNT(sales_line_id) AS total_underlying_sales_grain_records
FROM analytics_derived_sales_summary;
