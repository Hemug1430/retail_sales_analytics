USE retail_sales_db;

CREATE DATABASE IF NOT EXISTS analytics;

DROP VIEW IF EXISTS analytics.vw_average_order_value;

CREATE VIEW analytics.vw_average_order_value AS

WITH eligible_sales AS
(
    SELECT
        sales_line_id,
        order_id,
        order_date,
        quantity,
        unit_selling_price,
        discount_pct,

        ROUND(
            quantity
            * unit_selling_price
            * (1 - (discount_pct / 100)),
            2
        ) AS net_revenue

    FROM factsales

    WHERE order_id IS NOT NULL
      AND TRIM(order_id) <> ''
      AND order_status = 'Completed'
      AND quantity > 0
      AND unit_selling_price > 0
      AND discount_pct >= 0
      AND discount_pct <= 100
),

order_level_revenue AS
(
    SELECT
        order_id,
        SUM(net_revenue) AS order_net_revenue
    FROM eligible_sales
    GROUP BY order_id
),

aov_calculation AS
(
    SELECT
        SUM(order_net_revenue) AS eligible_net_revenue,
        COUNT(DISTINCT order_id) AS eligible_orders
    FROM order_level_revenue
)

SELECT
    eligible_net_revenue,
    eligible_orders,

    CASE
        WHEN eligible_orders > 0
        THEN ROUND(
            eligible_net_revenue / eligible_orders,
            2
        )
        ELSE 0
    END AS average_order_value

FROM aov_calculation;





USE retail_sales_db;

SELECT
    eligible_net_revenue,
    eligible_orders,
    average_order_value
FROM analytics.vw_average_order_value;



SELECT
    '01_ELIGIBLE_NET_REVENUE' AS check_name,
    eligible_net_revenue AS result_value
FROM analytics.vw_average_order_value

UNION ALL

SELECT
    '02_ELIGIBLE_ORDERS',
    eligible_orders
FROM analytics.vw_average_order_value

UNION ALL

SELECT
    '03_AVERAGE_ORDER_VALUE',
    average_order_value
FROM analytics.vw_average_order_value

UNION ALL

SELECT
    '04_NULL_AOV',
    COUNT(*)
FROM analytics.vw_average_order_value
WHERE average_order_value IS NULL

UNION ALL

SELECT
    '05_NEGATIVE_AOV',
    COUNT(*)
FROM analytics.vw_average_order_value
WHERE average_order_value < 0;