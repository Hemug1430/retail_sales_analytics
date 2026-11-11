-- ============================================================
-- Retail Sales Analytics
-- Phase 05 - Database Loading & Integration
-- Step 05.06 - Create Core Promotion Table
-- ============================================================

USE retail_sales_db;

-- ============================================================
-- CREATE TRUSTED PROMOTION MASTER TABLE
-- ============================================================

CREATE TABLE IF NOT EXISTS core_promotions (

    -- ========================================================
    -- Business Attributes
    -- ========================================================

    promotion_id VARCHAR(12) NOT NULL,

    promotion_name VARCHAR(100) NOT NULL,

    promotion_type VARCHAR(30) NOT NULL,

    start_date DATE NOT NULL,

    end_date DATE NOT NULL,

    discount_pct DECIMAL(5,2) NOT NULL,

    applicable_category VARCHAR(40),

    applicable_channel VARCHAR(20) NOT NULL,

    minimum_order_value DECIMAL(12,2),

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

    CONSTRAINT pk_core_promotions
        PRIMARY KEY (promotion_id),

    -- ========================================================
    -- Business Domain Constraints
    -- ========================================================

    CONSTRAINT chk_core_promotions_type
        CHECK (
            promotion_type IN (
                'Seasonal',
                'Category',
                'Storewide',
                'Channel'
            )
        ),

    CONSTRAINT chk_core_promotions_channel
        CHECK (
            applicable_channel IN (
                'Store',
                'Online',
                'ALL'
            )
        ),

    CONSTRAINT chk_core_promotions_status
        CHECK (
            status IN (
                'Planned',
                'Active',
                'Expired',
                'Cancelled'
            )
        ),

    CONSTRAINT chk_core_promotions_dates
        CHECK (
            end_date >= start_date
        ),

    CONSTRAINT chk_core_promotions_discount
        CHECK (
            discount_pct >= 0
            AND discount_pct <= 100
        ),

    CONSTRAINT chk_core_promotions_min_order
        CHECK (
            minimum_order_value IS NULL
            OR minimum_order_value >= 0
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
  AND table_name = 'core_promotions';


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
  AND table_name = 'core_promotions'
ORDER BY ordinal_position;



USE retail_sales_db;

SHOW TABLES LIKE 'core_promotions';