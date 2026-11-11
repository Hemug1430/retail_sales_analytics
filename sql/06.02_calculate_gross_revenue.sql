USE retail_sales_db;

-- ============================================================
-- 06.02 - CALCULATE GROSS REVENUE
-- Retail Sales Analytics
-- ============================================================

SELECT
    '06.02 - CALCULATE GROSS REVENUE' AS step;

-- ------------------------------------------------------------
-- 1. CREATE ANALYTICS SCHEMA
-- ------------------------------------------------------------

CREATE SCHEMA IF NOT EXISTS analytics;

-- ------------------------------------------------------------
-- 2. CREATE REUSABLE GROSS REVENUE VIEW
--
-- Frozen definition:
-- Gross Sales = Quantity × Unit Selling Price
-- Completed sales only.
--
-- Cancelled lines are retained but contribute zero
-- commercial sales value.
-- ------------------------------------------------------------

CREATE OR REPLACE VIEW analytics.vw_sales_gross_revenue AS

SELECT
    fs.sales_line_id,
    fs.order_id,
    fs.order_date,
    fs.order_status,
    fs.quantity,
    fs.unit_selling_price,

    CASE
        WHEN fs.order_status = 'Completed'
        THEN
            CAST(fs.quantity AS DECIMAL(18,4))
            *
            CAST(fs.unit_selling_price AS DECIMAL(18,4))
        ELSE
            CAST(0 AS DECIMAL(18,4))
    END AS gross_sales

FROM factsales fs;

-- ------------------------------------------------------------
-- 3. VALIDATION - TOTAL SALES LINES
-- ------------------------------------------------------------

SELECT
    COUNT(*) AS total_sales_lines
FROM analytics.vw_sales_gross_revenue;

-- ------------------------------------------------------------
-- 4. VALIDATION - ELIGIBLE COMPLETED SALES LINES
-- ------------------------------------------------------------

SELECT
    COUNT(*) AS completed_sales_lines
FROM analytics.vw_sales_gross_revenue
WHERE order_status = 'Completed';

-- ------------------------------------------------------------
-- 5. VALIDATION - COMPLETED GROSS REVENUE
-- ------------------------------------------------------------

SELECT
    COALESCE(
        SUM(gross_sales),
        0
    ) AS total_gross_revenue
FROM analytics.vw_sales_gross_revenue
WHERE order_status = 'Completed';

-- ------------------------------------------------------------
-- 6. VALIDATION - SAMPLE CALCULATIONS
-- ------------------------------------------------------------

SELECT
    sales_line_id,
    order_id,
    order_date,
    order_status,
    quantity,
    unit_selling_price,
    gross_sales
FROM analytics.vw_sales_gross_revenue
ORDER BY order_date, sales_line_id
LIMIT 10;

-- ------------------------------------------------------------
-- 7. VALIDATION - CANCELLED LINES MUST CONTRIBUTE ZERO
-- ------------------------------------------------------------

SELECT
    COUNT(*) AS cancelled_lines,
    COALESCE(
        SUM(gross_sales),
        0
    ) AS cancelled_gross_sales
FROM analytics.vw_sales_gross_revenue
WHERE order_status = 'Cancelled';

-- ------------------------------------------------------------
-- 8. VALIDATION - NULL GROSS SALES
-- ------------------------------------------------------------

SELECT
    COUNT(*) AS null_gross_sales
FROM analytics.vw_sales_gross_revenue
WHERE gross_sales IS NULL;

-- ------------------------------------------------------------
-- 9. FINAL STATUS
-- ------------------------------------------------------------

SELECT
    '06.02 GROSS REVENUE CALCULATION COMPLETED' AS status;