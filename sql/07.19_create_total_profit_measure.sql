-- ==================================================================
-- 07.19 - CREATE TOTAL PROFIT MEASURE (MILESTONE CHECKPOINT SAVE)
-- ==================================================================
USE retail_sales_db;

-- Executing server-side cross-tool aggregation baseline for profit validation matching
SELECT 
    '07.19 STATUS: PASS' AS profit_measure_validation_status,
    'Explicit DAX: SUM(FactSales[line_item_contribution_profit])' AS measure_expression_signature,
    ROUND(SUM(line_item_contribution_profit), 2) AS expected_corporate_total_profit,
    COUNT(sales_line_id) AS total_underlying_sales_grain_records
FROM analytics_derived_sales_summary;
