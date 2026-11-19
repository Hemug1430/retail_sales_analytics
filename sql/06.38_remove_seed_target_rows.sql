-- ==================================================================
-- 06.38 - REMOVE THE TWO HARD-CODED SEED TARGET ROWS
-- The old 05.25 script wrote TGT001 and TGT002 (2026-10-01) as demo rows
-- and loaded only those. Run this BEFORE loading the real targets.csv.
-- ==================================================================
USE retail_sales_db;

SELECT COUNT(*) AS rows_before FROM facttargets;
SELECT * FROM facttargets WHERE target_id IN ('TGT001','TGT002');

DELETE FROM facttargets WHERE target_id IN ('TGT001','TGT002');

SELECT COUNT(*) AS rows_after FROM facttargets;   -- expect 0
