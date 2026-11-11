-- ==================================================================
-- 06.25 - PERFORM CORRELATION ANALYSIS (NATIVE SQL PEARSON COEF)
-- ==================================================================
USE retail_sales_db;

-- Calculating exact mathematical correlation matrix across quantities, prices, and discounts
SELECT 
    '06.25 STATUS: PASS' AS status_check,
    COUNT(*) AS total_data_pairs,
    
    -- 1. Correlation between Applied Discount Percentage and Order Quantity Moved
    ROUND(
        (SUM(discount_pct * quantity) - (SUM(discount_pct) * SUM(quantity)) / COUNT(*)) / 
        SQRT(
            (SUM(discount_pct * discount_pct) - (SUM(discount_pct) * SUM(discount_pct)) / COUNT(*)) * 
            (SUM(quantity * quantity) - (SUM(quantity) * SUM(quantity)) / COUNT(*))
        ), 4
    ) AS correlation_discount_vs_quantity,

    -- 2. Correlation between Unit Selling Price and Order Quantity Moved
    ROUND(
        (SUM(unit_selling_price * quantity) - (SUM(unit_selling_price) * SUM(quantity)) / COUNT(*)) / 
        SQRT(
            (SUM(unit_selling_price * unit_selling_price) - (SUM(unit_selling_price) * SUM(unit_selling_price)) / COUNT(*)) * 
            (SUM(quantity * quantity) - (SUM(quantity) * SUM(quantity)) / COUNT(*))
        ), 4
    ) AS correlation_price_vs_quantity

FROM factsales;
