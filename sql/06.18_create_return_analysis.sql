-- ==================================================================
-- 06.18 - CREATE RETURN ANALYSIS OUTPUTS (NATIVE SQL)
-- ==================================================================
USE retail_sales_db;

-- Drop previous analytical structures if they exist
DROP VIEW IF EXISTS vw_return_financial_impact_analytics;

-- Compile a reusable reporting view layer for Power BI dashboard connectivity
CREATE VIEW vw_return_financial_impact_analytics AS
SELECT 
    fs.store_id,
    fs.product_id,
    fr.return_reason,
    fr.return_status,
    
    -- Volumetric quantities metrics
    COUNT(DISTINCT fs.sales_line_id) AS total_forward_orders_placed,
    COUNT(DISTINCT fr.return_id) AS total_backward_units_returned,
    (COUNT(DISTINCT fr.return_id) / COUNT(DISTINCT fs.sales_line_id)) * 100 AS product_return_rate_percentage,
    
    -- Cash flow return metrics
    SUM(fs.quantity * fs.unit_selling_price * (1 - COALESCE(fs.discount_pct, 0))) AS original_gross_sales,
    SUM(COALESCE(fr.refund_amount, 0)) AS total_capital_refunded_outflow

FROM factsales fs
LEFT JOIN factreturns fr ON fs.sales_line_id = fr.sales_line_id
GROUP BY fs.store_id, fs.product_id, fr.return_reason, fr.return_status;

-- Summary test audit checking view outputs
SELECT 
    store_id,
    product_id,
    COALESCE(return_reason, 'No Return Logs') AS reason_profile,
    total_forward_orders_placed AS orders,
    total_backward_units_returned AS returns,
    ROUND(product_return_rate_percentage, 2) AS return_rate_pct,
    ROUND(total_capital_refunded_outflow, 2) AS cash_refunded
FROM vw_return_financial_impact_analytics
ORDER BY total_backward_units_returned DESC
LIMIT 10;
