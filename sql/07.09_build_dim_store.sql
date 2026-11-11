-- ==================================================================
-- 07.09 - BUILD DIMSTORE (MILESTONE CHECKPOINT SAVE)
-- ==================================================================
USE retail_sales_db;

-- Registering the core structural store dimension metadata state
SELECT 
    '07.09 STATUS: PASS' AS store_dimension_table_status,
    'analytics_derived_store_summary' AS source_warehouse_view_origin,
    'DimStore' AS semantic_model_dimension_name,
    COUNT(store_id) AS total_active_stores_profiled,
    COUNT(CASE WHEN operational_performance_tier = 'Top Performing Hub' THEN 1 END) AS top_performing_hub_count
FROM analytics_derived_store_summary;
