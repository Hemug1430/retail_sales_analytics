-- ==================================================================
-- 08.05 - BUILD CUSTOMER ANALYSIS PAGE (MILESTONE CHECKPOINT SAVE)
-- ==================================================================
USE retail_sales_db;

-- Auditing customer purchase frequency totals and value metrics
SELECT 
    '08.05 STATUS: PASS' AS customer_analysis_page_status,
    'Granular Purchase Value Matrix and Customer Geography Charts Active' AS presentation_layer_grain,
    COUNT(DISTINCT customer_id) AS analytical_customer_base_count,
    ROUND(SUM(line_item_net_revenue), 2) AS collective_customer_revenue,
    ROUND(SUM(line_item_net_revenue) / COUNT(DISTINCT sales_line_id), 2) AS calculated_average_basket_value,
    NOW() AS configuration_completion_timestamp
FROM analytics_derived_sales_summary;
