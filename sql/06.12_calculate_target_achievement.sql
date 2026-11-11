USE retail_sales_db;

CREATE DATABASE IF NOT EXISTS analytics;

DROP VIEW IF EXISTS analytics.vw_target_achievement;

CREATE VIEW analytics.vw_target_achievement AS

WITH eligible_sales AS
(
    SELECT
        DATE_FORMAT(order_date, '%Y-%m-01') AS target_month,
        store_id,
        product_id,
        order_id,
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

sales_with_category AS
(
    SELECT
        es.target_month,
        es.store_id,
        cp.category,
        es.order_id,
        es.quantity,
        es.net_revenue

    FROM eligible_sales es

    INNER JOIN core_products cp
        ON es.product_id = cp.product_id
),

actuals AS
(
    SELECT
        target_month,
        store_id,
        category,

        SUM(net_revenue) AS actual_revenue,

        COUNT(DISTINCT order_id) AS actual_orders,

        SUM(quantity) AS actual_quantity

    FROM sales_with_category

    GROUP BY
        target_month,
        store_id,
        category
),

target_data AS
(
    SELECT
        DATE(target_month) AS target_month,
        store_id,
        category,

        revenue_target,
        profit_target,
        order_target,
        return_rate_target_pct

    FROM facttargets
)

SELECT

    t.target_month,

    t.store_id,

    t.category,

    /* =====================================================
       REVENUE
       ===================================================== */

    a.actual_revenue,

    t.revenue_target,

    CASE
        WHEN a.actual_revenue IS NOT NULL
        THEN ROUND(
            a.actual_revenue - t.revenue_target,
            2
        )
        ELSE NULL
    END AS revenue_variance,

    CASE
        WHEN a.actual_revenue IS NOT NULL
             AND t.revenue_target <> 0
        THEN ROUND(
            (
                a.actual_revenue
                / t.revenue_target
            ) * 100,
            2
        )
        ELSE NULL
    END AS revenue_achievement_pct,

    /* =====================================================
       ORDERS
       ===================================================== */

    a.actual_orders,

    t.order_target,

    CASE
        WHEN a.actual_orders IS NOT NULL
        THEN
            a.actual_orders - t.order_target
        ELSE NULL
    END AS order_variance,

    CASE
        WHEN a.actual_orders IS NOT NULL
             AND t.order_target <> 0
        THEN ROUND(
            (
                a.actual_orders
                / t.order_target
            ) * 100,
            2
        )
        ELSE NULL
    END AS order_achievement_pct,

    /* =====================================================
       PROFIT
       ===================================================== */

    CAST(NULL AS DECIMAL(18,2))
        AS actual_profit,

    t.profit_target,

    CAST(NULL AS DECIMAL(18,2))
        AS profit_variance,

    CAST(NULL AS DECIMAL(18,2))
        AS profit_achievement_pct,

    /* =====================================================
       RETURN RATE
       ===================================================== */

    CAST(NULL AS DECIMAL(18,4))
        AS actual_return_rate_pct,

    t.return_rate_target_pct,

    CAST(NULL AS DECIMAL(18,4))
        AS return_rate_variance,

    CAST(NULL AS DECIMAL(18,4))
        AS return_rate_achievement_pct

FROM target_data t

LEFT JOIN actuals a
    ON a.target_month = DATE_FORMAT(
        t.target_month,
        '%Y-%m-01'
    )

   AND a.store_id = t.store_id

   AND a.category = t.category;
   
   
   
   
   ## verification check table
   
   
   USE retail_sales_db;

SELECT
    target_month,
    store_id,
    category,
    actual_revenue,
    revenue_target,
    revenue_variance,
    revenue_achievement_pct,
    actual_orders,
    order_target,
    order_variance,
    order_achievement_pct,
    actual_profit,
    profit_target,
    profit_variance,
    profit_achievement_pct,
    actual_return_rate_pct,
    return_rate_target_pct,
    return_rate_variance,
    return_rate_achievement_pct
FROM analytics.vw_target_achievement
ORDER BY
    target_month,
    store_id,
    category;
    
    
    ## Final validation 
    SELECT
    '01_TOTAL_TARGET_ROWS' AS check_name,
    COUNT(*) AS result_value
FROM analytics.vw_target_achievement

UNION ALL

SELECT
    '02_REVENUE_TARGET_ROWS',
    COUNT(*)
FROM analytics.vw_target_achievement
WHERE revenue_target IS NOT NULL

UNION ALL

SELECT
    '03_ORDER_TARGET_ROWS',
    COUNT(*)
FROM analytics.vw_target_achievement
WHERE order_target IS NOT NULL

UNION ALL

SELECT
    '04_INVALID_REVENUE_ACHIEVEMENT',
    COUNT(*)
FROM analytics.vw_target_achievement
WHERE revenue_target = 0
  AND revenue_achievement_pct IS NOT NULL

UNION ALL

SELECT
    '05_INVALID_ORDER_ACHIEVEMENT',
    COUNT(*)
FROM analytics.vw_target_achievement
WHERE order_target = 0
  AND order_achievement_pct IS NOT NULL;
   