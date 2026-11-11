-- ============================================================
-- Retail Sales Analytics
-- Phase 05 - Database Loading & Integration
-- Step 05.02 - Create Core Customer Table
-- ============================================================

USE retail_sales_db;

-- ============================================================
-- REMOVE OLD EMPTY TABLE
-- ============================================================

DROP TABLE IF EXISTS core_customers;


-- ============================================================
-- CREATE TRUSTED CUSTOMER MASTER TABLE
-- ============================================================

CREATE TABLE core_customers (

    -- ========================================================
    -- Business Attributes
    -- ========================================================

    customer_id VARCHAR(12) NOT NULL,
    customer_name VARCHAR(100) NOT NULL,

    gender VARCHAR(15),

    date_of_birth DATE,

    email VARCHAR(120),

    phone VARCHAR(15),

    city VARCHAR(60) NOT NULL,
    state VARCHAR(60) NOT NULL,
    region VARCHAR(20) NOT NULL,

    postal_code VARCHAR(10),

    registration_date DATE NOT NULL,

    customer_segment VARCHAR(20) NOT NULL,

    preferred_channel VARCHAR(20),

    status VARCHAR(15) NOT NULL,


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
    -- PRIMARY KEY
    -- ========================================================

    CONSTRAINT pk_core_customers
        PRIMARY KEY (customer_id),


    -- ========================================================
    -- BUSINESS DOMAIN CONSTRAINTS
    -- ========================================================

    -- Gender
    CONSTRAINT chk_core_customers_gender
        CHECK (
            gender IS NULL
            OR gender IN ('Male', 'Female', 'Other')
        ),


    -- Region
    CONSTRAINT chk_core_customers_region
        CHECK (
            region IN (
                'North',
                'South',
                'East',
                'West',
                'Central'
            )
        ),


    -- Customer Segment
    CONSTRAINT chk_core_customers_segment
        CHECK (
            customer_segment IN (
                'Occasional',
                'Regular',
                'Premium',
                'VIP'
            )
        ),


    -- Preferred Channel
    CONSTRAINT chk_core_customers_channel
        CHECK (
            preferred_channel IS NULL
            OR preferred_channel IN (
                'Online',
                'Mobile App',
                'Offline'
            )
        ),


    -- Customer Status
    CONSTRAINT chk_core_customers_status
        CHECK (
            status IN (
                'Active',
                'Inactive'
            )
        ),


    -- Date Validation
    CONSTRAINT chk_core_customers_dates
        CHECK (
            date_of_birth IS NULL
            OR date_of_birth < registration_date
        )

);


-- ============================================================
-- VERIFICATION 1
-- CONFIRM TABLE EXISTS
-- ============================================================

SELECT
    table_name
FROM information_schema.tables
WHERE table_schema = 'retail_sales_db'
  AND table_name = 'core_customers';


-- ============================================================
-- VERIFICATION 2
-- CONFIRM TABLE COLUMNS
-- ============================================================

SELECT
    column_name,
    column_type,
    is_nullable,
    column_key
FROM information_schema.columns
WHERE table_schema = 'retail_sales_db'
  AND table_name = 'core_customers'
ORDER BY ordinal_position;


-- ============================================================
-- VERIFICATION 3
-- CONFIRM PREFERRED CHANNEL RULE
-- ============================================================

SELECT
    constraint_name,
    check_clause
FROM information_schema.check_constraints
WHERE constraint_schema = 'retail_sales_db'
  AND constraint_name = 'chk_core_customers_channel';


-- ============================================================
-- VERIFICATION 4
-- CONFIRM TABLE IS EMPTY BEFORE LOAD
-- ============================================================

SELECT
    COUNT(*) AS core_customer_count
FROM core_customers;




USE retail_sales_db;

SELECT COUNT(*) AS core_customer_count
FROM core_customers;









USE retail_sales_db;

ALTER TABLE core_customers
DROP CHECK chk_core_customers_channel;

ALTER TABLE core_customers
ADD CONSTRAINT chk_core_customers_channel
CHECK (
    preferred_channel IS NULL
    OR preferred_channel IN (
        'Online',
        'Mobile App',
        'Offline'
    )
);

SELECT
    constraint_name,
    check_clause
FROM information_schema.check_constraints
WHERE constraint_schema = 'retail_sales_db'
  AND constraint_name = 'chk_core_customers_channel';

SELECT
    COUNT(*) AS core_customer_count
FROM core_customers;




USE retail_sales_db;

SHOW TABLES LIKE 'core_customers';