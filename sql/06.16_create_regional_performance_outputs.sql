USE retail_sales_db;

SELECT
    geography_level,
    performance_month,
    COUNT(*) AS output_rows,
    SUM(net_revenue) AS total_revenue,
    SUM(profit) AS total_profit,
    SUM(completed_orders) AS total_orders,
    SUM(customers) AS total_customers,
    SUM(return_events) AS total_return_events,
    SUM(revenue_target) AS total_revenue_target
FROM analytics.vw_regional_performance_outputs
GROUP BY geography_level, performance_month
ORDER BY performance_month, geography_level;



USE retail_sales_db;

SHOW CREATE VIEW analytics.vw_regional_performance_outputs;

## verifcation step


USE retail_sales_db;

SELECT
    geography_level,
    COUNT(*) AS output_rows,
    SUM(net_revenue) AS total_revenue,
    SUM(profit) AS total_profit,
    SUM(completed_orders) AS total_orders
FROM analytics.vw_regional_performance_outputs
WHERE performance_month = '2024-01-01'
GROUP BY geography_level
ORDER BY geography_level;