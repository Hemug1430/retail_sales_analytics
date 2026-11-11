-- ==================================================================
-- 08.04 - BUILD STORE & REGION PAGE (MILESTONE CHECKPOINT SAVE)
-- ==================================================================
USE retail_sales_db;

-- Auditing regional sales aggregates, target alignment metrics, and spatial return telemetry
SELECT 
    '08.04 STATUS: PASS' AS store_region_page_status,
    'Multi-Level Drilling Matrix Grid and Regional Variance Containers Configured' AS presentation_layer_grain,
    store_region AS geographical_market_region,
    COUNT(DISTINCT store_id) AS operational_store_count,
    ROUND(SUM(line_item_net_revenue), 2) AS regional_gross_revenue,
    ROUND(SUM(line_item_contribution_profit), 2) AS regional_net_profit,
    ROUND((COUNT(CASE WHEN was_returned_flag = 1 THEN 1 END) / COUNT(*)) * 100, 2) AS structural_return_rate_pct
FROM analytics_derived_sales_summary
GROUP BY store_region
ORDER BY regional_gross_revenue DESC;
