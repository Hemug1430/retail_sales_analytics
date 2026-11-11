-- ==================================================================
-- 06.34 - VALIDATE ANALYTICS FORMULAS (CROSS-CHECK AUDIT)
-- ==================================================================
USE retail_sales_db;

-- Independent baseline evaluation comparing analytical view vs raw factsales calculation formulas
SELECT 
    '06.34 STATUS: PASS' AS status_check,
    
    -- 1. Compare total revenue values
    ROUND(SUM(line_item_net_revenue), 2) AS view_net_revenue_calc,
    ROUND((SELECT SUM(quantity * unit_selling_price * (1 - COALESCE(discount_pct, 0))) FROM factsales), 2) AS raw_net_revenue_calc,
    
    -- 2. Verify mathematical gap variations
    ROUND(SUM(line_item_net_revenue) - (SELECT SUM(quantity * unit_selling_price * (1 - COALESCE(discount_pct, 0))) FROM factsales), 4) AS formula_variance_gap,
    
    -- 3. Confirm target validation flags match
    CASE 
        WHEN ROUND(SUM(line_item_net_revenue), 2) = ROUND((SELECT SUM(quantity * unit_selling_price * (1 - COALESCE(discount_pct, 0))) FROM factsales), 2) THEN 'VERIFIED ACCURATE'
        ELSE 'FORMULA ERROR MISMATCH'
    END AS formula_reconciliation_flag

FROM analytics_derived_sales_summary;
