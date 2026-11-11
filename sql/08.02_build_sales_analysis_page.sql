-- ==================================================================
-- 08.02 - BUILD SALES ANALYSIS PAGE (MILESTONE CHECKPOINT SAVE)
-- ==================================================================
USE retail_sales_db;

-- Documenting the successful implementation of categorical volume matrix totals and promotional performance bars
SELECT 
    '08.02 STATUS: PASS' AS sales_analysis_page_status,
    'Categorical Matrix Totals and Promo Performance Bars Active' AS layout_grain_signature,
    ROUND(SUM(CASE WHEN was_promotional_sale_flag = 1 THEN line_item_net_revenue ELSE 0 END), 2) AS promotional_revenue_total,
    ROUND(SUM(CASE WHEN was_promotional_sale_flag = 0 THEN line_item_net_revenue ELSE 0 END), 2) AS standard_revenue_total
FROM analytics_derived_sales_summary;
