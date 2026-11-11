USE retail_sales_db;

CREATE DATABASE IF NOT EXISTS analytics;

DROP VIEW IF EXISTS analytics.vw_return_refund_metrics;

CREATE VIEW analytics.vw_return_refund_metrics AS

WITH return_events AS
(
    SELECT
        r.return_id,
        r.sales_line_id,
        DATE(r.return_date) AS return_date,
        r.quantity_returned,
        COALESCE(r.refund_amount, 0) AS refund_amount
    FROM factreturns r
    WHERE r.return_date IS NOT NULL
),

sales_line_reference AS
(
    SELECT
        f.sales_line_id,
        MAX(f.quantity) AS sold_quantity
    FROM factsales f
    GROUP BY f.sales_line_id
),

return_metrics AS
(
    SELECT
        re.return_date,

        SUM(re.quantity_returned) AS returned_quantity,

        SUM(re.refund_amount) AS refund_amount,

        COUNT(DISTINCT re.return_id) AS return_count,

        SUM(
            COALESCE(sl.sold_quantity, 0)
        ) AS eligible_sold_quantity

    FROM return_events re

    LEFT JOIN sales_line_reference sl
        ON re.sales_line_id = sl.sales_line_id

    GROUP BY
        re.return_date
)

SELECT
    return_date,

    returned_quantity,

    refund_amount,

    return_count,

    eligible_sold_quantity,

    CASE
        WHEN eligible_sold_quantity > 0
        THEN
            ROUND(
                returned_quantity
                / eligible_sold_quantity
                * 100,
                4
            )
        ELSE 0
    END AS return_rate_pct

FROM return_metrics;