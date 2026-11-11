USE retail_sales_db;

-- ============================================================
-- 06.04 - CALCULATE NET REVENUE
-- Retail Sales Analytics
-- ============================================================

SELECT
    '06.04 - CALCULATE NET REVENUE' AS step;

-- ------------------------------------------------------------
-- 1. CREATE REUSABLE NET REVENUE VIEW
--
-- Net Revenue = Gross Revenue - Discount Amount
-- Completed sales only.
-- Cancelled sales contribute zero commercial revenue.
-- ------------------------------------------------------------

CREATE OR REPLACE VIEW analytics.vw_sales_net_revenue AS

SELECT
    da.sales_line_id,
    da.order_id,
    da.order_date,
    da.order_status,
    da.quantity,
    da.unit_selling_price,
    da.discount_pct,
    da.gross_sales,
    da.discount_amount,

    CASE
        WHEN da.order_status = 'Completed'
        THEN
            CAST(da.gross_sales AS DECIMAL(18,4))
            -
            CAST(da.discount_amount AS DECIMAL(18,4))
        ELSE
            CAST(0 AS DECIMAL(18,4))
    END AS net_revenue

FROM analytics.vw_sales_discount_amount da;

-- ------------------------------------------------------------
-- 2. VALIDATION - TOTAL SALES LINES
-- ------------------------------------------------------------

SELECT
    COUNT(*) AS total_sales_lines
FROM analytics.vw_sales_net_revenue;

-- ------------------------------------------------------------
-- 3. VALIDATION - COMPLETED SALES LINES
-- ------------------------------------------------------------

SELECT
    COUNT(*) AS completed_sales_lines
FROM analytics.vw_sales_net_revenue
WHERE order_status = 'Completed';

-- ------------------------------------------------------------
-- 4. VALIDATION - TOTAL NET REVENUE
-- ------------------------------------------------------------

SELECT
    COALESCE(
        SUM(net_revenue),
        0
    ) AS total_net_revenue
FROM analytics.vw_sales_net_revenue
WHERE order_status = 'Completed';

-- ------------------------------------------------------------
-- 5. VALIDATION - SAMPLE CALCULATIONS
-- ------------------------------------------------------------

SELECT
    sales_line_id,
    order_id,
    order_status,
    quantity,
    unit_selling_price,
    discount_pct,
    gross_sales,
    discount_amount,
    net_revenue
FROM analytics.vw_sales_net_revenue
ORDER BY order_date, sales_line_id
LIMIT 10;

-- ------------------------------------------------------------
-- 6. VALIDATION - CANCELLED ORDER TREATMENT
-- ------------------------------------------------------------

SELECT
    COUNT(*) AS cancelled_lines,
    COALESCE(
        SUM(gross_sales),
        0
    ) AS cancelled_gross_sales,
    COALESCE(
        SUM(discount_amount),
        0
    ) AS cancelled_discount_amount,
    COALESCE(
        SUM(net_revenue),
        0
    ) AS cancelled_net_revenue
FROM analytics.vw_sales_net_revenue
WHERE order_status = 'Cancelled';

-- ------------------------------------------------------------
-- 7. CANCELLED NET REVENUE MUST BE ZERO
-- ------------------------------------------------------------

SELECT
    COUNT(*) AS invalid_cancelled_net_revenue_rows
FROM analytics.vw_sales_net_revenue
WHERE order_status = 'Cancelled'
  AND net_revenue <> 0;

-- ------------------------------------------------------------
-- 8. NET REVENUE MUST NOT EXCEED GROSS SALES
-- ------------------------------------------------------------

SELECT
    COUNT(*) AS invalid_net_revenue_rows
FROM analytics.vw_sales_net_revenue
WHERE order_status = 'Completed'
  AND net_revenue > gross_sales;

-- ------------------------------------------------------------
-- 9. NULL NET REVENUE CHECK
-- ------------------------------------------------------------

SELECT
    COUNT(*) AS null_net_revenue
FROM analytics.vw_sales_net_revenue
WHERE net_revenue IS NULL;

-- ------------------------------------------------------------
-- 10. FINAL STATUS
-- ------------------------------------------------------------

SELECT
    '06.04 NET REVENUE CALCULATION COMPLETED' AS status;