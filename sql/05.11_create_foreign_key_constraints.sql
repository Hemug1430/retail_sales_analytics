-- ============================================================
-- Retail Sales Analytics
-- Phase 05 - Database Loading & Integration
-- Step 05.11 - Create Foreign-Key Constraints
-- ============================================================

USE retail_sales_db;


-- ============================================================
-- 1. core_salespersons → core_stores
-- Required relationship
-- ============================================================

ALTER TABLE core_salespersons
    ADD CONSTRAINT fk_core_salespersons_store
    FOREIGN KEY (store_id)
    REFERENCES core_stores (store_id);


-- ============================================================
-- 2. FactSales → core_customers
-- Optional relationship
-- NULL is allowed for anonymous / walk-in sales
-- ============================================================

ALTER TABLE FactSales
    ADD CONSTRAINT fk_fact_sales_customer
    FOREIGN KEY (customer_id)
    REFERENCES core_customers (customer_id);


-- ============================================================
-- 3. FactSales → core_products
-- Required relationship
-- ============================================================

ALTER TABLE FactSales
    ADD CONSTRAINT fk_fact_sales_product
    FOREIGN KEY (product_id)
    REFERENCES core_products (product_id);


-- ============================================================
-- 4. FactSales → core_stores
-- Required relationship
-- ============================================================

ALTER TABLE FactSales
    ADD CONSTRAINT fk_fact_sales_store
    FOREIGN KEY (store_id)
    REFERENCES core_stores (store_id);


-- ============================================================
-- 5. FactSales → core_salespersons
-- Optional / conditional relationship
-- NULL is permitted for applicable online transactions
-- ============================================================

ALTER TABLE FactSales
    ADD CONSTRAINT fk_fact_sales_salesperson
    FOREIGN KEY (salesperson_id)
    REFERENCES core_salespersons (salesperson_id);


-- ============================================================
-- 6. FactSales → core_promotions
-- Optional relationship
-- ============================================================

ALTER TABLE FactSales
    ADD CONSTRAINT fk_fact_sales_promotion
    FOREIGN KEY (promotion_id)
    REFERENCES core_promotions (promotion_id);


-- ============================================================
-- 7. FactReturns → FactSales
-- Required relationship
-- ============================================================

ALTER TABLE FactReturns
    ADD CONSTRAINT fk_fact_returns_sales_line
    FOREIGN KEY (sales_line_id)
    REFERENCES FactSales (sales_line_id);


-- ============================================================
-- 8. FactReturns → core_stores
-- Optional relationship
-- ============================================================

ALTER TABLE FactReturns
    ADD CONSTRAINT fk_fact_returns_processed_store
    FOREIGN KEY (processed_store_id)
    REFERENCES core_stores (store_id);


-- ============================================================
-- 9. FactTargets → core_stores
-- Required relationship
-- ============================================================

ALTER TABLE FactTargets
    ADD CONSTRAINT fk_fact_targets_store
    FOREIGN KEY (store_id)
    REFERENCES core_stores (store_id);


-- ============================================================
-- VERIFICATION 1
-- Count all foreign-key constraints created in the project
-- ============================================================

SELECT
    COUNT(*) AS foreign_key_count
FROM information_schema.table_constraints
WHERE constraint_schema = 'retail_sales_db'
  AND constraint_type = 'FOREIGN KEY';


-- ============================================================
-- VERIFICATION 2
-- List all foreign-key constraints
-- ============================================================

SELECT
    tc.table_name AS child_table,
    tc.constraint_name,
    kcu.column_name AS child_column,
    kcu.referenced_table_name AS parent_table,
    kcu.referenced_column_name AS parent_column
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_schema = kcu.constraint_schema
   AND tc.table_name = kcu.table_name
   AND tc.constraint_name = kcu.constraint_name
WHERE tc.constraint_schema = 'retail_sales_db'
  AND tc.constraint_type = 'FOREIGN KEY'
ORDER BY
    tc.table_name,
    tc.constraint_name;


-- ============================================================
-- VERIFICATION 3
-- Confirm the 9 project-required relationships specifically
-- ============================================================

SELECT
    tc.table_name AS child_table,
    tc.constraint_name,
    kcu.column_name AS child_column,
    kcu.referenced_table_name AS parent_table,
    kcu.referenced_column_name AS parent_column
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_schema = kcu.constraint_schema
   AND tc.table_name = kcu.table_name
   AND tc.constraint_name = kcu.constraint_name
WHERE tc.constraint_schema = 'retail_sales_db'
  AND tc.constraint_type = 'FOREIGN KEY'
  AND tc.constraint_name IN (
      'fk_core_salespersons_store',
      'fk_fact_sales_customer',
      'fk_fact_sales_product',
      'fk_fact_sales_store',
      'fk_fact_sales_salesperson',
      'fk_fact_sales_promotion',
      'fk_fact_returns_sales_line',
      'fk_fact_returns_processed_store',
      'fk_fact_targets_store'
  )
ORDER BY
    tc.table_name,
    tc.constraint_name;