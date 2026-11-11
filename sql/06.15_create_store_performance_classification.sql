USE retail_sales_db;

CREATE DATABASE IF NOT EXISTS analytics;

DROP VIEW IF EXISTS analytics.vw_store_performance_classification;

CREATE VIEW analytics.vw_store_performance_classification AS

WITH
/* ============================================================
   1. Monthly completed sales by store
   ============================================================ */
monthly_sales AS
(
    SELECT
        DATE_FORMAT(fs.order_date, '%Y-%m-01') AS performance_month,
        fs.store_id,

        SUM(
            fs.quantity *
            fs.unit_selling_price *
            (
                1 - COALESCE(fs.discount_pct, 0) / 100
            )
        ) AS revenue,

        SUM(fs.quantity) AS units,

        COUNT(DISTINCT fs.order_id) AS completed_orders,

        COUNT(
            DISTINCT
            CASE
                WHEN fs.customer_id IS NOT NULL
                    THEN fs.customer_id
            END
        ) AS customers

    FROM factsales fs

    WHERE fs.order_status = 'Completed'

    GROUP BY
        DATE_FORMAT(fs.order_date, '%Y-%m-01'),
        fs.store_id
),

/* ============================================================
   2. Monthly profit by store
      Uses the governed sales-profit analytics view.
   ============================================================ */
monthly_profit AS
(
    SELECT
        DATE_FORMAT(sp.order_date, '%Y-%m-01') AS performance_month,
        sp.product_id,
        fs.store_id,

        SUM(sp.profit) AS profit,

        SUM(sp.total_cost) AS total_cost

    FROM analytics.vw_sales_profit sp

    INNER JOIN factsales fs
        ON sp.sales_line_id = fs.sales_line_id

    WHERE sp.order_status = 'Completed'
      AND fs.order_status = 'Completed'

    GROUP BY
        DATE_FORMAT(sp.order_date, '%Y-%m-01'),
        sp.product_id,
        fs.store_id
),

monthly_store_profit AS
(
    SELECT
        performance_month,
        store_id,

        SUM(profit) AS profit,

        SUM(total_cost) AS total_cost

    FROM monthly_profit

    GROUP BY
        performance_month,
        store_id
),

/* ============================================================
   3. Monthly return metrics
      Returns are attributed to the original selling store,
      not processed_store_id.
   ============================================================ */
monthly_returns AS
(
    SELECT
        DATE_FORMAT(fs.order_date, '%Y-%m-01') AS performance_month,
        fs.store_id,

        SUM(
            CASE
                WHEN fr.return_status = 'Refunded'
                    THEN fr.quantity_returned
                ELSE 0
            END
        ) AS refunded_quantity,

        SUM(
            CASE
                WHEN fr.return_status = 'Refunded'
                    THEN COALESCE(fr.refund_amount, 0)
                ELSE 0
            END
        ) AS refunded_amount,

        COUNT(
            DISTINCT
            CASE
                WHEN fr.return_status = 'Refunded'
                    THEN fr.return_id
            END
        ) AS refunded_returns

    FROM factsales fs

    INNER JOIN factreturns fr
        ON fs.sales_line_id = fr.sales_line_id

    WHERE fs.order_status = 'Completed'

    GROUP BY
        DATE_FORMAT(fs.order_date, '%Y-%m-01'),
        fs.store_id
),

/* ============================================================
   4. Monthly sold quantity
   ============================================================ */
monthly_units AS
(
    SELECT
        DATE_FORMAT(order_date, '%Y-%m-01') AS performance_month,
        store_id,
        SUM(quantity) AS sold_quantity

    FROM factsales

    WHERE order_status = 'Completed'

    GROUP BY
        DATE_FORMAT(order_date, '%Y-%m-01'),
        store_id
),

/* ============================================================
   5. Monthly targets aggregated from store/category target grain
   ============================================================ */
monthly_targets AS
(
    SELECT
        DATE_FORMAT(target_month, '%Y-%m-01') AS performance_month,
        store_id,

        SUM(revenue_target) AS revenue_target,

        SUM(profit_target) AS profit_target,

        SUM(order_target) AS order_target,

        AVG(return_rate_target_pct) AS return_rate_target_pct

    FROM facttargets

    GROUP BY
        DATE_FORMAT(target_month, '%Y-%m-01'),
        store_id
),

/* ============================================================
   6. Combine store performance
   ============================================================ */
store_base AS
(
    SELECT
        ms.performance_month,
        ms.store_id,

        cs.store_name,
        cs.store_type,
        cs.city,
        cs.state,
        cs.region,
        cs.opening_date,

        ms.revenue,
        ms.units,
        ms.completed_orders,
        ms.customers,

        COALESCE(
            mp.profit,
            0
        ) AS profit,

        COALESCE(
            mp.total_cost,
            0
        ) AS total_cost,

        COALESCE(
            mr.refunded_quantity,
            0
        ) AS refunded_quantity,

        COALESCE(
            mr.refunded_amount,
            0
        ) AS refunded_amount,

        COALESCE(
            mr.refunded_returns,
            0
        ) AS refunded_returns,

        COALESCE(
            mu.sold_quantity,
            0
        ) AS sold_quantity,

        mt.revenue_target,
        mt.profit_target,
        mt.order_target,
        mt.return_rate_target_pct

    FROM monthly_sales ms

    INNER JOIN core_stores cs
        ON ms.store_id = cs.store_id

    LEFT JOIN monthly_store_profit mp
        ON ms.performance_month = mp.performance_month
       AND ms.store_id = mp.store_id

    LEFT JOIN monthly_returns mr
        ON ms.performance_month = mr.performance_month
       AND ms.store_id = mr.store_id

    LEFT JOIN monthly_units mu
        ON ms.performance_month = mu.performance_month
       AND ms.store_id = mu.store_id

    LEFT JOIN monthly_targets mt
        ON ms.performance_month = mt.performance_month
       AND ms.store_id = mt.store_id
),

/* ============================================================
   7. Growth calculations
   ============================================================ */
with_growth AS
(
    SELECT
        sb.*,

        LAG(sb.revenue) OVER
        (
            PARTITION BY sb.store_id
            ORDER BY sb.performance_month
        ) AS previous_month_revenue,

        LAG(sb.profit) OVER
        (
            PARTITION BY sb.store_id
            ORDER BY sb.performance_month
        ) AS previous_month_profit,

        LAG(sb.completed_orders) OVER
        (
            PARTITION BY sb.store_id
            ORDER BY sb.performance_month
        ) AS previous_month_orders,

        LAG(sb.customers) OVER
        (
            PARTITION BY sb.store_id
            ORDER BY sb.performance_month
        ) AS previous_month_customers,

        LAG(sb.revenue) OVER
        (
            PARTITION BY
                sb.store_id
            ORDER BY
                sb.performance_month
        ) AS previous_period_revenue

    FROM store_base sb
),

/* ============================================================
   8. Final calculations
   ============================================================ */
calculated AS
(
    SELECT
        wg.*,

        CASE
            WHEN previous_month_revenue IS NULL
                THEN NULL

            WHEN previous_month_revenue = 0
                THEN NULL

            ELSE
                (
                    (revenue - previous_month_revenue)
                    / previous_month_revenue
                ) * 100
        END AS mom_revenue_growth_pct,

        CASE
            WHEN previous_month_profit IS NULL
                THEN NULL

            WHEN previous_month_profit = 0
                THEN NULL

            ELSE
                (
                    (profit - previous_month_profit)
                    / ABS(previous_month_profit)
                ) * 100
        END AS mom_profit_growth_pct,

        CASE
            WHEN previous_month_orders IS NULL
                THEN NULL

            WHEN previous_month_orders = 0
                THEN NULL

            ELSE
                (
                    (completed_orders - previous_month_orders)
                    / previous_month_orders
                ) * 100
        END AS mom_order_growth_pct,

        CASE
            WHEN revenue_target IS NULL
                OR revenue_target = 0
                THEN NULL

            ELSE
                (revenue / revenue_target) * 100
        END AS revenue_achievement_pct,

        CASE
            WHEN profit_target IS NULL
                OR profit_target = 0
                THEN NULL

            ELSE
                (profit / profit_target) * 100
        END AS profit_achievement_pct,

        CASE
            WHEN order_target IS NULL
                OR order_target = 0
                THEN NULL

            ELSE
                (completed_orders / order_target) * 100
        END AS order_achievement_pct,

        CASE
            WHEN sold_quantity = 0
                THEN NULL

            ELSE
                (refunded_quantity / sold_quantity) * 100
        END AS return_rate_pct,

        CASE
            WHEN revenue = 0
                THEN NULL

            ELSE
                (profit / revenue) * 100
        END AS profit_margin_pct

    FROM with_growth wg
)

SELECT
    performance_month,
    store_id,
    store_name,
    store_type,
    city,
    state,
    region,
    opening_date,

    revenue,
    profit,
    profit_margin_pct,

    units,
    completed_orders,
    customers,

    refunded_quantity,
    refunded_amount,
    refunded_returns,
    sold_quantity,
    return_rate_pct,

    revenue_target,
    profit_target,
    order_target,
    return_rate_target_pct,

    revenue_achievement_pct,
    profit_achievement_pct,
    order_achievement_pct,

    mom_revenue_growth_pct,
    mom_profit_growth_pct,
    mom_order_growth_pct,

    /* ========================================================
       Store performance band
       Based on documented revenue/profit/order achievement.
       ======================================================== */
    CASE

        WHEN
            (
                revenue_achievement_pct < 85
                OR profit_achievement_pct < 85
                OR order_achievement_pct < 85
            )
            THEN 'Critical'

        WHEN
            (
                revenue_achievement_pct < 95
                OR profit_achievement_pct < 95
                OR order_achievement_pct < 95
            )
            THEN 'Below Target'

        WHEN
            (
                revenue_achievement_pct <= 105
                AND profit_achievement_pct <= 105
                AND order_achievement_pct <= 105
            )
            THEN 'On Track'

        ELSE 'Above Target'

    END AS performance_band,

    /* ========================================================
       Margin band
       Same documented margin thresholds used by the project.
       ======================================================== */
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

    /* ========================================================
       Return target status
       Lower return rate is better.
       ======================================================== */
    CASE
        WHEN return_rate_pct IS NULL
            OR return_rate_target_pct IS NULL
            THEN 'Not Available'

        WHEN return_rate_pct <= return_rate_target_pct
            THEN 'Pass'

        ELSE 'Fail'

    END AS return_target_status,

    /* ========================================================
       Underperformance indicators
       ======================================================== */
    CASE
        WHEN
            (
                revenue_achievement_pct < 85
                OR profit_achievement_pct < 85
                OR order_achievement_pct < 85
                OR
                (
                    return_rate_pct IS NOT NULL
                    AND return_rate_target_pct IS NOT NULL
                    AND return_rate_pct > return_rate_target_pct
                )
            )
            THEN 1

        ELSE 0

    END AS underperformance_flag,

    CASE
        WHEN
            (
                revenue_achievement_pct < 85
                OR profit_achievement_pct < 85
                OR order_achievement_pct < 85
            )
            THEN 'Target Critical'

        WHEN
            return_rate_pct IS NOT NULL
            AND return_rate_target_pct IS NOT NULL
            AND return_rate_pct > return_rate_target_pct
            THEN 'Return Risk'

        WHEN
            profit_margin_pct < 10
            THEN 'Margin Pressure'

        WHEN
            mom_revenue_growth_pct < 0
            THEN 'Revenue Decline'

        ELSE 'Normal'

    END AS underperformance_indicator,

    /* ========================================================
       STORE060 special handling
       New/Ramp-up when no valid prior-month baseline exists.
       ======================================================== */
    CASE
        WHEN store_id = 'STORE060'
             AND opening_date >= '2026-05-01'
             AND
             (
                 previous_month_revenue IS NULL
                 OR previous_month_revenue = 0
             )
            THEN 'New/Ramp-up'

        WHEN previous_month_revenue IS NULL
            THEN 'No Prior Baseline'

        ELSE 'Established'

    END AS store_lifecycle_status

FROM calculated;




## verification 

USE retail_sales_db;

SELECT
    performance_band,
    margin_band,
    return_target_status,
    COUNT(*) AS store_month_count
FROM analytics.vw_store_performance_classification
GROUP BY
    performance_band,
    margin_band,
    return_target_status
ORDER BY
    performance_band,
    margin_band,
    return_target_status;
    
    ## Final validation 
    SELECT
    performance_month,
    store_id,
    store_name,
    region,
    revenue,
    profit,
    profit_margin_pct,
    completed_orders,
    customers,
    revenue_achievement_pct,
    profit_achievement_pct,
    order_achievement_pct,
    return_rate_pct,
    return_rate_target_pct,
    performance_band,
    underperformance_flag,
    underperformance_indicator,
    store_lifecycle_status
FROM analytics.vw_store_performance_classification
ORDER BY
    performance_month,
    store_id
LIMIT 50;