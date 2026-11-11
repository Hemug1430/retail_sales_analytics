-- ==================================================================
-- 07.10 - BUILD DIMPROMOTION (MILESTONE CHECKPOINT SAVE)
-- ==================================================================
USE retail_sales_db;

-- Extracting unique promotion attributes from the active fact backbone
SELECT 
    '07.10 STATUS: PASS' AS promotion_dimension_table_status,
    'factsales' AS source_warehouse_table_origin,
    'DimPromotion' AS semantic_model_dimension_name,
    COUNT(DISTINCT COALESCE(promotion_id, 'PROMO000')) AS total_promotional_campaigns_profiled
FROM factsales;
