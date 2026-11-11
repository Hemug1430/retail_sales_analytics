-- ==================================================================
-- 06.20 - CREATE RUNNING-TOTAL OUTPUTS (NATIVE SQL TIME WINDOWS)
-- ==================================================================
USE retail_sales_db;

-- Drop previous analytical view layers if they exist
DROP VIEW IF EXISTS vw_monthly_running_totals;

-- Compile a monthly category cumulative reporting view layer
CREATE VIEW vw_monthly_running_totals AS
SELECT 
    DATE_FORMAT(fs.order_date, '%Y-%m') AS sales_month,
    p.category AS category,
    SUM(fs.quantity * fs.unit_selling_price * (1 - COALESCE(fs.discount_pct, 0))) AS monthly_revenue,
    
    -- SQL Window function to calculate the running cumulative total
    SUM(SUM(fs.quantity * fs.unit_selling_price * (1 - COALESCE(fs.discount_pct, 0)))) 
        OVER (
            PARTITION BY p.category 
            ORDER BY DATE_FORMAT(fs.order_date, '%Y-%m')
        ) AS cumulative_running_total_revenue

FROM factsales fs
INNER JOIN core_products p ON fs.product_id = p.product_id
GROUP BY DATE_FORMAT(fs.order_date, '%Y-%m'), p.category;

-- Snapshot verification summary query run
SELECT 
    sales_month,
    category,
    ROUND(monthly_revenue, 2) AS current_month_net,
    ROUND(cumulative_running_total_revenue, 2) AS running_balance
FROM vw_monthly_running_totals
ORDER BY category, sales_month;
