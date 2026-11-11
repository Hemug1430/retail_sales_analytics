USE retail_sales_db;

-- ============================================================
-- 06.03 - CALCULATE DISCOUNT AMOUNT
-- Retail Sales Analytics
-- ============================================================

SELECT
    '06.03 - CALCULATE DISCOUNT AMOUNT' AS step;

-- ------------------------------------------------------------
-- 1. CREATE REUSABLE DISCOUNT CALCULATION VIEW
--
-- Frozen definition:
-- Discount Amount =
-- (Quantity × Unit Selling Price) × Discount Percentage / 100
--
-- Completed sales only.
-- ------------------------------------------------------------

CREATE OR REPLACE VIEW analytics.vw_sales_discount_amount AS

SELECT
    gr.sales_line_id,
    gr.order_id,
    gr.order_date,
    gr.order_status,
    gr.quantity,
    gr.unit_selling_price,

    fs.discount_pct,

    gr.gross_sales,

    CASE
        WHEN gr.order_status = 'Completed'
        THEN
            CAST(gr.gross_sales AS DECIMAL(18,4))
            *
            CAST(COALESCE(fs.discount_pct, 0) AS DECIMAL(18,4))
            / 100
        ELSE
            CAST(0 AS DECIMAL(18,4))
    END AS discount_amount

FROM analytics.vw_sales_gross_revenue gr

INNER JOIN factsales fs
    ON gr.sales_line_id = fs.sales_line_id;

-- ------------------------------------------------------------
-- 2. VALIDATION - TOTAL SALES LINES
-- ------------------------------------------------------------

SELECT
    COUNT(*) AS total_sales_lines
FROM analytics.vw_sales_discount_amount;

-- ------------------------------------------------------------
-- 3. VALIDATION - COMPLETED SALES LINES
-- ------------------------------------------------------------

SELECT
    COUNT(*) AS completed_sales_lines
FROM analytics.vw_sales_discount_amount
WHERE order_status = 'Completed';

-- ------------------------------------------------------------
-- 4. VALIDATION - TOTAL DISCOUNT AMOUNT
-- ------------------------------------------------------------

SELECT
    COALESCE(
        SUM(discount_amount),
        0
    ) AS total_discount_amount
FROM analytics.vw_sales_discount_amount
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
    discount_amount
FROM analytics.vw_sales_discount_amount
WHERE order_status = 'Completed'
ORDER BY order_date, sales_line_id
LIMIT 10;

-- ------------------------------------------------------------
-- 6. VALIDATION - CANCELLED LINES
-- ------------------------------------------------------------

SELECT
    COUNT(*) AS cancelled_lines,
    COALESCE(
        SUM(discount_amount),
        0
    ) AS cancelled_discount_amount
FROM analytics.vw_sales_discount_amount
WHERE order_status = 'Cancelled';

-- ------------------------------------------------------------
-- 7. VALIDATION - NULL DISCOUNT AMOUNTS
-- ------------------------------------------------------------

SELECT
    COUNT(*) AS null_discount_amount
FROM analytics.vw_sales_discount_amount
WHERE discount_amount IS NULL;

-- ------------------------------------------------------------
-- 8. VALIDATION - DISCOUNT CANNOT EXCEED GROSS SALES
-- ------------------------------------------------------------

SELECT
    COUNT(*) AS invalid_discount_rows
FROM analytics.vw_sales_discount_amount
WHERE order_status = 'Completed'
  AND discount_amount > gross_sales;

-- ------------------------------------------------------------
-- 9. FINAL STATUS
-- ------------------------------------------------------------

SELECT
    '06.03 DISCOUNT AMOUNT CALCULATION COMPLETED' AS status;