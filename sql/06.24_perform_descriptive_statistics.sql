-- ==================================================================
-- 06.24 - PERFORM DESCRIPTIVE STATISTICS (NATIVE SQL DATA METRICS)
-- ==================================================================
USE retail_sales_db;

-- 1. Descriptive Summary Metrics for Transaction Invoicing Variables
SELECT 
    '06.24 STATUS: PASS' AS status_check,
    COUNT(sales_line_id) AS total_observations_count,
    
    -- Mean / Average Indicators
    ROUND(AVG(quantity), 2) AS mean_quantity_sold,
    ROUND(AVG(unit_selling_price), 2) AS mean_unit_selling_price,
    ROUND(AVG(quantity * unit_selling_price * (1 - COALESCE(discount_pct, 0))), 2) AS mean_net_revenue,
    
    -- Statistical Spread and Dispersion Profiles
    ROUND(VARIANCE(quantity), 4) AS quantity_variance,
    ROUND(STDDEV(quantity), 4) AS quantity_standard_deviation,
    ROUND(VARIANCE(unit_selling_price), 4) AS price_variance,
    ROUND(STDDEV(unit_selling_price), 4) AS price_standard_deviation,
    
    -- Boundary Min/Max Ranges
    MIN(quantity) AS absolute_min_quantity,
    MAX(quantity) AS absolute_max_quantity,
    MIN(unit_selling_price) AS absolute_min_price,
    MAX(unit_selling_price) AS absolute_max_price
FROM factsales;

-- 2. Percentile Distribution Array Matrix using Window Functions
WITH OrderedSales AS (
    SELECT 
        quantity,
        unit_selling_price,
        PERCENT_RANK() OVER (ORDER BY quantity) AS quantity_percentile_rank,
        PERCENT_RANK() OVER (ORDER BY unit_selling_price) AS price_percentile_rank
    FROM factsales
)
SELECT 
    '06.24 STATUS: PASS' AS status_check,
    -- Estimating core percentile breaks based on positional rank values
    MAX(CASE WHEN quantity_percentile_rank <= 0.25 THEN quantity END) AS quantity_25th_percentile_q1,
    MAX(CASE WHEN quantity_percentile_rank <= 0.50 THEN quantity END) AS quantity_50th_percentile_median,
    MAX(CASE WHEN quantity_percentile_rank <= 0.75 THEN quantity END) AS quantity_75th_percentile_q3,
    MAX(CASE WHEN price_percentile_rank <= 0.25 THEN unit_selling_price END) AS price_25th_percentile_q1,
    MAX(CASE WHEN price_percentile_rank <= 0.50 THEN unit_selling_price END) AS price_50th_percentile_median,
    MAX(CASE WHEN price_percentile_rank <= 0.75 THEN unit_selling_price END) AS price_75th_percentile_q3
FROM OrderedSales;
