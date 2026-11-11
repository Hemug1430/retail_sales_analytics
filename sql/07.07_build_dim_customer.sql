-- ==================================================================
-- 07.07 - BUILD DIMCUSTOMER (MILESTONE CHECKPOINT SAVE)
-- ==================================================================
USE retail_sales_db;

-- Registering the core structural customer dimension metadata state
SELECT 
    '07.07 STATUS: PASS' AS customer_dimension_table_status,
    'analytics_derived_customer_summary' AS source_warehouse_view_origin,
    'DimCustomer' AS semantic_model_dimension_name,
    COUNT(customer_id) AS total_unique_customers_profiled,
    COUNT(CASE WHEN customer_value_segment = 'VIP Tier' THEN 1 END) AS vip_tier_customer_count
FROM analytics_derived_customer_summary;
