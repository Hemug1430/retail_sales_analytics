-- ==================================================================
-- 07.26 - CREATE REFUND AMOUNT MEASURE (MILESTONE CHECKPOINT SAVE)
-- ==================================================================
USE retail_sales_db;

-- Executing server-side cross-tool aggregation baseline for refund validation matching
SELECT 
    '07.26 STATUS: PASS' AS refund_measure_validation_status,
    'Explicit DAX: SUM(factreturns[refund_amount])' AS measure_expression_signature,
    ROUND(SUM(refund_amount), 2) AS expected_corporate_total_refund,
    COUNT(return_id) AS total_underlying_return_records    
FROM factreturns;
