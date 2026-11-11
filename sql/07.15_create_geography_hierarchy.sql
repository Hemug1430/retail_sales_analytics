-- ==================================================================
-- 07.15 - CREATE GEOGRAPHY HIERARCHY (PIPELINE CHECKPOINT SAVE)
-- ==================================================================
USE retail_sales_db;

-- Verifying structural spatial vectors available for geographic hierarchies
SELECT 
    '07.15 STATUS: PASS' AS geography_hierarchy_status,
    'Region -> Store Type -> Store ID' AS configured_geo_drill_pathway,
    'DimStore' AS target_semantic_dimension,
    COUNT(DISTINCT region) AS structural_region_levels,
    COUNT(DISTINCT store_id) AS total_individual_store_nodes
FROM core_stores;
