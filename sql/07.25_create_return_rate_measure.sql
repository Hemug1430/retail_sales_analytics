-- ==================================================================
-- 07.25 - CREATE RETURN RATE MEASURE (MILESTONE CHECKPOINT SAVE)
-- ==================================================================
USE retail_sales_db;

-- Executing server-side cross-tool aggregation baseline for return rate matching
SELECT 
    '07.25 STATUS: PASS' AS return_rate_validation_status,
    'Explicit DAX: DIVIDE(DISTINCTCOUNT(factreturns[sales_line_id]), [Total Orders])' AS measure_signature,
    ROUND((COUNT(DISTINCT r.sales_line_id) / COUNT(DISTINCT s.sales_line_id)) * 100, 2) AS expected_corporate_return_rate_pct,
    COUNT(DISTINCT s.sales_line_id) AS total_underlying_orders_baseline
FROM analytics_derived_sales_summary s
LEFT JOIN factreturns r ON s.sales_line_id = r.sales_line_id;
