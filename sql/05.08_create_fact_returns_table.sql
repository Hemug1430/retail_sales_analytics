-- ============================================================
-- Retail Sales Analytics
-- Phase 05 - Database Loading & Integration
-- Step 05.08 - Create FactReturns Table
-- ============================================================

USE retail_sales_db;

-- ============================================================
-- CREATE TRUSTED RETURNS FACT TABLE
-- Grain:
-- One row = one return event
-- ============================================================

CREATE TABLE IF NOT EXISTS FactReturns (

    -- ========================================================
    -- Return Identity / Sales Link
    -- Foreign keys will be added in Step 05.11
    -- ========================================================

    return_id VARCHAR(18) NOT NULL,

    sales_line_id VARCHAR(18) NOT NULL,

    -- ========================================================
    -- Return Attributes
    -- ========================================================

    return_date DATE NOT NULL,

    quantity_returned INT NOT NULL,

    return_reason VARCHAR(40) NOT NULL,

    return_status VARCHAR(20) NOT NULL,

    refund_method VARCHAR(25),

    refund_amount DECIMAL(12,2),

    processed_store_id VARCHAR(10),

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

    CONSTRAINT pk_fact_returns
        PRIMARY KEY (return_id),

    -- ========================================================
    -- Business Constraints
    -- ========================================================

    CONSTRAINT chk_fact_returns_quantity
        CHECK (
            quantity_returned > 0
        ),

    CONSTRAINT chk_fact_returns_reason
        CHECK (
            return_reason IN (
                'Damaged',
                'Wrong Product',
                'Quality Issue',
                'Size/Fit Issue',
                'Customer Changed Mind',
                'Late Delivery',
                'Other'
            )
        ),

    CONSTRAINT chk_fact_returns_status
        CHECK (
            return_status IN (
                'Requested',
                'Approved',
                'Rejected',
                'Refunded'
            )
        ),

    CONSTRAINT chk_fact_returns_refund_method
        CHECK (
            refund_method IS NULL
            OR refund_method IN (
                'Original Payment',
                'Store Credit',
                'Cash'
            )
        ),

    CONSTRAINT chk_fact_returns_refund_amount
        CHECK (
            refund_amount IS NULL
            OR refund_amount >= 0
        )
);


-- ============================================================
-- VERIFICATION 1
-- Confirm FactReturns exists
-- ============================================================

SELECT
    table_name
FROM information_schema.tables
WHERE table_schema = 'retail_sales_db'
  AND table_name = 'FactReturns';


-- ============================================================
-- VERIFICATION 2
-- Confirm FactReturns columns
-- ============================================================

SELECT
    column_name,
    column_type,
    is_nullable,
    column_key
FROM information_schema.columns
WHERE table_schema = 'retail_sales_db'
  AND table_name = 'FactReturns'
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
  AND table_name = 'FactReturns'
  AND constraint_type = 'PRIMARY KEY';
  
  
  SHOW TABLES LIKE 'factreturns';