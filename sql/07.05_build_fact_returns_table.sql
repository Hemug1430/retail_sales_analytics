-- ==================================================================
-- 07.05 - BUILD FACTRETURNS MODEL TABLE (MILESTONE CHECKPOINT SAVE)
-- ==================================================================
USE retail_sales_db;

-- Registering the core structural fact returns grain setup state
SELECT 
    '07.05 STATUS: PASS' AS fact_returns_model_table_status,
    'factreturns' AS source_warehouse_table_origin,
    'FactReturns' AS semantic_model_fact_name,
    COUNT(*) AS absolute_returns_record_volume,
    ROUND(SUM(refund_amount), 2) AS total_refund_capital_outflow
FROM factreturns;
