USE retail_sales_db;

-- ============================================================
-- 06.08 - CALCULATE PROFIT MARGIN %
-- Retail Sales Analytics
-- ============================================================

SELECT
    '06.08 - CALCULATE PROFIT MARGIN %' AS step;


-- ============================================================
-- 1. CREATE PROFIT MARGIN VIEW
--
-- Definition:
-- Profit Margin % = Profit / Net Revenue × 100
--
-- Zero-denominator treatment:
-- If Net Revenue = 0, Profit Margin % = 0.
--
-- Only eligible Completed sales with historical cost
-- available are included.
-- ============================================================

CREATE OR REPLACE VIEW analytics.vw_sales_profit_margin AS

SELECT
    p.sales_line_id,
    p.order_id,
    p.order_date,
    p.order_status,
    p.net_revenue,
    p.total_cost,
    p.profit,

    CASE
        WHEN p.net_revenue = 0
        THEN CAST(0 AS DECIMAL(18,4))

        ELSE
            (
                CAST(p.profit AS DECIMAL(18,4))
                /
                CAST(p.net_revenue AS DECIMAL(18,4))
            ) * 100
    END AS profit_margin_pct

FROM analytics.vw_sales_profit p;


-- ============================================================
-- 2. VALIDATE ELIGIBLE SALES
-- ============================================================

SELECT
    COUNT(*) AS eligible_profit_margin_lines
FROM analytics.vw_sales_profit_margin;


-- ============================================================
-- 3. VALIDATE TOTAL PROFIT
-- ============================================================

SELECT
    COALESCE(
        SUM(profit),
        0
    ) AS total_profit
FROM analytics.vw_sales_profit_margin;


-- ============================================================
-- 4. VALIDATE TOTAL NET REVENUE
-- ============================================================

SELECT
    COALESCE(
        SUM(net_revenue),
        0
    ) AS total_net_revenue
FROM analytics.vw_sales_profit_margin;


-- ============================================================
-- 5. SAMPLE PROFIT MARGIN CALCULATIONS
-- ============================================================

SELECT
    sales_line_id,
    order_id,
    order_date,
    net_revenue,
    total_cost,
    profit,
    profit_margin_pct
FROM analytics.vw_sales_profit_margin
ORDER BY order_date, sales_line_id
LIMIT 10;


-- ============================================================
-- 6. VALIDATE PROFIT MARGIN FORMULA
-- ============================================================

SELECT
    COUNT(*) AS invalid_profit_margin_rows
FROM analytics.vw_sales_profit_margin
WHERE net_revenue <> 0
  AND ABS(
        profit_margin_pct
        -
        (
            (profit / net_revenue) * 100
        )
      ) > 0.0001;


-- ============================================================
-- 7. VALIDATE ZERO-DENOMINATOR HANDLING
-- ============================================================

SELECT
    COUNT(*) AS zero_net_revenue_rows
FROM analytics.vw_sales_profit_margin
WHERE net_revenue = 0;


-- ============================================================
-- 8. VALIDATE NULL PROFIT MARGIN
-- ============================================================

SELECT
    COUNT(*) AS null_profit_margin_rows
FROM analytics.vw_sales_profit_margin
WHERE profit_margin_pct IS NULL;


-- ============================================================
-- 9. FINAL STATUS
-- ============================================================

SELECT
    CASE
        WHEN EXISTS (
            SELECT 1
            FROM analytics.vw_sales_profit_margin
        )
        THEN
            '06.08 PROFIT MARGIN CALCULATION COMPLETED'
        ELSE
            '06.08 IMPLEMENTED - NO ELIGIBLE SALES WITH HISTORICAL COST AVAILABLE'
    END AS status;