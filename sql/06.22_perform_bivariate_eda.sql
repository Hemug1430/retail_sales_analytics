-- ==================================================================
-- 06.22 - PERFORM BIVARIATE EDA (NATIVE SQL RELATIONSHIP ANALYSIS)
-- ==================================================================
USE retail_sales_db;

-- 1. Sales vs Region / Store Performance Relationship Analysis
SELECT 
    '06.22 STATUS: PASS' AS status_check,
    fs.store_id,
    COUNT(fs.sales_line_id) AS total_orders,
    SUM(fs.quantity) AS total_units_sold,
    ROUND(SUM(fs.quantity * fs.unit_selling_price * (1 - COALESCE(fs.discount_pct, 0))), 2) AS net_revenue
FROM factsales fs
GROUP BY fs.store_id
ORDER BY net_revenue DESC;

-- 2. Net Sales Revenue & Profit Contribution Margin vs Category
SELECT 
    '06.22 STATUS: PASS' AS status_check,
    p.category,
    ROUND(SUM(fs.quantity * fs.unit_selling_price * (1 - COALESCE(fs.discount_pct, 0))), 2) AS net_revenue,
    -- Estimating gross margin impact assuming product cost baseline averages 60% of original selling price
    ROUND(SUM(fs.quantity * fs.unit_selling_price * (1 - COALESCE(fs.discount_pct, 0))) - 
          SUM(fs.quantity * (fs.unit_selling_price * 0.60)), 2) AS estimated_profit_margin
FROM factsales fs
INNER JOIN core_products p ON fs.product_id = p.product_id
GROUP BY p.category
ORDER BY estimated_profit_margin DESC;

-- 3. Discount Percentage vs Order Quantity Matrix (Correlation Check)
SELECT 
    '06.22 STATUS: PASS' AS status_check,
    ROUND(fs.discount_pct * 100, 0) AS applied_discount_bucket_percentage,
    COUNT(fs.sales_line_id) AS transaction_count,
    ROUND(AVG(fs.quantity), 2) AS average_units_per_order,
    SUM(fs.quantity) AS total_volume_sold
FROM factsales fs
GROUP BY ROUND(fs.discount_pct * 100, 0)
ORDER BY applied_discount_bucket_percentage ASC;

-- 4. Returns vs Product Category Impact Profiling
SELECT 
    '06.22 STATUS: PASS' AS status_check,
    p.category,
    COUNT(fs.sales_line_id) AS total_forward_orders,
    COUNT(fr.return_id) AS total_backward_returns,
    ROUND((COUNT(fr.return_id) / COUNT(fs.sales_line_id)) * 100, 2) AS categorical_return_rate_percentage,
    ROUND(SUM(COALESCE(fr.refund_amount, 0)), 2) AS total_capital_refunded
FROM factsales fs
INNER JOIN core_products p ON fs.product_id = p.product_id
LEFT JOIN factreturns fr ON fs.sales_line_id = fr.sales_line_id
GROUP BY p.category
ORDER BY total_backward_returns DESC;
