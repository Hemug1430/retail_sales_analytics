-- ============================================================
-- Retail Sales Analytics
-- Phase 05 - Database Loading & Integration
-- Step 05.03 - Create Core Product Table
-- ============================================================

USE retail_sales_db;

-- ============================================================
-- CREATE TRUSTED PRODUCT MASTER TABLE
-- ============================================================

CREATE TABLE IF NOT EXISTS core_products (

    -- ========================================================
    -- Business Attributes
    -- ========================================================

    product_id VARCHAR(12) NOT NULL,

    product_name VARCHAR(120) NOT NULL,

    category VARCHAR(40) NOT NULL,

    subcategory VARCHAR(60) NOT NULL,

    brand VARCHAR(60) NOT NULL,

    unit_cost DECIMAL(12,2) NOT NULL,

    list_price DECIMAL(12,2) NOT NULL,

    tax_rate_pct DECIMAL(5,2) NOT NULL,

    launch_date DATE NOT NULL,

    status VARCHAR(20) NOT NULL,

    -- ========================================================
    -- ETL Audit / Traceability Columns
    -- ========================================================

    batch_id VARCHAR(40) NOT NULL,

    source_file_name VARCHAR(255) NOT NULL,

    source_row_number INT,

    record_hash VARCHAR(64),

    load_timestamp DATETIME NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    created_at DATETIME NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    updated_at DATETIME NOT NULL
        DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    -- ========================================================
    -- Primary Key
    -- ========================================================

    CONSTRAINT pk_core_products
        PRIMARY KEY (product_id),

    -- ========================================================
    -- Business Domain Constraints
    -- ========================================================

    CONSTRAINT chk_core_products_category
        CHECK (
            category IN (
                'Electronics',
                'Home & Kitchen',
                'Fashion',
                'Beauty & Personal Care',
                'Sports & Fitness',
                'Grocery'
            )
        ),

    CONSTRAINT chk_core_products_status
        CHECK (
            status IN (
                'Active',
                'Discontinued',
                'Suspended'
            )
        ),

    CONSTRAINT chk_core_products_unit_cost
        CHECK (
            unit_cost >= 0
        ),

    CONSTRAINT chk_core_products_list_price
        CHECK (
            list_price >= 0
        ),

    CONSTRAINT chk_core_products_tax_rate
        CHECK (
            tax_rate_pct >= 0
            AND tax_rate_pct <= 100
        ),

    CONSTRAINT chk_core_products_price_relationship
        CHECK (
            list_price >= unit_cost
        )
);


-- ============================================================
-- VERIFICATION 1
-- Confirm the table exists
-- ============================================================

SELECT
    table_name
FROM information_schema.tables
WHERE table_schema = 'retail_sales_db'
  AND table_name = 'core_products';


-- ============================================================
-- VERIFICATION 2
-- Confirm table columns
-- ============================================================

SELECT
    column_name,
    column_type,
    is_nullable,
    column_key
FROM information_schema.columns
WHERE table_schema = 'retail_sales_db'
  AND table_name = 'core_products'
ORDER BY ordinal_position;




SHOW TABLES LIKE 'core_products';