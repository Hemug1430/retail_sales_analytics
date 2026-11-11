USE retail_sales_db;

CREATE DATABASE IF NOT EXISTS analytics;

DROP VIEW IF EXISTS analytics.vw_growth_metrics;

CREATE VIEW analytics.vw_growth_metrics AS

WITH eligible_sales AS
(
    SELECT
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

/* =========================================================
   MONTHLY NET REVENUE
   ========================================================= */

monthly_revenue AS
(
    SELECT
        DATE_FORMAT(order_date, '%Y-%m-01') AS period_start,

        SUM(net_revenue) AS net_revenue

    FROM eligible_sales

    GROUP BY
        DATE_FORMAT(order_date, '%Y-%m-01')
),

monthly_growth AS
(
    SELECT
        'MoM' AS growth_type,

        period_start,

        net_revenue,

        (
            SELECT
                m2.net_revenue
            FROM monthly_revenue m2
            WHERE m2.period_start =
                  DATE_FORMAT(
                      DATE_SUB(
                          STR_TO_DATE(
                              m1.period_start,
                              '%Y-%m-%d'
                          ),
                          INTERVAL 1 MONTH
                      ),
                      '%Y-%m-%d'
                  )
        ) AS prior_period_value

    FROM monthly_revenue m1
),

/* =========================================================
   QUARTERLY NET REVENUE
   ========================================================= */

quarterly_revenue AS
(
    SELECT
        CAST(
            CONCAT(
                YEAR(order_date),
                '-',
                LPAD(
                    ((QUARTER(order_date) - 1) * 3) + 1,
                    2,
                    '0'
                ),
                '-01'
            ) AS DATE
        ) AS period_start,

        SUM(net_revenue) AS net_revenue

    FROM eligible_sales

    GROUP BY
        YEAR(order_date),
        QUARTER(order_date)
),

quarterly_growth AS
(
    SELECT
        'QoQ' AS growth_type,

        period_start,

        net_revenue,

        (
            SELECT
                q2.net_revenue
            FROM quarterly_revenue q2
            WHERE q2.period_start =
                  DATE_SUB(
                      q1.period_start,
                      INTERVAL 3 MONTH
                  )
        ) AS prior_period_value

    FROM quarterly_revenue q1
),

/* =========================================================
   YEARLY NET REVENUE
   ========================================================= */

yearly_revenue AS
(
    SELECT
        CAST(
            CONCAT(
                YEAR(order_date),
                '-01-01'
            ) AS DATE
        ) AS period_start,

        SUM(net_revenue) AS net_revenue

    FROM eligible_sales

    GROUP BY
        YEAR(order_date)
),

yearly_growth AS
(
    SELECT
        'YoY' AS growth_type,

        period_start,

        net_revenue,

        (
            SELECT
                y2.net_revenue
            FROM yearly_revenue y2
            WHERE y2.period_start =
                  DATE_SUB(
                      y1.period_start,
                      INTERVAL 1 YEAR
                  )
        ) AS prior_period_value

    FROM yearly_revenue y1
),

/* =========================================================
   COMBINE ALL GROWTH PERIODS
   ========================================================= */

combined_growth AS
(
    SELECT
        growth_type,
        period_start,
        net_revenue,
        prior_period_value
    FROM monthly_growth

    UNION ALL

    SELECT
        growth_type,
        period_start,
        net_revenue,
        prior_period_value
    FROM quarterly_growth

    UNION ALL

    SELECT
        growth_type,
        period_start,
        net_revenue,
        prior_period_value
    FROM yearly_growth
)

SELECT
    growth_type,

    period_start,

    net_revenue AS current_period_value,

    prior_period_value,

    CASE
        WHEN prior_period_value IS NOT NULL
        THEN ROUND(
            net_revenue - prior_period_value,
            2
        )
        ELSE NULL
    END AS absolute_change,

    CASE
        WHEN prior_period_value IS NOT NULL
             AND prior_period_value <> 0
        THEN ROUND(
            (
                (net_revenue - prior_period_value)
                / prior_period_value
            ) * 100,
            2
        )
        ELSE NULL
    END AS growth_percentage

FROM combined_growth;



USE retail_sales_db;

SELECT
    growth_type,
    period_start,
    current_period_value,
    prior_period_value,
    absolute_change,
    growth_percentage
FROM analytics.vw_growth_metrics
ORDER BY
    growth_type,
    period_start;
    
    
    
    USE retail_sales_db;

SELECT
    '01_TOTAL_ROWS' AS check_name,
    COUNT(*) AS result_value
FROM analytics.vw_growth_metrics

UNION ALL

SELECT
    '02_MOM_ROWS',
    COUNT(*)
FROM analytics.vw_growth_metrics
WHERE growth_type = 'MoM'

UNION ALL

SELECT
    '03_QOQ_ROWS',
    COUNT(*)
FROM analytics.vw_growth_metrics
WHERE growth_type = 'QoQ'

UNION ALL

SELECT
    '04_YOY_ROWS',
    COUNT(*)
FROM analytics.vw_growth_metrics
WHERE growth_type = 'YoY'

UNION ALL

SELECT
    '05_INVALID_GROWTH_COMPARISONS',
    COUNT(*)
FROM analytics.vw_growth_metrics
WHERE prior_period_value IS NULL
  AND (
        absolute_change IS NOT NULL
        OR growth_percentage IS NOT NULL
      )

UNION ALL

SELECT
    '06_ZERO_PRIOR_WITH_GROWTH',
    COUNT(*)
FROM analytics.vw_growth_metrics
WHERE prior_period_value = 0
  AND growth_percentage IS NOT NULL;