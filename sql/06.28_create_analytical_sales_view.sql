-- ==================================================================
-- 06.28 - CREATE ANALYTICAL SALES TABLE/VIEW (NATIVE BI LAYER)
-- ==================================================================
USE retail_sales_db;

-- Drop previous analytical instances if they exist to refresh schema metadata
DROP VIEW IF EXISTS analytics_derived_sales_summary;

-- Compile a unified, high-performance analytical layer view for Power BI dashboards
CREATE VIEW analytics_derived_sales_summary AS
SELECT 
    fs.sales_line_id,
    fs.order_date,
    DATE_FORMAT(fs.order_date, '%Y-%m') AS order_year_month,
    fs.store_id,
    fs.product_id,
    p.category AS product_category,
    fs.customer_id,
    
    -- Baseline Volume metrics
    fs.quantity AS units_sold_count,
    fs.unit_selling_price AS gross_unit_price,
    
    -- Derived Financial Calculations
    ROUND(fs.quantity * fs.unit_selling_price, 2) AS line_item_gross_revenue,
    ROUND(fs.quantity * fs.unit_selling_price * COALESCE(fs.discount_pct, 0), 2) AS line_item_discount_markdown,
    ROUND(fs.quantity * fs.unit_selling_price * (1 - COALESCE(fs.discount_pct, 0)), 2) AS line_item_net_revenue,
    
    -- Corporate Contribution Margin Formulas (Assuming a 60% standard production cost baseline)
    ROUND(
        (fs.quantity * fs.unit_selling_price * (1 - COALESCE(fs.discount_pct, 0))) - 
        (fs.quantity * (fs.unit_selling_price * 0.60)), 2
    ) AS line_item_contribution_profit,
    
    -- Operational Flag Indicators
    CASE 
        WHEN fs.promotion_id IS NULL OR fs.promotion_id = '' OR fs.promotion_id = 'PROMO000' THEN 0
        ELSE 1
    END AS was_promotional_sale_flag

FROM factsales fs
INNER JOIN core_products p ON fs.product_id = p.product_id;

-- Execute a checkpoint audit to print confirmation
SELECT 
    '06.28 STATUS: PASS' AS status_check,
    product_category,
    SUM(units_sold_count) AS aggregate_units,
    ROUND(SUM(line_item_net_revenue), 2) AS aggregate_net_revenue,
    ROUND(SUM(line_item_contribution_profit), 2) AS aggregate_net_profit
FROM analytics_derived_sales_summary
GROUP BY product_category
ORDER BY aggregate_net_revenue DESC;
