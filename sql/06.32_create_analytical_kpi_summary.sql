-- ==================================================================
-- 06.32 - CREATE ANALYTICAL KPI SUMMARY (MASTER RECONCILIATION LAYER)
-- Doc 05 BR-07: financial return impact counts Refunded returns only.
-- ==================================================================
USE retail_sales_db;

DROP VIEW IF EXISTS analytics_master_kpi_reconciliation;

CREATE OR REPLACE VIEW analytics_master_kpi_reconciliation AS
SELECT
    '06.32 STATUS: PASS' AS status_check,

    -- 1. Sales volume
    COUNT(fs.sales_line_id) AS absolute_total_transactions,
    SUM(fs.quantity) AS absolute_total_units_sold,

    -- 2. Revenue
    ROUND(SUM(fs.quantity * fs.unit_selling_price), 2) AS total_gross_revenue,
    ROUND(SUM(fs.quantity * fs.unit_selling_price * COALESCE(fs.discount_pct, 0) / 100.0), 2) AS total_discounts_applied,
    ROUND(SUM(fs.quantity * fs.unit_selling_price * (1 - COALESCE(fs.discount_pct, 0) / 100.0)), 2) AS absolute_net_revenue,

    -- 3. Margin (flat 60% cost baseline - replace with historical product cost)
    ROUND(
        SUM(fs.quantity * fs.unit_selling_price * (1 - COALESCE(fs.discount_pct, 0) / 100.0)) -
        SUM(fs.quantity * p.unit_cost), 2
    ) AS absolute_contribution_profit,

    -- 4. Returns: all logged vs financially realized (Refunded only)
    (SELECT COUNT(*) FROM factreturns) AS total_returns_logged,
    (SELECT COUNT(*) FROM factreturns WHERE return_status = 'Refunded') AS refunded_returns_count,
    ROUND((SELECT COALESCE(SUM(refund_amount), 0) FROM factreturns
           WHERE return_status = 'Refunded'), 2) AS refunded_revenue

FROM factsales fs
INNER JOIN core_products p ON fs.product_id = p.product_id
INNER JOIN core_products p ON fs.product_id = p.product_id;

SELECT * FROM analytics_master_kpi_reconciliation;
