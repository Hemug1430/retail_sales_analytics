-- ============================================================
-- Retail Sales Analytics
-- Phase 05 - Database Loading & Integration
-- Step 05.10 - Create Primary-Key / Unique Constraints
-- ============================================================

USE retail_sales_db;


-- ============================================================
-- 1. ADD UNIQUE BUSINESS-GRAIN CONSTRAINT FOR FACT TARGETS
--
-- Approved grain:
-- One row = one month + one store + one category
--
-- Primary key target_id already exists.
-- ============================================================

SET @constraint_exists = (
    SELECT COUNT(*)
    FROM information_schema.table_constraints
    WHERE constraint_schema = 'retail_sales_db'
      AND table_name = 'FactTargets'
      AND constraint_name = 'uq_fact_targets_month_store_category'
);

SET @sql = IF(
    @constraint_exists = 0,
    'ALTER TABLE FactTargets
     ADD CONSTRAINT uq_fact_targets_month_store_category
     UNIQUE (target_month, store_id, category)',
    'SELECT ''Unique business-grain constraint already exists'' AS message'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;


-- ============================================================
-- 2. VERIFY PRIMARY KEYS FOR ALL TRUSTED TABLES
-- ============================================================

SELECT
    table_name,
    constraint_name,
    constraint_type
FROM information_schema.table_constraints
WHERE constraint_schema = 'retail_sales_db'
  AND constraint_type = 'PRIMARY KEY'
  AND table_name IN (
      'core_customers',
      'core_products',
      'core_stores',
      'core_salespersons',
      'core_promotions',
      'FactSales',
      'FactReturns',
      'FactTargets'
  )
ORDER BY table_name;


-- ============================================================
-- 3. VERIFY PRIMARY-KEY COLUMNS
-- ============================================================

SELECT
    kcu.table_name,
    kcu.constraint_name,
    kcu.column_name,
    kcu.ordinal_position
FROM information_schema.key_column_usage AS kcu
WHERE kcu.constraint_schema = 'retail_sales_db'
  AND kcu.constraint_name = 'PRIMARY'
  AND kcu.table_name IN (
      'core_customers',
      'core_products',
      'core_stores',
      'core_salespersons',
      'core_promotions',
      'FactSales',
      'FactReturns',
      'FactTargets'
  )
ORDER BY
    kcu.table_name,
    kcu.ordinal_position;


-- ============================================================
-- 4. VERIFY FACT TARGETS BUSINESS-GRAIN UNIQUE CONSTRAINT
-- ============================================================

SELECT
    tc.table_name,
    tc.constraint_name,
    tc.constraint_type
FROM information_schema.table_constraints AS tc
WHERE tc.constraint_schema = 'retail_sales_db'
  AND tc.table_name = 'FactTargets'
  AND tc.constraint_name = 'uq_fact_targets_month_store_category';


-- ============================================================
-- 5. VERIFY UNIQUE-CONSTRAINT COLUMNS
-- ============================================================

SELECT
    kcu.table_name,
    kcu.constraint_name,
    kcu.column_name,
    kcu.ordinal_position
FROM information_schema.key_column_usage AS kcu
WHERE kcu.constraint_schema = 'retail_sales_db'
  AND kcu.table_name = 'FactTargets'
  AND kcu.constraint_name = 'uq_fact_targets_month_store_category'
ORDER BY kcu.ordinal_position;