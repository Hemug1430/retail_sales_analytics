-- ============================================================
-- Retail Sales Analytics
-- Phase 05 - Database Loading & Integration
-- Step 05.04 - Create Core Store Table
-- ============================================================

USE retail_sales_db;

-- ============================================================
-- CREATE TRUSTED STORE MASTER TABLE
-- ============================================================

CREATE TABLE IF NOT EXISTS core_stores (

    -- ========================================================
    -- Business Attributes
    -- ========================================================

    store_id VARCHAR(10) NOT NULL,

    store_name VARCHAR(100) NOT NULL,

    store_type VARCHAR(25) NOT NULL,

    city VARCHAR(60) NOT NULL,

    state VARCHAR(60) NOT NULL,

    region VARCHAR(20) NOT NULL,

    postal_code VARCHAR(10) NOT NULL,

    opening_date DATE NOT NULL,

    floor_area_sqft INT,

    manager_name VARCHAR(100),

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

    CONSTRAINT pk_core_stores
        PRIMARY KEY (store_id),

    -- ========================================================
    -- Business Domain Constraints
    -- ========================================================

    CONSTRAINT chk_core_stores_type
        CHECK (
            store_type IN (
                'Mall',
                'High Street',
                'Outlet',
                'Neighborhood'
            )
        ),

    CONSTRAINT chk_core_stores_region
        CHECK (
            region IN (
                'North',
                'South',
                'East',
                'West',
                'Central'
            )
        ),

    CONSTRAINT chk_core_stores_status
        CHECK (
            status IN (
                'Active',
                'Temporarily Closed',
                'Closed'
            )
        ),

    CONSTRAINT chk_core_stores_floor_area
        CHECK (
            floor_area_sqft IS NULL
            OR floor_area_sqft >= 0
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
  AND table_name = 'core_stores';


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
  AND table_name = 'core_stores'
ORDER BY ordinal_position;




USE retail_sales_db;

SHOW TABLES LIKE 'core_stores';