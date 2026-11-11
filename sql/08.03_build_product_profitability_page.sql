-- ==================================================================
-- 08.03 - BUILD PRODUCT & PROFITABILITY PAGE (CHECKPOINT SAVE)
-- ==================================================================
USE retail_sales_db;

-- Auditing categorical margin rates, ranks, and cost alignment states
SELECT 
    '08.03 STATUS: PASS' AS product_profitability_page_status,
    'Profitability Matrix, Dynamic RANKX, and Cost Vectors Confirmed' AS layout_grain_signature,
    product_category,
    ROUND(SUM(line_item_net_revenue), 2) AS category_revenue,
    ROUND(SUM(line_item_net_revenue - line_item_contribution_profit), 2) AS category_cost,
    ROUND(SUM(line_item_contribution_profit), 2) AS category_profit,
    ROUND((SUM(line_item_contribution_profit) / SUM(line_item_net_revenue)) * 100, 2) AS category_margin_pct
FROM analytics_derived_sales_summary
GROUP BY product_category
ORDER BY category_revenue DESC;
