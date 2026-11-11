USE retail_sales_db;

-- ============================================================
-- 06.06 - CALCULATE TOTAL COST
-- Retail Sales Analytics
-- ============================================================

SELECT
    '06.06 - CALCULATE TOTAL COST' AS step;


-- ============================================================
-- 1. CREATE TOTAL COST VIEW
--
-- Definition:
-- Total Cost = Quantity × Historical Unit Cost
--
-- Eligible sales:
--   - Completed sales
--   - Historical unit cost is available
--
-- No current product cost is substituted when historical
-- cost is unavailable.
-- ============================================================

CREATE OR REPLACE VIEW analytics.vw_sales_total_cost AS

SELECT
    hc.sales_line_id,
    hc.order_id,
    hc.order_date,
    hc.order_status,
    hc.product_id,
    hc.quantity,
    hc.unit_cost_effective,

    CAST(hc.quantity AS DECIMAL(18,4))
    *
    CAST(hc.unit_cost_effective AS DECIMAL(18,4))
        AS total_cost

FROM analytics.vw_sales_historical_cost hc

WHERE hc.order_status = 'Completed'
  AND hc.historical_cost_status = 'AVAILABLE';


-- ============================================================
-- 2. VALIDATE ELIGIBLE SALES
-- ============================================================

SELECT
    COUNT(*) AS eligible_sales_lines
FROM analytics.vw_sales_total_cost;


-- ============================================================
-- 3. VALIDATE HISTORICAL UNIT COST
-- ============================================================

SELECT
    COUNT(*) AS rows_with_historical_cost
FROM analytics.vw_sales_total_cost
WHERE unit_cost_effective IS NOT NULL;


-- ============================================================
-- 4. CALCULATE TOTAL HISTORICAL COST
-- ============================================================

SELECT
    COALESCE(
        SUM(total_cost),
        0
    ) AS total_cost
FROM analytics.vw_sales_total_cost;


-- ============================================================
-- 5. SAMPLE CALCULATIONS
-- ============================================================

SELECT
    sales_line_id,
    order_id,
    order_date,
    product_id,
    quantity,
    unit_cost_effective,
    total_cost
FROM analytics.vw_sales_total_cost
ORDER BY order_date, sales_line_id
LIMIT 10;


-- ============================================================
-- 6. VALIDATE FORMULA
-- ============================================================

SELECT
    COUNT(*) AS invalid_total_cost_rows
FROM analytics.vw_sales_total_cost
WHERE total_cost <>
      (
          CAST(quantity AS DECIMAL(18,4))
          *
          CAST(unit_cost_effective AS DECIMAL(18,4))
      );


-- ============================================================
-- 7. VALIDATE NULL COST
-- ============================================================

SELECT
    COUNT(*) AS null_total_cost_rows
FROM analytics.vw_sales_total_cost
WHERE total_cost IS NULL;


-- ============================================================
-- 8. FINAL STATUS
-- ============================================================

SELECT
    CASE
        WHEN EXISTS (
            SELECT 1
            FROM analytics.vw_sales_total_cost
        )
        THEN
            '06.06 TOTAL COST CALCULATION COMPLETED'
        ELSE
            '06.06 IMPLEMENTED - NO ELIGIBLE SALES WITH HISTORICAL COST AVAILABLE'
    END AS status;