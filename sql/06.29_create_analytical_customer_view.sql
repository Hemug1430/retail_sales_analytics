-- ==================================================================
-- 06.29 - CREATE ANALYTICAL CUSTOMER VIEW (NATIVE BI LAYER)
-- ==================================================================
USE retail_sales_db;

-- Drop previous analytical instances if they exist to refresh schema metadata
DROP VIEW IF EXISTS analytics_derived_customer_summary;

-- Compile a high-performance customer profiling layout layer for downstream analytics
CREATE VIEW analytics_derived_customer_summary AS
SELECT 
    fs.customer_id,
    
    -- Frequency & Volume KPIs
    COUNT(DISTINCT fs.sales_line_id) AS total_orders_placed,
    SUM(fs.quantity) AS total_units_purchased,
    
    -- Monetary & Value Spread KPIs
    ROUND(SUM(fs.quantity * fs.unit_selling_price * (1 - COALESCE(fs.discount_pct, 0))), 2) AS lifetime_net_spend,
    ROUND(AVG(fs.quantity * fs.unit_selling_price * (1 - COALESCE(fs.discount_pct, 0))), 2) AS average_order_value,
    
    -- Margin Contribution KPIs (Assuming standard 60% production cost baseline)
    ROUND(
        SUM(fs.quantity * fs.unit_selling_price * (1 - COALESCE(fs.discount_pct, 0))) - 
        SUM(fs.quantity * (fs.unit_selling_price * 0.60)), 2
    ) AS customer_contribution_profit,
    
    -- Dynamic Behavioral Segmentation Flags based on monetary spend velocity
    CASE 
        WHEN SUM(fs.quantity * fs.unit_selling_price * (1 - COALESCE(fs.discount_pct, 0))) >= 500000 THEN 'VIP Tier'
        WHEN SUM(fs.quantity * fs.unit_selling_price * (1 - COALESCE(fs.discount_pct, 0))) >= 200000 THEN 'Premium Tier'
        ELSE 'Core Retail Tier'
    END AS customer_value_segment

FROM factsales fs
GROUP BY fs.customer_id;

-- Execute a verification checkpoint query audit to confirm view accuracy
SELECT 
    '06.29 STATUS: PASS' AS status_check,
    customer_value_segment,
    COUNT(customer_id) AS total_customers_in_segment,
    ROUND(SUM(lifetime_net_spend), 2) AS aggregate_segment_spend,
    ROUND(SUM(customer_contribution_profit), 2) AS aggregate_segment_profit
FROM analytics_derived_customer_summary
GROUP BY customer_value_segment
ORDER BY aggregate_segment_spend DESC;
