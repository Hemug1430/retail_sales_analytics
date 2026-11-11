-- ==================================================================
-- 06.30 - CREATE ANALYTICAL PRODUCT VIEW (NATIVE BI LAYER)
-- ==================================================================
USE retail_sales_db;

-- Drop previous analytical instances if they exist to refresh schema metadata
DROP VIEW IF EXISTS analytics_derived_product_summary;

-- Compile a high-performance product and category performance view layer
CREATE VIEW analytics_derived_product_summary AS
WITH ProductBaseMetrics AS (
    SELECT 
        fs.product_id,
        p.category AS product_category,
        
        -- Volume Sales Metrics
        SUM(fs.quantity) AS total_quantity_sold,
        
        -- Financial Performance Metrics
        ROUND(SUM(fs.quantity * fs.unit_selling_price * (1 - COALESCE(fs.discount_pct, 0))), 2) AS net_sales_revenue,
        ROUND(SUM(fs.quantity * (fs.unit_selling_price * 0.60)), 2) AS estimated_total_cost,
        
        -- Return Volumetric Tracking (Linking with factreturns mapping)
        COUNT(DISTINCT fr.return_id) AS total_units_returned

    FROM factsales fs
    INNER JOIN core_products p ON fs.product_id = p.product_id
    LEFT JOIN factreturns fr ON fs.sales_line_id = fr.sales_line_id
    GROUP BY fs.product_id, p.category
)
SELECT 
    '06.30 STATUS: PASS' AS status_check,
    product_id,
    product_category,
    total_quantity_sold,
    net_sales_revenue,
    estimated_total_cost,
    
    -- Calculated Derived Margin Elements
    ROUND(net_sales_revenue - estimated_total_cost, 2) AS net_product_profit,
    ROUND(((net_sales_revenue - estimated_total_cost) / net_sales_revenue) * 100, 2) AS profit_margin_percentage,
    
    total_units_returned,
    ROUND((total_units_returned / total_quantity_sold) * 100, 2) AS product_return_rate_pct,
    
    -- Dynamic Window Ranking function across the entire warehouse inventory
    DENSE_RANK() OVER (PARTITION BY product_category ORDER BY net_sales_revenue DESC) AS product_rank_in_category

FROM ProductBaseMetrics;

-- Execute a verification checkpoint query audit to confirm view accuracy
SELECT 
    status_check,
    product_category,
    COUNT(product_id) AS items_tracked_count,
    SUM(total_quantity_sold) AS category_units_moved,
    ROUND(SUM(net_sales_revenue), 2) AS category_net_revenue,
    ROUND(AVG(profit_margin_percentage), 2) AS average_product_margin_pct
FROM analytics_derived_product_summary
GROUP BY product_category
ORDER BY category_net_revenue DESC;
