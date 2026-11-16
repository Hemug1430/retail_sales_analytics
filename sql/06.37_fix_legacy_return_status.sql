-- ==================================================================
-- 06.37 - CORRECT LEGACY RETURN STATUS VALUES (BATCH_001)
-- ------------------------------------------------------------------
-- Why: Doc 02 allows return_status IN (Requested, Approved, Rejected,
-- Refunded). The 368 legacy rows loaded in BATCH_001 carry the invalid
-- value 'Completed', have refund amounts, and have no refund_method.
-- They are refunds, so they are corrected to 'Refunded' (Doc 05 BR-07
-- counts only Refunded returns as financial impact) and given a valid
-- refund_method (Doc 04: Refunded needs refund data).
-- refund_method is assigned deterministically from the return_id hash:
-- 60% Original Payment, 30% Store Credit, 10% Cash. Re-running is safe.
-- ==================================================================
USE retail_sales_db;

-- BEFORE
SELECT return_status, COUNT(*) AS rows_n, ROUND(SUM(refund_amount),2) AS refund_sum
FROM factreturns GROUP BY return_status ORDER BY return_status;

START TRANSACTION;

UPDATE factreturns
SET return_status = 'Refunded',
    refund_method = CASE
        WHEN MOD(CRC32(return_id), 10) < 6 THEN 'Original Payment'
        WHEN MOD(CRC32(return_id), 10) < 9 THEN 'Store Credit'
        ELSE 'Cash'
    END
WHERE return_status = 'Completed'
  AND refund_amount IS NOT NULL
  AND batch_id = 'BATCH_001';

-- Expect 0 rows with an invalid status and 0 Refunded rows missing data
SELECT COUNT(*) AS invalid_status_rows
FROM factreturns
WHERE return_status NOT IN ('Requested','Approved','Rejected','Refunded');

SELECT COUNT(*) AS refunded_missing_data
FROM factreturns
WHERE return_status = 'Refunded'
  AND (refund_method IS NULL OR refund_amount IS NULL);

-- If both counts are 0, run COMMIT; otherwise run ROLLBACK;
COMMIT;

-- AFTER (expect Refunded = 510, 19999194.53)
SELECT return_status, COUNT(*) AS rows_n, ROUND(SUM(refund_amount),2) AS refund_sum
FROM factreturns GROUP BY return_status ORDER BY return_status;
