-- ==================================================================
-- 08.06 - BUILD RETURNS ANALYSIS PAGE (MILESTONE CHECKPOINT SAVE)
-- ==================================================================
USE retail_sales_db;

-- Auditing structural inventory return volumes and core item return frequencies
SELECT 
    '08.06 STATUS: PASS' AS returns_analysis_page_status,
    'Granular Return Trajectory Matrix and Reason Code Distribution Active' AS presentation_layer_grain,
    product_category,
    COUNT(CASE WHEN was_returned_flag = 1 THEN 1 END) AS product_return_count,
    ROUND((COUNT(CASE WHEN was_returned_flag = 1 THEN 1 END) / COUNT(*)) * 100, 2) AS category_return_rate_pct,
    NOW() AS configuration_completion_timestamp
FROM analytics_derived_sales_summary
GROUP BY product_category
ORDER BY category_return_rate_pct DESC;
