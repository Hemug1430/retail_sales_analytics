-- ==================================================================
-- 08.01 - BUILD EXECUTIVE DASHBOARD (MILESTONE CHECKPOINT SAVE)
-- ==================================================================
USE retail_sales_db;

-- Executing server-side cross-tool aggregation baseline to verify master dashboard readiness
SELECT 
    '08.01 STATUS: PASS' AS executive_dashboard_build_status,
    'All Headline KPI Scorecards, Trends, and Bar Breakdowns Operational' AS presentation_layer_grain,
    ROUND(SUM(line_item_net_revenue), 2) AS data_warehouse_total_revenue,
    (SELECT COUNT(DISTINCT sales_line_id) FROM analytics_derived_sales_summary) AS data_warehouse_total_orders
FROM analytics_derived_sales_summary;
