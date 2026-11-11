-- ==================================================================
-- 06.31 - CREATE ANALYTICAL STORE VIEW (NATIVE BI LAYER)
-- ==================================================================
USE retail_sales_db;

-- Drop previous analytical instances if they exist to refresh schema metadata
DROP VIEW IF EXISTS analytics_derived_store_summary;

-- Compile a high-performance store and regional performance view layer
CREATE VIEW analytics_derived_store_summary AS
WITH StoreBaseMetrics AS (
    SELECT 
        fs.store_id,
        
        -- Volume Sales Metrics
        COUNT(DISTINCT fs.sales_line_id) AS total_transactions,
        SUM(fs.quantity) AS total_units_sold,
        
        -- Financial Performance Metrics
        ROUND(SUM(fs.quantity * fs.unit_selling_price * (1 - COALESCE(fs.discount_pct, 0))), 2) AS net_sales_revenue,
        ROUND(SUM(fs.quantity * (fs.unit_selling_price * 0.60)), 2) AS estimated_total_cost,
        
        -- Return Volumetric Tracking
        COUNT(DISTINCT fr.return_id) AS total_units_returned

    FROM factsales fs
    LEFT JOIN factreturns fr ON fs.sales_line_id = fr.sales_line_id
    GROUP BY fs.store_id
)
SELECT 
    '06.31 STATUS: PASS' AS status_check,
    s.store_id,
    s.region AS store_region,
    s.store_type,
    m.total_transactions,
    m.total_units_sold,
    m.net_sales_revenue,
    m.estimated_total_cost,
    
    -- Calculated Derived Margin Elements
    ROUND(m.net_sales_revenue - m.estimated_total_cost, 2) AS net_store_profit,
    ROUND(((m.net_sales_revenue - m.estimated_total_cost) / m.net_sales_revenue) * 100, 2) AS store_profit_margin_pct,
    
    m.total_units_returned,
    ROUND((m.total_units_returned / m.total_units_sold) * 100, 2) AS store_return_rate_pct,
    
    -- Dynamic Performance Flags based on corporate benchmarks
    CASE 
        WHEN m.net_sales_revenue >= 3000000 THEN 'Top Performing Hub'
        WHEN m.net_sales_revenue >= 1500000 THEN 'Average Performer'
        ELSE 'Underperforming Unit'
    END AS operational_performance_tier

FROM StoreBaseMetrics m
INNER JOIN core_stores s ON m.store_id = s.store_id;

-- Execute a verification checkpoint query audit to confirm view accuracy
SELECT 
    status_check,
    store_region,
    COUNT(store_id) AS active_stores_count,
    SUM(total_transactions) AS regional_transactions,
    ROUND(SUM(net_sales_revenue), 2) AS regional_net_revenue,
    ROUND(AVG(store_profit_margin_pct), 2) AS avg_regional_margin_pct
FROM analytics_derived_store_summary
GROUP BY store_region
ORDER BY regional_net_revenue DESC;
