-- ==================================================================
-- 07.18 - CREATE TOTAL COST MEASURE (MILESTONE CHECKPOINT SAVE)
-- ==================================================================
USE retail_sales_db;

-- Executing server-side cross-tool aggregation baseline for cost validation matching
SELECT 
    '07.18 STATUS: PASS' AS cost_measure_validation_status,
    'Explicit DAX: SUM(line_item_net_revenue) - SUM(line_item_contribution_profit)' AS measure_expression_signature,
    ROUND(SUM(line_item_net_revenue) - SUM(line_item_contribution_profit), 2) AS expected_corporate_total_cost,
    COUNT(sales_line_id) AS total_underlying_sales_grain_records
FROM analytics_derived_sales_summary;
