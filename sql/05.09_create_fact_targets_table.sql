-- ============================================================
-- Retail Sales Analytics
-- Phase 05 - Database Loading & Integration
-- Step 05.09 - Create FactTargets Table
-- ============================================================

USE retail_sales_db;

-- ============================================================
-- CREATE TRUSTED TARGET FACT TABLE
--
-- Approved grain:
-- One row = one target for one month + one store + category
--
-- Foreign keys will be added in Step 05.11.
-- ============================================================

CREATE TABLE IF NOT EXISTS FactTargets (

    -- ========================================================
    -- Target Identity / Grain
    -- ========================================================

    target_id VARCHAR(18) NOT NULL,

    target_month DATE NOT NULL,

    store_id VARCHAR(10) NOT NULL,

    category VARCHAR(40) NOT NULL,

    -- ========================================================
    -- Target Measures
    -- ========================================================

    revenue_target DECIMAL(14,2) NOT NULL,

    profit_target DECIMAL(14,2) NOT NULL,

    order_target INT NOT NULL,

    return_rate_target_pct DECIMAL(5,2) NOT NULL,

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

    CONSTRAINT pk_fact_targets
        PRIMARY KEY (target_id),

    -- ========================================================
    -- Business Constraints
    -- ========================================================

    CONSTRAINT chk_fact_targets_category
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

    CONSTRAINT chk_fact_targets_revenue
        CHECK (
            revenue_target >= 0
        ),

    CONSTRAINT chk_fact_targets_profit
        CHECK (
            profit_target >= 0
        ),

    CONSTRAINT chk_fact_targets_orders
        CHECK (
            order_target >= 0
        ),

    CONSTRAINT chk_fact_targets_return_rate
        CHECK (
            return_rate_target_pct >= 0
            AND return_rate_target_pct <= 100
        ),

    CONSTRAINT chk_fact_targets_month
        CHECK (
            DAY(target_month) = 1
        )
);


-- ============================================================
-- VERIFICATION 1
-- Confirm FactTargets exists
-- ============================================================

SELECT
    table_name
FROM information_schema.tables
WHERE table_schema = 'retail_sales_db'
  AND table_name = 'FactTargets';


-- ============================================================
-- VERIFICATION 2
-- Confirm FactTargets columns
-- ============================================================

SELECT
    column_name,
    column_type,
    is_nullable,
    column_key
FROM information_schema.columns
WHERE table_schema = 'retail_sales_db'
  AND table_name = 'FactTargets'
ORDER BY ordinal_position;


-- ============================================================
-- VERIFICATION 3
-- Confirm primary key
-- ============================================================

SELECT
    constraint_name,
    constraint_type
FROM information_schema.table_constraints
WHERE table_schema = 'retail_sales_db'
  AND table_name = 'FactTargets'
  AND constraint_type = 'PRIMARY KEY';
  
  
  SHOW TABLES LIKE 'facttargets';