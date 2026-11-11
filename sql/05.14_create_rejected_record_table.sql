-- ============================================================
-- Retail Sales Analytics
-- Phase 05 - Database Loading & Integration
-- Step 05.14 - Create Rejected-Record Table
-- ============================================================

USE retail_sales_db;


-- ============================================================
-- CREATE GENERIC REJECTED-RECORD TABLE
--
-- Purpose:
-- Preserve rejected source records and their validation evidence
-- without modifying the original source files.
-- ============================================================

CREATE TABLE IF NOT EXISTS rejected_records (

    -- ========================================================
    -- Rejection Identity
    -- ========================================================

    rejected_record_id BIGINT NOT NULL AUTO_INCREMENT,

    batch_id VARCHAR(40) NOT NULL,

    source_file_name VARCHAR(255) NOT NULL,

    source_row_number INT,

    dataset_name VARCHAR(50) NOT NULL,

    -- ========================================================
    -- Business-Key / Record Identification
    -- ========================================================

    business_key VARCHAR(255),

    record_hash VARCHAR(64),

    -- ========================================================
    -- Rejection Classification
    -- ========================================================

    reject_code VARCHAR(50) NOT NULL,

    reject_message VARCHAR(1000) NOT NULL,

    reject_timestamp DATETIME NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    -- ========================================================
    -- Original Source Evidence
    --
    -- JSON preserves the rejected row without forcing the
    -- generic table to use dataset-specific columns.
    -- ========================================================

    raw_record JSON,

    -- ========================================================
    -- Processing Metadata
    -- ========================================================

    validation_stage VARCHAR(50),

    created_at DATETIME NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    -- ========================================================
    -- Primary Key
    -- ========================================================

    CONSTRAINT pk_rejected_records
        PRIMARY KEY (rejected_record_id),

    -- ========================================================
    -- Validation Constraints
    -- ========================================================

    CONSTRAINT chk_rejected_records_row_number
        CHECK (
            source_row_number IS NULL
            OR source_row_number > 0
        )
);


-- ============================================================
-- VERIFICATION 1
-- Confirm table exists
-- ============================================================

SELECT
    table_name
FROM information_schema.tables
WHERE table_schema = 'retail_sales_db'
  AND table_name = 'rejected_records';


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
  AND table_name = 'rejected_records'
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
  AND table_name = 'rejected_records'
  AND constraint_type = 'PRIMARY KEY';