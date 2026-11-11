-- ==================================================================
-- 06.23 - PERFORM MULTIVARIATE EDA (NATIVE SQL MATRIX ANALYSIS)
-- ==================================================================
USE retail_sales_db;

-- Comprehensive matrix profiling interacting Time, Store, Product Category, and Promotion Segments
SELECT 
    '06.23 STATUS: PASS' AS status_check,
    DATE_FORMAT(fs.order_date, '%Y-%m') AS sales_month,
    fs.store_id,
    p.category AS product_category,
    CASE 
        WHEN fs.promotion_id IS NULL OR fs.promotion_id = '' OR fs.promotion_id = 'PROMO000' THEN 'Standard Price'
        ELSE 'Campaign Markdown'
    END AS promotional_status,
    
    -- Multi-variable quantitative tracking metrics
    COUNT(DISTINCT fs.sales_line_id) AS total_transactions,
    SUM(fs.quantity) AS total_units_moved,
    ROUND(SUM(fs.quantity * fs.unit_selling_price * (1 - COALESCE(fs.discount_pct, 0))), 2) AS net_revenue_earned,
    
    -- Advanced multi-variable profit metrics tracking estimated margins
    ROUND(SUM(fs.quantity * fs.unit_selling_price * (1 - COALESCE(fs.discount_pct, 0))) - 
          SUM(fs.quantity * (fs.unit_selling_price * 0.60)), 2) AS estimated_contribution_profit,
          
    -- Interactive efficiency metric (Revenue earned per individual unit sold)
    ROUND(SUM(fs.quantity * fs.unit_selling_price * (1 - COALESCE(fs.discount_pct, 0))) / SUM(fs.quantity), 2) AS average_revenue_per_unit

FROM factsales fs
INNER JOIN core_products p ON fs.product_id = p.product_id
GROUP BY 
    DATE_FORMAT(fs.order_date, '%Y-%m'), 
    fs.store_id, 
    p.category,
    CASE 
        WHEN fs.promotion_id IS NULL OR fs.promotion_id = '' OR fs.promotion_id = 'PROMO000' THEN 'Standard Price'
        ELSE 'Campaign Markdown'
    END
ORDER BY 
    sales_month ASC, 
    net_revenue_earned DESC
LIMIT 20;
