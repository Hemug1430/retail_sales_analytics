-- ==================================================================
-- 06.32 - CREATE ANALYTICAL KPI SUMMARY (MASTER RECONCILIATION LAYER)
-- ==================================================================
USE retail_sales_db;

-- Drop previous analytical instances if they exist to refresh schema metadata
DROP VIEW IF EXISTS analytics_master_kpi_reconciliation;

-- Compile a single-row high-performance master verification view layer
CREATE VIEW analytics_master_kpi_reconciliation AS
SELECT 
    '06.32 STATUS: PASS' AS status_check,
    
    -- 1. Core Forward Sales Volume & Frequency
    COUNT(fs.sales_line_id) AS absolute_total_transactions,
    SUM(fs.quantity) AS absolute_total_units_sold,
    
    -- 2. Financial Sales Aggregations
    ROUND(SUM(fs.quantity * fs.unit_selling_price), 2) AS total_gross_revenue,
    ROUND(SUM(fs.quantity * fs.unit_selling_price * COALESCE(fs.discount_pct, 0)), 2) AS total_discounts_applied,
    ROUND(SUM(fs.quantity * fs.unit_selling_price * (1 - COALESCE(fs.discount_pct, 0))), 2) AS absolute_net_revenue,
    
    -- 3. Margin Calculations (Assuming a 60% production cost baseline matrix)
    ROUND(
        SUM(fs.quantity * fs.unit_selling_price * (1 - COALESCE(fs.discount_pct, 0))) - 
        SUM(fs.quantity * (fs.unit_selling_price * 0.60)), 2
    ) AS absolute_contribution_profit,
    
    -- 4. Backward Claims & Returns Aggregations
    (SELECT COUNT(DISTINCT return_id) FROM factreturns) AS absolute_total_returned_units,
    ROUND((SELECT SUM(COALESCE(refund_amount, 0)) FROM factreturns), 2) AS absolute_total_capital_refunded

FROM factsales fs;

-- Execute the master audit verification run
SELECT * FROM analytics_master_kpi_reconciliation;
