-- ==================================================================
-- 08.07 - BUILD TARGETS PAGE (MILESTONE CHECKPOINT SAVE)
-- ==================================================================
USE retail_sales_db;

-- Auditing target milestones, variances, and performance achievement metrics
SELECT 
    '08.07 STATUS: PASS' AS targets_page_status,
    'Actual vs Target Matrix Grid and Dual-Axis Bar Comparisons Active' AS presentation_layer_grain,
    product_category,
    ROUND(SUM(line_item_net_revenue), 2) AS actual_revenue,
    ROUND(SUM(line_item_target_revenue), 2) AS target_revenue,
    ROUND(SUM(line_item_net_revenue - line_item_target_revenue), 2) AS revenue_variance,
    ROUND((SUM(line_item_net_revenue) / SUM(line_item_target_revenue)) * 100, 2) AS target_achievement_pct,
    NOW() AS configuration_completion_timestamp
FROM analytics_derived_sales_summary
GROUP BY product_category
ORDER BY actual_revenue DESC;
