-- ============================================================
-- Retail Sales Analytics
-- Phase 05 - Database Loading & Integration
-- Step 05.05 - Create Core Salesperson Table
-- ============================================================

USE retail_sales_db;

-- ============================================================
-- CREATE TRUSTED SALESPERSON MASTER TABLE
-- ============================================================

CREATE TABLE IF NOT EXISTS core_salespersons (

    -- ========================================================
    -- Business Attributes
    -- ========================================================

    salesperson_id VARCHAR(12) NOT NULL,

    salesperson_name VARCHAR(100) NOT NULL,

    store_id VARCHAR(10) NOT NULL,

    joining_date DATE NOT NULL,

    role VARCHAR(40) NOT NULL,

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

    CONSTRAINT pk_core_salespersons
        PRIMARY KEY (salesperson_id),

    -- ========================================================
    -- Business Domain Constraints
    -- ========================================================

    CONSTRAINT chk_core_salespersons_role
        CHECK (
            role IN (
                'Sales Associate',
                'Senior Sales Associate',
                'Store Supervisor'
            )
        ),

    CONSTRAINT chk_core_salespersons_status
        CHECK (
            status IN (
                'Active',
                'Inactive'
            )
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
  AND table_name = 'core_salespersons';


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
  AND table_name = 'core_salespersons'
ORDER BY ordinal_position;


USE retail_sales_db;

SHOW TABLES LIKE 'core_salespersons';