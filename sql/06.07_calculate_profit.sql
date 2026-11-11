USE retail_sales_db;

-- ============================================================
-- 06.07 - CALCULATE PROFIT
-- Retail Sales Analytics
-- ============================================================

SELECT
    '06.07 - CALCULATE PROFIT' AS step;


-- ============================================================
-- 1. CREATE PROFIT VIEW
--
-- Definition:
-- Profit = Net Revenue - Total Cost
--
-- Eligible sales:
--   - Completed
--   - Historical cost available
--   - Total cost available
-- ============================================================

CREATE OR REPLACE VIEW analytics.vw_sales_profit AS

SELECT
    nr.sales_line_id,
    nr.order_id,
    nr.order_date,
    nr.order_status,
    nr.net_revenue,

    tc.product_id,
    tc.quantity,
    tc.unit_cost_effective,
    tc.total_cost,

    CAST(nr.net_revenue AS DECIMAL(18,4))
    -
    CAST(tc.total_cost AS DECIMAL(18,4))
        AS profit

FROM analytics.vw_sales_net_revenue nr

INNER JOIN analytics.vw_sales_total_cost tc
    ON nr.sales_line_id = tc.sales_line_id

WHERE nr.order_status = 'Completed';


-- ============================================================
-- 2. VALIDATE ELIGIBLE PROFIT ROWS
-- ============================================================

SELECT
    COUNT(*) AS eligible_profit_lines
FROM analytics.vw_sales_profit;


-- ============================================================
-- 3. CALCULATE TOTAL PROFIT
-- ============================================================

SELECT
    COALESCE(
        SUM(profit),
        0
    ) AS total_profit
FROM analytics.vw_sales_profit;


-- ============================================================
-- 4. SAMPLE PROFIT CALCULATIONS
-- ============================================================

SELECT
    sales_line_id,
    order_id,
    order_date,
    net_revenue,
    total_cost,
    profit
FROM analytics.vw_sales_profit
ORDER BY order_date, sales_line_id
LIMIT 10;


-- ============================================================
-- 5. VALIDATE PROFIT FORMULA
-- ============================================================

SELECT
    COUNT(*) AS invalid_profit_rows
FROM analytics.vw_sales_profit
WHERE profit <>
      (
          CAST(net_revenue AS DECIMAL(18,4))
          -
          CAST(total_cost AS DECIMAL(18,4))
      );


-- ============================================================
-- 6. VALIDATE NULL PROFIT
-- ============================================================

SELECT
    COUNT(*) AS null_profit_rows
FROM analytics.vw_sales_profit
WHERE profit IS NULL;


-- ============================================================
-- 7. VALIDATE CANCELLED SALES
-- ============================================================

SELECT
    COUNT(*) AS cancelled_profit_rows
FROM analytics.vw_sales_profit
WHERE order_status = 'Cancelled';


-- ============================================================
-- 8. FINAL STATUS
-- ============================================================

SELECT
    CASE
        WHEN EXISTS (
            SELECT 1
            FROM analytics.vw_sales_profit
        )
        THEN
            '06.07 PROFIT CALCULATION COMPLETED'
        ELSE
            '06.07 IMPLEMENTED - NO ELIGIBLE SALES WITH HISTORICAL COST AVAILABLE'
    END AS status;