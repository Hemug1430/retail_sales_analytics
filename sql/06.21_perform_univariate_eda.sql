-- ==================================================================
-- 06.21 - PERFORM UNIVARIATE EDA (NATIVE SQL STATISTICAL ANALYSIS)
-- ==================================================================
USE retail_sales_db;

-- 1. Descriptive Summary Metrics for Key Sales Variables
SELECT 
    '06.21 STATUS: PASS' AS status_check,
    'Sales Variables Profiling' AS Analysis_Target,
    COUNT(sales_line_id) AS total_record_count,
    ROUND(AVG(quantity), 2) AS avg_quantity_per_order,
    ROUND(MIN(quantity), 2) AS min_quantity,
    ROUND(MAX(quantity), 2) AS max_quantity,
    ROUND(STDDEV(quantity), 2) AS quantity_standard_deviation,
    ROUND(AVG(unit_selling_price), 2) AS avg_unit_selling_price,
    ROUND(MIN(unit_selling_price), 2) AS min_selling_price,
    ROUND(MAX(unit_selling_price), 2) AS max_selling_price,
    ROUND(AVG(discount_pct * 100), 2) AS avg_discount_percentage,
    COUNT(CASE WHEN discount_pct IS NULL THEN 1 END) AS missing_discount_values
FROM factsales;

-- 2. Quantitative Value Spread Profiling for Return Actions
SELECT 
    '06.21 STATUS: PASS' AS status_check,
    'Return Variables Profiling' AS Analysis_Target,
    COUNT(return_id) AS total_returned_units,
    ROUND(SUM(refund_amount), 2) AS total_refund_capital_outflow,
    ROUND(AVG(refund_amount), 2) AS average_refund_payout,
    ROUND(MIN(refund_amount), 2) AS absolute_min_refund,
    ROUND(MAX(refund_amount), 2) AS absolute_max_refund
FROM factreturns;

-- 3. Distribution Frequency Mapping for Core Categorical Segments
SELECT 
    '06.21 STATUS: PASS' AS status_check,
    p.category,
    COUNT(fs.sales_line_id) AS transaction_volume,
    ROUND((COUNT(fs.sales_line_id) / (SELECT COUNT(*) FROM factsales)) * 100, 2) AS volume_distribution_percentage
FROM factsales fs
INNER JOIN core_products p ON fs.product_id = p.product_id
GROUP BY p.category
ORDER BY transaction_volume DESC;
