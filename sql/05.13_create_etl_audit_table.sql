-- ============================================================
-- Retail Sales Analytics
-- Phase 05 - Database Loading & Integration
-- Step 05.13 - Create ETL Audit Table
-- ============================================================

USE retail_sales_db;


-- ============================================================
-- CREATE AUTHORITATIVE FILE/BATCH PROCESSING AUDIT TABLE
--
-- One row = one processing attempt for one source file
-- ============================================================

CREATE TABLE IF NOT EXISTS etl_file_log (

    -- ========================================================
    -- File / Batch Identity
    -- ========================================================

    file_id VARCHAR(64) NOT NULL,

    batch_id VARCHAR(40) NOT NULL,

    file_name VARCHAR(255) NOT NULL,

    file_type VARCHAR(20) NOT NULL,

    file_period VARCHAR(7),

    file_size_bytes BIGINT,

    sha256_hash CHAR(64) NOT NULL,

    schema_fingerprint VARCHAR(128),

    -- ========================================================
    -- Processing Counts
    -- ========================================================

    records_read BIGINT NOT NULL DEFAULT 0,

    records_staged BIGINT NOT NULL DEFAULT 0,

    records_inserted BIGINT NOT NULL DEFAULT 0,

    records_updated BIGINT NOT NULL DEFAULT 0,

    records_unchanged BIGINT NOT NULL DEFAULT 0,

    records_duplicated BIGINT NOT NULL DEFAULT 0,

    records_rejected BIGINT NOT NULL DEFAULT 0,

    -- ========================================================
    -- Processing Timing
    -- ========================================================

    load_start_time DATETIME NOT NULL,

    load_end_time DATETIME,

    duration_seconds DECIMAL(12,3),

    -- ========================================================
    -- Processing Status
    -- ========================================================

    load_status VARCHAR(30) NOT NULL,

    correction_mode VARCHAR(30),

    retry_of_file_id VARCHAR(64),

    -- ========================================================
    -- Error Information
    -- ========================================================

    error_class VARCHAR(30),

    error_code VARCHAR(50),

    error_message VARCHAR(1000),

    -- ========================================================
    -- Archive / Quarantine Information
    -- ========================================================

    archive_path VARCHAR(500),

    quarantine_path VARCHAR(500),

    -- ========================================================
    -- Technical Audit Timestamps
    -- ========================================================

    created_at DATETIME NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    updated_at DATETIME NOT NULL
        DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    -- ========================================================
    -- Primary Key
    -- ========================================================

    CONSTRAINT pk_etl_file_log
        PRIMARY KEY (file_id),

    -- ========================================================
    -- Processing Status Constraint
    -- ========================================================

    CONSTRAINT chk_etl_file_log_status
        CHECK (
            load_status IN (
                'RECEIVED',
                'VALIDATING',
                'STAGED',
                'MERGING',
                'SUCCESS',
                'SUCCESS_WITH_REJECTS',
                'SKIPPED_DUPLICATE',
                'QUARANTINED',
                'FAILED'
            )
        ),

    -- ========================================================
    -- Count Validation
    -- ========================================================

    CONSTRAINT chk_etl_file_log_records_read
        CHECK (records_read >= 0),

    CONSTRAINT chk_etl_file_log_records_staged
        CHECK (records_staged >= 0),

    CONSTRAINT chk_etl_file_log_records_inserted
        CHECK (records_inserted >= 0),

    CONSTRAINT chk_etl_file_log_records_updated
        CHECK (records_updated >= 0),

    CONSTRAINT chk_etl_file_log_records_unchanged
        CHECK (records_unchanged >= 0),

    CONSTRAINT chk_etl_file_log_records_duplicated
        CHECK (records_duplicated >= 0),

    CONSTRAINT chk_etl_file_log_records_rejected
        CHECK (records_rejected >= 0),

    -- ========================================================
    -- File Size Validation
    -- ========================================================

    CONSTRAINT chk_etl_file_log_file_size
        CHECK (
            file_size_bytes IS NULL
            OR file_size_bytes >= 0
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
  AND table_name = 'etl_file_log';


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
  AND table_name = 'etl_file_log'
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
  AND table_name = 'etl_file_log'
  AND constraint_type = 'PRIMARY KEY';


-- ============================================================
-- VERIFICATION 4
-- Confirm status constraint
-- ============================================================

SELECT
    constraint_name,
    constraint_type
FROM information_schema.table_constraints
WHERE table_schema = 'retail_sales_db'
  AND table_name = 'etl_file_log'
  AND constraint_name = 'chk_etl_file_log_status';