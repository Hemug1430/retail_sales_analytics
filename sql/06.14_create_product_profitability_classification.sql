USE retail_sales_db;

CREATE DATABASE IF NOT EXISTS analytics;

DROP VIEW IF EXISTS analytics.vw_product_profitability_classification;

CREATE VIEW analytics.vw_product_profitability_classification AS

WITH product_summary AS
(
    SELECT
        product_id,

        SUM(net_revenue) AS net_revenue,

        SUM(total_cost) AS total_cost,

        SUM(profit) AS profit,

        SUM(quantity) AS units_sold,

        COUNT(DISTINCT order_id) AS completed_orders

    FROM analytics.vw_sales_profit

    WHERE order_status = 'Completed'
      AND product_id IS NOT NULL

    GROUP BY
        product_id
),

product_with_master AS
(
    SELECT
        cp.product_id,
        cp.product_name,
        cp.category,
        cp.subcategory,
        cp.brand,

        COALESCE(
            ps.net_revenue,
            0
        ) AS net_revenue,

        ps.total_cost,
        ps.profit,

        COALESCE(
            ps.units_sold,
            0
        ) AS units_sold,

        COALESCE(
            ps.completed_orders,
            0
        ) AS completed_orders

    FROM core_products cp

    LEFT JOIN product_summary ps
        ON cp.product_id = ps.product_id
),

revenue_ranked AS
(
    SELECT
        pwm.*,

        SUM(net_revenue) OVER () AS total_revenue,

        SUM(net_revenue) OVER
        (
            ORDER BY
                net_revenue DESC,
                product_id
            ROWS BETWEEN UNBOUNDED PRECEDING
            AND CURRENT ROW
        ) AS cumulative_revenue

    FROM product_with_master pwm
),

classified AS
(
    SELECT
        product_id,
        product_name,
        category,
        subcategory,
        brand,

        net_revenue,
        total_cost,
        profit,

        CASE
            WHEN net_revenue = 0
                THEN NULL

            WHEN profit IS NULL
                THEN NULL

            ELSE
                (profit / net_revenue) * 100
        END AS profit_margin_pct,

        units_sold,
        completed_orders,

        CASE
            WHEN total_revenue = 0
                THEN NULL

            WHEN cumulative_revenue / total_revenue <= 0.70
                THEN 'A'

            WHEN cumulative_revenue / total_revenue <= 0.90
                THEN 'B'

            ELSE 'C'
        END AS revenue_abc_band

    FROM revenue_ranked
)

SELECT
    product_id,
    product_name,
    category,
    subcategory,
    brand,

    net_revenue,
    total_cost,
    profit,
    profit_margin_pct,

    units_sold,
    completed_orders,

    revenue_abc_band,

    CASE
        WHEN revenue_abc_band = 'A'
            THEN 'High Revenue'

        WHEN revenue_abc_band = 'B'
            THEN 'Medium Revenue'

        WHEN revenue_abc_band = 'C'
            THEN 'Low Revenue'

        ELSE 'Not Available'
    END AS revenue_group,

    CASE
        WHEN profit IS NULL
            THEN 'Not Available'

        WHEN profit < 0
            THEN 'Loss'

        WHEN profit_margin_pct < 10
            THEN 'Low'

        WHEN profit_margin_pct <= 25
            THEN 'Medium'

        WHEN profit_margin_pct <= 40
            THEN 'Healthy'

        ELSE 'High'
    END AS margin_band,

    CASE
        WHEN profit IS NULL
            THEN 'Profitability Not Available'

        WHEN profit < 0
            THEN 'Loss-Making'

        WHEN profit_margin_pct < 10
            THEN 'Low Margin'

        WHEN profit_margin_pct <= 25
            THEN 'Medium Margin'

        WHEN profit_margin_pct <= 40
            THEN 'Healthy Margin'

        ELSE 'High Margin'
    END AS profitability_classification

FROM classified;



## verificaiton
USE retail_sales_db;

SELECT
    revenue_abc_band,
    revenue_group,
    margin_band,
    COUNT(*) AS product_count
FROM analytics.vw_product_profitability_classification
GROUP BY
    revenue_abc_band,
    revenue_group,
    margin_band
ORDER BY
    revenue_abc_band,
    margin_band;