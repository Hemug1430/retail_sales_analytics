USE retail_sales_db;

-- ============================================================
-- 05.15 - CREATE MASTER HISTORY TABLES
-- Retail Sales Analytics Project
--
-- Purpose:
-- Create structural history tables for the trusted master/core
-- entities.
--
-- IMPORTANT:
-- This step creates the history-table structures only.
-- SCD history processing itself belongs to tracker step 05.27.
-- No history records are inserted in 05.15.
-- ============================================================


-- ============================================================
-- 1. CUSTOMER HISTORY
-- ============================================================

CREATE TABLE IF NOT EXISTS core_customers_history
LIKE core_customers;


-- ============================================================
-- 2. PRODUCT HISTORY
-- ============================================================

CREATE TABLE IF NOT EXISTS core_products_history
LIKE core_products;


-- ============================================================
-- 3. STORE HISTORY
-- ============================================================

CREATE TABLE IF NOT EXISTS core_stores_history
LIKE core_stores;


-- ============================================================
-- 4. SALESPERSON HISTORY
-- ============================================================

CREATE TABLE IF NOT EXISTS core_salespersons_history
LIKE core_salespersons;


-- ============================================================
-- 5. PROMOTION HISTORY
-- ============================================================

CREATE TABLE IF NOT EXISTS core_promotions_history
LIKE core_promotions;


-- ============================================================
-- VERIFICATION 1
-- Verify that all required history tables exist
-- ============================================================

SELECT
    TABLE_NAME
FROM information_schema.tables
WHERE TABLE_SCHEMA = 'retail_sales_db'
  AND TABLE_NAME IN (
      'core_customers_history',
      'core_products_history',
      'core_stores_history',
      'core_salespersons_history',
      'core_promotions_history'
  )
ORDER BY TABLE_NAME;


-- ============================================================
-- VERIFICATION 2
-- Show row counts
-- 05.15 should create EMPTY history tables.
-- ============================================================

SELECT
    'core_customers_history' AS table_name,
    COUNT(*) AS total_rows
FROM core_customers_history

UNION ALL

SELECT
    'core_products_history' AS table_name,
    COUNT(*) AS total_rows
FROM core_products_history

UNION ALL

SELECT
    'core_stores_history' AS table_name,
    COUNT(*) AS total_rows
FROM core_stores_history

UNION ALL

SELECT
    'core_salespersons_history' AS table_name,
    COUNT(*) AS total_rows
FROM core_salespersons_history

UNION ALL

SELECT
    'core_promotions_history' AS table_name,
    COUNT(*) AS total_rows
FROM core_promotions_history;


-- ============================================================
-- VERIFICATION 3
-- Confirm the history tables are empty
-- ============================================================

SELECT
    TABLE_NAME,
    TABLE_ROWS
FROM information_schema.tables
WHERE TABLE_SCHEMA = 'retail_sales_db'
  AND TABLE_NAME IN (
      'core_customers_history',
      'core_products_history',
      'core_stores_history',
      'core_salespersons_history',
      'core_promotions_history'
  )
ORDER BY TABLE_NAME;