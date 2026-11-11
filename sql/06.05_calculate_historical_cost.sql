USE retail_sales_db;

-- ============================================================
-- 06.05 - CALCULATE HISTORICAL COST
-- Retail Sales Analytics
-- ============================================================

SELECT
    '06.05 - CALCULATE HISTORICAL COST' AS step;


-- ============================================================
-- 1. CREATE HISTORICAL COST VIEW
--
-- Historical rule:
-- Use the product version effective on order_date.
--
-- IMPORTANT:
-- Current product cost must NOT be used when no historical
-- version is effective for the sales date.
--
-- Missing historical cost is explicitly flagged.
-- ============================================================

CREATE OR REPLACE VIEW analytics.vw_sales_historical_cost AS

SELECT
    nr.sales_line_id,
    nr.order_id,
    nr.order_date,
    nr.order_status,

    fs.product_id,

    nr.quantity,
    nr.gross_sales,
    nr.discount_amount,
    nr.net_revenue,

    cp.unit_cost AS unit_cost_effective,

    CASE
        WHEN cp.product_id IS NOT NULL
        THEN 'AVAILABLE'
        ELSE 'HISTORICAL_COST_UNAVAILABLE'
    END AS historical_cost_status,

    CASE
        WHEN nr.order_status = 'Completed'
             AND cp.unit_cost IS NOT NULL
        THEN
            CAST(nr.quantity AS DECIMAL(18,4))
            *
            CAST(cp.unit_cost AS DECIMAL(18,4))
        ELSE
            NULL
    END AS total_cost

FROM analytics.vw_sales_net_revenue nr

INNER JOIN factsales fs
    ON nr.sales_line_id = fs.sales_line_id

LEFT JOIN core_products cp
    ON fs.product_id = cp.product_id
   AND cp.valid_from <= nr.order_date
   AND (
        cp.valid_to IS NULL
        OR cp.valid_to > nr.order_date
   );


-- ============================================================
-- 2. TOTAL SALES LINES
-- ============================================================

SELECT
    COUNT(*) AS total_sales_lines
FROM analytics.vw_sales_historical_cost;


-- ============================================================
-- 3. COMPLETED SALES LINES
-- ============================================================

SELECT
    COUNT(*) AS completed_sales_lines
FROM analytics.vw_sales_historical_cost
WHERE order_status = 'Completed';


-- ============================================================
-- 4. HISTORICAL COST AVAILABLE
-- ============================================================

SELECT
    COUNT(*) AS historical_cost_available
FROM analytics.vw_sales_historical_cost
WHERE historical_cost_status = 'AVAILABLE';


-- ============================================================
-- 5. HISTORICAL COST UNAVAILABLE
-- ============================================================

SELECT
    COUNT(*) AS historical_cost_unavailable
FROM analytics.vw_sales_historical_cost
WHERE historical_cost_status = 'HISTORICAL_COST_UNAVAILABLE';


-- ============================================================
-- 6. TOTAL HISTORICAL COST
-- ============================================================

SELECT
    COALESCE(
        SUM(total_cost),
        0
    ) AS total_historical_cost
FROM analytics.vw_sales_historical_cost
WHERE order_status = 'Completed'
  AND historical_cost_status = 'AVAILABLE';


-- ============================================================
-- 7. SAMPLE HISTORICAL COST RESULTS
-- ============================================================

SELECT
    sales_line_id,
    order_id,
    order_date,
    product_id,
    quantity,
    unit_cost_effective,
    historical_cost_status,
    total_cost
FROM analytics.vw_sales_historical_cost
ORDER BY order_date, sales_line_id
LIMIT 10;


-- ============================================================
-- 8. VALIDATE COST CALCULATION
-- ============================================================

SELECT
    COUNT(*) AS invalid_cost_calculations
FROM analytics.vw_sales_historical_cost
WHERE order_status = 'Completed'
  AND historical_cost_status = 'AVAILABLE'
  AND total_cost <>
      (
          CAST(quantity AS DECIMAL(18,4))
          *
          CAST(unit_cost_effective AS DECIMAL(18,4))
      );


-- ============================================================
-- 9. SHOW UNRESOLVED PRODUCT COST EXAMPLES
-- ============================================================

SELECT
    sales_line_id,
    order_id,
    order_date,
    product_id,
    quantity,
    historical_cost_status
FROM analytics.vw_sales_historical_cost
WHERE historical_cost_status = 'HISTORICAL_COST_UNAVAILABLE'
ORDER BY order_date, sales_line_id
LIMIT 10;


-- ============================================================
-- 10. FINAL STATUS
-- ============================================================

SELECT
    CASE
        WHEN EXISTS (
            SELECT 1
            FROM analytics.vw_sales_historical_cost
            WHERE historical_cost_status =
                  'HISTORICAL_COST_UNAVAILABLE'
        )
        THEN
            '06.05 IMPLEMENTED - HISTORICAL COST DATA UNAVAILABLE FOR SOME SALES'
        ELSE
            '06.05 HISTORICAL COST CALCULATION COMPLETED'
    END AS status;