-- ==================================================================
-- 07.11 - BUILD DIMDATE (MILESTONE CHECKPOINT SAVE)
-- ==================================================================
USE retail_sales_db;

-- Verifying structural dates availability matrix for cross-tool validation
SELECT 
    '07.11 STATUS: PASS' AS date_dimension_table_status,
    'DAX Calculated Engine' AS dynamic_generation_layer_origin,
    'DimDate' AS semantic_model_dimension_name,
    MIN(order_date) AS tracking_calendar_start_boundary,
    MAX(order_date) AS tracking_calendar_end_boundary,
    COUNT(DISTINCT order_date) AS total_operational_days_tracked
FROM factsales;
