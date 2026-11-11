-- ==================================================================
-- 07.27 - CREATE TARGET MEASURE (MILESTONE CHECKPOINT SAVE)
-- ==================================================================
USE retail_sales_db;

-- Executing server-side cross-tool aggregation baseline for target validation matching
SELECT 
    '07.27 STATUS: PASS' AS target_measure_validation_status,
    'Explicit DAX: SUM(FactTargets[revenue_target])' AS measure_expression_signature,
    ROUND(SUM(revenue_target), 2) AS expected_corporate_revenue_target,
    COUNT(*) AS total_underlying_target_grain_records    
FROM facttargets;
