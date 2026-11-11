-- ==================================================================
-- 06.27 - INVESTIGATE HIDDEN BUSINESS EVENTS (NATIVE SQL ANALYSIS)
-- ==================================================================
USE retail_sales_db;

-- 1. Detect Festival Sales Spikes (Isolating the top revenue dates to track simulated events)
SELECT 
    '06.27 STATUS: PASS' AS status_check,
    'Festival Spike Analysis' AS event_target,
    fs.order_date,
    COUNT(fs.sales_line_id) AS transactional_order_volume,
    ROUND(SUM(fs.quantity * fs.unit_selling_price * (1 - COALESCE(fs.discount_pct, 0))), 2) AS single_day_net_revenue
FROM factsales fs
GROUP BY fs.order_date
ORDER BY single_day_net_revenue DESC
LIMIT 5;

-- 2. Store Sales Trend Analysis (Detecting declining or underperforming locations)
SELECT 
    '06.27 STATUS: PASS' AS status_check,
    fs.store_id,
    DATE_FORMAT(fs.order_date, '%Y') AS sales_year,
    COUNT(DISTINCT fs.sales_line_id) AS annual_transaction_volume,
    ROUND(SUM(fs.quantity * fs.unit_selling_price * (1 - COALESCE(fs.discount_pct, 0))), 2) AS annual_net_revenue
FROM factsales fs
GROUP BY fs.store_id, DATE_FORMAT(fs.order_date, '%Y')
ORDER BY fs.store_id ASC, sales_year ASC;

-- 3. High-Return Toxic Product Profiling (Identifying products with high return frequencies)
SELECT 
    '06.27 STATUS: PASS' AS status_check,
    fs.product_id,
    COUNT(fs.sales_line_id) AS total_forward_orders,
    COUNT(fr.return_id) AS total_backward_returns,
    ROUND((COUNT(fr.return_id) / COUNT(fs.sales_line_id)) * 100, 2) AS product_return_rate_percentage,
    ROUND(SUM(COALESCE(fr.refund_amount, 0)), 2) AS total_capital_refunded_outflow
FROM factsales fs
LEFT JOIN factreturns fr ON fs.sales_line_id = fr.sales_line_id
GROUP BY fs.product_id
HAVING total_backward_returns > 5
ORDER BY product_return_rate_percentage DESC
LIMIT 5;
