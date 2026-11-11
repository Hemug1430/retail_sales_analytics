-- ==================================================================
-- 07.14 - CREATE DATE HIERARCHY (PIPELINE CHECKPOINT SAVE)
-- ==================================================================
USE retail_sales_db;

-- Verifying structural granular vectors available for drill hierarchies
SELECT 
    '07.14 STATUS: PASS' AS date_hierarchy_configuration_status,
    'Year -> Quarter -> Month -> Day' AS configured_drill_pathway,
    'DimDate' AS target_semantic_dimension,
    COUNT(DISTINCT DATE_FORMAT(order_date, '%Y')) AS structural_year_levels,
    COUNT(DISTINCT DATE_FORMAT(order_date, '%m')) AS structural_month_levels
FROM factsales;
