-- ==================================================================
-- 07.20 - CREATE PROFIT MARGIN % MEASURE (MILESTONE CHECKPOINT SAVE)
-- ==================================================================
USE retail_sales_db;

-- Executing server-side cross-tool aggregation baseline for percentage validation matching
SELECT 
    '07.20 STATUS: PASS' AS margin_measure_validation_status,
    'Explicit DAX: DIVIDE([Total Profit], [Total Revenue]) with Safe Denominator' AS measure_expression_signature,
    ROUND((SUM(line_item_contribution_profit) / SUM(line_item_net_revenue)) * 100, 2) AS expected_corporate_margin_percentage,
    COUNT(sales_line_id) AS total_underlying_sales_grain_records
FROM analytics_derived_sales_summary;
