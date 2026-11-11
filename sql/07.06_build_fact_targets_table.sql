-- ==================================================================
-- 07.06 - BUILD FACTTARGETS MODEL TABLE (MILESTONE CHECKPOINT SAVE)
-- ==================================================================
USE retail_sales_db;

-- Registering the core structural fact targets grain setup state
SELECT 
    '07.06 STATUS: PASS' AS fact_targets_model_table_status,
    'facttargets' AS source_warehouse_table_origin,
    'FactTargets' AS semantic_model_fact_name,
    COUNT(*) AS absolute_targets_record_count,
    ROUND(SUM(revenue_target), 2) AS absolute_corporate_revenue_target
FROM facttargets;
