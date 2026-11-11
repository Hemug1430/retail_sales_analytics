USE retail_sales_db;

CREATE DATABASE IF NOT EXISTS analytics;

DROP VIEW IF EXISTS analytics.vw_customer_segmentation;

CREATE VIEW analytics.vw_customer_segmentation AS

WITH
latest_date AS
(
    SELECT
        MAX(order_date) AS analysis_date
    FROM factsales
    WHERE order_status = 'Completed'
),

policy AS
(
    SELECT
        analysis_date,

        CASE
            WHEN analysis_date >= '2026-07-01'
                THEN 'V2'
            ELSE 'V1'
        END AS policy_version,

        CASE
            WHEN analysis_date >= '2026-07-01'
                THEN DATE('2026-07-01')
            ELSE NULL
        END AS effective_date

    FROM latest_date
),

customer_metrics AS
(
    SELECT
        fs.customer_id,

        SUM(
            fs.quantity *
            fs.unit_selling_price *
            (
                1 - COALESCE(fs.discount_pct, 0) / 100
            )
        ) AS t12m_net_revenue,

        COUNT(DISTINCT fs.order_id) AS completed_orders,

        SUM(fs.quantity) AS t12m_units,

        MAX(fs.order_date) AS last_purchase_date

    FROM factsales fs

    CROSS JOIN latest_date ld

    WHERE fs.order_status = 'Completed'
      AND fs.customer_id IS NOT NULL
      AND fs.order_date BETWEEN
          DATE_SUB(ld.analysis_date, INTERVAL 11 MONTH)
          AND ld.analysis_date

    GROUP BY
        fs.customer_id
),

segmented AS
(
    SELECT
        cc.customer_id,
        cc.customer_name,

        /* Preserve operational/source segment */
        cc.customer_segment AS source_customer_segment,

        cm.t12m_net_revenue,

        COALESCE(
            cm.completed_orders,
            0
        ) AS completed_orders,

        COALESCE(
            cm.t12m_units,
            0
        ) AS t12m_units,

        cm.last_purchase_date,

        CASE
            WHEN cm.last_purchase_date IS NULL
                THEN NULL
            ELSE DATEDIFF(
                p.analysis_date,
                cm.last_purchase_date
            )
        END AS recency_days,

        p.analysis_date,
        p.policy_version,
        p.effective_date,

        /* Analytical customer segmentation */
        CASE

            /* Policy V2 - effective 2026-07-01 */
            WHEN p.policy_version = 'V2'
                 AND COALESCE(cm.t12m_net_revenue, 0) >= 125000
                 AND COALESCE(cm.completed_orders, 0) >= 12
                THEN 'VIP'

            WHEN p.policy_version = 'V2'
                 AND COALESCE(cm.t12m_net_revenue, 0) >= 50000
                 AND COALESCE(cm.completed_orders, 0) >= 6
                THEN 'Premium'

            WHEN p.policy_version = 'V2'
                 AND (
                     COALESCE(cm.completed_orders, 0) >= 3
                     OR COALESCE(cm.t12m_net_revenue, 0) >= 15000
                 )
                THEN 'Regular'

            /* Policy V1 - through 2026-06-30 */
            WHEN p.policy_version = 'V1'
                 AND (
                     COALESCE(cm.t12m_net_revenue, 0) >= 100000
                     OR COALESCE(cm.completed_orders, 0) >= 18
                 )
                THEN 'VIP'

            WHEN p.policy_version = 'V1'
                 AND (
                     COALESCE(cm.t12m_net_revenue, 0) >= 40000
                     OR COALESCE(cm.completed_orders, 0) >= 8
                 )
                THEN 'Premium'

            WHEN p.policy_version = 'V1'
                 AND (
                     COALESCE(cm.completed_orders, 0) >= 3
                     OR COALESCE(cm.t12m_net_revenue, 0) >= 12000
                 )
                THEN 'Regular'

            ELSE 'Occasional'

        END AS analytical_customer_segment

    FROM core_customers cc

    CROSS JOIN policy p

    LEFT JOIN customer_metrics cm
        ON cc.customer_id = cm.customer_id
)

SELECT
    customer_id,
    customer_name,
    source_customer_segment,
    analytical_customer_segment,
    t12m_net_revenue,
    completed_orders,
    t12m_units,
    last_purchase_date,
    recency_days,
    analysis_date,
    policy_version,
    effective_date

FROM segmented;


## Verification Query

USE retail_sales_db;

SELECT
    policy_version,
    effective_date,
    analytical_customer_segment,
    COUNT(*) AS customer_count
FROM analytics.vw_customer_segmentation
GROUP BY
    policy_version,
    effective_date,
    analytical_customer_segment
ORDER BY
    policy_version,
    analytical_customer_segment;
    
    ## Final validation 
    SELECT
    customer_id,
    source_customer_segment,
    analytical_customer_segment,
    t12m_net_revenue,
    completed_orders,
    policy_version,
    effective_date
FROM analytics.vw_customer_segmentation
ORDER BY
    t12m_net_revenue DESC
LIMIT 20;