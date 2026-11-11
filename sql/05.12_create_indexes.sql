-- ============================================================
-- Retail Sales Analytics
-- Phase 05 - Database Loading & Integration
-- Step 05.12 - Create Indexes
-- ============================================================

USE retail_sales_db;


-- ============================================================
-- Helper pattern:
-- Check information_schema before creating each index.
-- This makes the script safe to rerun.
-- ============================================================


-- ============================================================
-- CORE CUSTOMERS
-- ============================================================

SET @exists = (
    SELECT COUNT(*)
    FROM information_schema.statistics
    WHERE table_schema = 'retail_sales_db'
      AND table_name = 'core_customers'
      AND index_name = 'idx_core_customers_batch'
);

SET @sql = IF(
    @exists = 0,
    'CREATE INDEX idx_core_customers_batch
     ON core_customers (batch_id)',
    'SELECT ''idx_core_customers_batch already exists'' AS message'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;


SET @exists = (
    SELECT COUNT(*)
    FROM information_schema.statistics
    WHERE table_schema = 'retail_sales_db'
      AND table_name = 'core_customers'
      AND index_name = 'idx_core_customers_region_status'
);

SET @sql = IF(
    @exists = 0,
    'CREATE INDEX idx_core_customers_region_status
     ON core_customers (region, status)',
    'SELECT ''idx_core_customers_region_status already exists'' AS message'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;


-- ============================================================
-- CORE PRODUCTS
-- ============================================================

SET @exists = (
    SELECT COUNT(*)
    FROM information_schema.statistics
    WHERE table_schema = 'retail_sales_db'
      AND table_name = 'core_products'
      AND index_name = 'idx_core_products_batch'
);

SET @sql = IF(
    @exists = 0,
    'CREATE INDEX idx_core_products_batch
     ON core_products (batch_id)',
    'SELECT ''idx_core_products_batch already exists'' AS message'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;


SET @exists = (
    SELECT COUNT(*)
    FROM information_schema.statistics
    WHERE table_schema = 'retail_sales_db'
      AND table_name = 'core_products'
      AND index_name = 'idx_core_products_category_status'
);

SET @sql = IF(
    @exists = 0,
    'CREATE INDEX idx_core_products_category_status
     ON core_products (category, status)',
    'SELECT ''idx_core_products_category_status already exists'' AS message'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;


-- ============================================================
-- CORE STORES
-- ============================================================

SET @exists = (
    SELECT COUNT(*)
    FROM information_schema.statistics
    WHERE table_schema = 'retail_sales_db'
      AND table_name = 'core_stores'
      AND index_name = 'idx_core_stores_batch'
);

SET @sql = IF(
    @exists = 0,
    'CREATE INDEX idx_core_stores_batch
     ON core_stores (batch_id)',
    'SELECT ''idx_core_stores_batch already exists'' AS message'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;


SET @exists = (
    SELECT COUNT(*)
    FROM information_schema.statistics
    WHERE table_schema = 'retail_sales_db'
      AND table_name = 'core_stores'
      AND index_name = 'idx_core_stores_region_status'
);

SET @sql = IF(
    @exists = 0,
    'CREATE INDEX idx_core_stores_region_status
     ON core_stores (region, status)',
    'SELECT ''idx_core_stores_region_status already exists'' AS message'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;


-- ============================================================
-- CORE SALESPERSONS
-- ============================================================

SET @exists = (
    SELECT COUNT(*)
    FROM information_schema.statistics
    WHERE table_schema = 'retail_sales_db'
      AND table_name = 'core_salespersons'
      AND index_name = 'idx_core_salespersons_batch'
);

SET @sql = IF(
    @exists = 0,
    'CREATE INDEX idx_core_salespersons_batch
     ON core_salespersons (batch_id)',
    'SELECT ''idx_core_salespersons_batch already exists'' AS message'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;


SET @exists = (
    SELECT COUNT(*)
    FROM information_schema.statistics
    WHERE table_schema = 'retail_sales_db'
      AND table_name = 'core_salespersons'
      AND index_name = 'idx_core_salespersons_store_status'
);

SET @sql = IF(
    @exists = 0,
    'CREATE INDEX idx_core_salespersons_store_status
     ON core_salespersons (store_id, status)',
    'SELECT ''idx_core_salespersons_store_status already exists'' AS message'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;


-- ============================================================
-- CORE PROMOTIONS
-- ============================================================

SET @exists = (
    SELECT COUNT(*)
    FROM information_schema.statistics
    WHERE table_schema = 'retail_sales_db'
      AND table_name = 'core_promotions'
      AND index_name = 'idx_core_promotions_batch'
);

SET @sql = IF(
    @exists = 0,
    'CREATE INDEX idx_core_promotions_batch
     ON core_promotions (batch_id)',
    'SELECT ''idx_core_promotions_batch already exists'' AS message'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;


SET @exists = (
    SELECT COUNT(*)
    FROM information_schema.statistics
    WHERE table_schema = 'retail_sales_db'
      AND table_name = 'core_promotions'
      AND index_name = 'idx_core_promotions_dates'
);

SET @sql = IF(
    @exists = 0,
    'CREATE INDEX idx_core_promotions_dates
     ON core_promotions (start_date, end_date)',
    'SELECT ''idx_core_promotions_dates already exists'' AS message'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;


-- ============================================================
-- FACT SALES
-- ============================================================

SET @exists = (
    SELECT COUNT(*)
    FROM information_schema.statistics
    WHERE table_schema = 'retail_sales_db'
      AND table_name = 'FactSales'
      AND index_name = 'idx_fact_sales_batch'
);

SET @sql = IF(
    @exists = 0,
    'CREATE INDEX idx_fact_sales_batch
     ON FactSales (batch_id)',
    'SELECT ''idx_fact_sales_batch already exists'' AS message'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;


SET @exists = (
    SELECT COUNT(*)
    FROM information_schema.statistics
    WHERE table_schema = 'retail_sales_db'
      AND table_name = 'FactSales'
      AND index_name = 'idx_fact_sales_order_date'
);

SET @sql = IF(
    @exists = 0,
    'CREATE INDEX idx_fact_sales_order_date
     ON FactSales (order_date)',
    'SELECT ''idx_fact_sales_order_date already exists'' AS message'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;


SET @exists = (
    SELECT COUNT(*)
    FROM information_schema.statistics
    WHERE table_schema = 'retail_sales_db'
      AND table_name = 'FactSales'
      AND index_name = 'idx_fact_sales_customer'
);

SET @sql = IF(
    @exists = 0,
    'CREATE INDEX idx_fact_sales_customer
     ON FactSales (customer_id)',
    'SELECT ''idx_fact_sales_customer already exists'' AS message'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;


SET @exists = (
    SELECT COUNT(*)
    FROM information_schema.statistics
    WHERE table_schema = 'retail_sales_db'
      AND table_name = 'FactSales'
      AND index_name = 'idx_fact_sales_product'
);

SET @sql = IF(
    @exists = 0,
    'CREATE INDEX idx_fact_sales_product
     ON FactSales (product_id)',
    'SELECT ''idx_fact_sales_product already exists'' AS message'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;


SET @exists = (
    SELECT COUNT(*)
    FROM information_schema.statistics
    WHERE table_schema = 'retail_sales_db'
      AND table_name = 'FactSales'
      AND index_name = 'idx_fact_sales_store_date'
);

SET @sql = IF(
    @exists = 0,
    'CREATE INDEX idx_fact_sales_store_date
     ON FactSales (store_id, order_date)',
    'SELECT ''idx_fact_sales_store_date already exists'' AS message'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;


SET @exists = (
    SELECT COUNT(*)
    FROM information_schema.statistics
    WHERE table_schema = 'retail_sales_db'
      AND table_name = 'FactSales'
      AND index_name = 'idx_fact_sales_salesperson'
);

SET @sql = IF(
    @exists = 0,
    'CREATE INDEX idx_fact_sales_salesperson
     ON FactSales (salesperson_id)',
    'SELECT ''idx_fact_sales_salesperson already exists'' AS message'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;


SET @exists = (
    SELECT COUNT(*)
    FROM information_schema.statistics
    WHERE table_schema = 'retail_sales_db'
      AND table_name = 'FactSales'
      AND index_name = 'idx_fact_sales_promotion'
);

SET @sql = IF(
    @exists = 0,
    'CREATE INDEX idx_fact_sales_promotion
     ON FactSales (promotion_id)',
    'SELECT ''idx_fact_sales_promotion already exists'' AS message'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;


-- ============================================================
-- FACT RETURNS
-- ============================================================

SET @exists = (
    SELECT COUNT(*)
    FROM information_schema.statistics
    WHERE table_schema = 'retail_sales_db'
      AND table_name = 'FactReturns'
      AND index_name = 'idx_fact_returns_batch'
);

SET @sql = IF(
    @exists = 0,
    'CREATE INDEX idx_fact_returns_batch
     ON FactReturns (batch_id)',
    'SELECT ''idx_fact_returns_batch already exists'' AS message'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;


SET @exists = (
    SELECT COUNT(*)
    FROM information_schema.statistics
    WHERE table_schema = 'retail_sales_db'
      AND table_name = 'FactReturns'
      AND index_name = 'idx_fact_returns_date'
);

SET @sql = IF(
    @exists = 0,
    'CREATE INDEX idx_fact_returns_date
     ON FactReturns (return_date)',
    'SELECT ''idx_fact_returns_date already exists'' AS message'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;


SET @exists = (
    SELECT COUNT(*)
    FROM information_schema.statistics
    WHERE table_schema = 'retail_sales_db'
      AND table_name = 'FactReturns'
      AND index_name = 'idx_fact_returns_sales_line'
);

SET @sql = IF(
    @exists = 0,
    'CREATE INDEX idx_fact_returns_sales_line
     ON FactReturns (sales_line_id)',
    'SELECT ''idx_fact_returns_sales_line already exists'' AS message'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;


SET @exists = (
    SELECT COUNT(*)
    FROM information_schema.statistics
    WHERE table_schema = 'retail_sales_db'
      AND table_name = 'FactReturns'
      AND index_name = 'idx_fact_returns_processed_store'
);

SET @sql = IF(
    @exists = 0,
    'CREATE INDEX idx_fact_returns_processed_store
     ON FactReturns (processed_store_id)',
    'SELECT ''idx_fact_returns_processed_store already exists'' AS message'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;


-- ============================================================
-- FACT TARGETS
-- ============================================================

SET @exists = (
    SELECT COUNT(*)
    FROM information_schema.statistics
    WHERE table_schema = 'retail_sales_db'
      AND table_name = 'FactTargets'
      AND index_name = 'idx_fact_targets_batch'
);

SET @sql = IF(
    @exists = 0,
    'CREATE INDEX idx_fact_targets_batch
     ON FactTargets (batch_id)',
    'SELECT ''idx_fact_targets_batch already exists'' AS message'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;


-- ============================================================
-- Verification 1
-- Show all non-primary indexes created by this step
-- ============================================================

SELECT
    table_name,
    index_name,
    GROUP_CONCAT(
        column_name
        ORDER BY seq_in_index
    ) AS indexed_columns,
    non_unique
FROM information_schema.statistics
WHERE table_schema = 'retail_sales_db'
  AND index_name LIKE 'idx_%'
GROUP BY
    table_name,
    index_name,
    non_unique
ORDER BY
    table_name,
    index_name;


-- ============================================================
-- Verification 2
-- Count indexes created by this step
-- ============================================================

SELECT
    COUNT(DISTINCT index_name) AS project_index_count
FROM information_schema.statistics
WHERE table_schema = 'retail_sales_db'
  AND index_name LIKE 'idx_%';