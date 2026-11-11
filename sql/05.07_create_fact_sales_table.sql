-- ============================================================
-- Retail Sales Analytics
-- Phase 05 - Database Loading & Integration
-- Step 05.07 - Create FactSales Table
-- ============================================================

USE retail_sales_db;

-- ============================================================
-- CREATE TRUSTED SALES-LINE FACT TABLE
-- Grain:
-- One row = one product line in an order
-- sales_line_id must be unique
-- order_id may repeat
-- ============================================================

CREATE TABLE IF NOT EXISTS FactSales (

    -- ========================================================
    -- Transaction Identity
    -- ========================================================

    sales_line_id VARCHAR(18) NOT NULL,

    order_id VARCHAR(16) NOT NULL,

    order_date DATE NOT NULL,

    order_time TIME NOT NULL,

    -- ========================================================
    -- Dimension / Reference Business Keys
    -- Foreign keys will be added in Step 05.11
    -- ========================================================

    customer_id VARCHAR(12),

    product_id VARCHAR(12) NOT NULL,

    store_id VARCHAR(10) NOT NULL,

    salesperson_id VARCHAR(12),

    promotion_id VARCHAR(12),

    -- ========================================================
    -- Sales Transaction Attributes
    -- ========================================================

    sales_channel VARCHAR(20) NOT NULL,

    quantity INT NOT NULL,

    unit_selling_price DECIMAL(12,2) NOT NULL,

    discount_pct DECIMAL(5,2) NOT NULL,

    payment_method VARCHAR(25) NOT NULL,

    order_status VARCHAR(20) NOT NULL,

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

    CONSTRAINT pk_fact_sales
        PRIMARY KEY (sales_line_id),

    -- ========================================================
    -- Business Constraints
    -- ========================================================

    CONSTRAINT chk_fact_sales_quantity
        CHECK (
            quantity > 0
        ),

    CONSTRAINT chk_fact_sales_unit_price
        CHECK (
            unit_selling_price >= 0
        ),

    CONSTRAINT chk_fact_sales_discount
        CHECK (
            discount_pct >= 0
            AND discount_pct <= 100
        ),

    CONSTRAINT chk_fact_sales_channel
        CHECK (
            sales_channel IN (
                'Store',
                'Online'
            )
        ),

    CONSTRAINT chk_fact_sales_payment
        CHECK (
            payment_method IN (
                'Cash',
                'Card',
                'UPI',
                'Wallet',
                'Net Banking'
            )
        ),

    CONSTRAINT chk_fact_sales_status
        CHECK (
            order_status IN (
                'Completed',
                'Cancelled'
            )
        )
);


-- ============================================================
-- VERIFICATION 1
-- Confirm FactSales exists
-- ============================================================

SELECT
    table_name
FROM information_schema.tables
WHERE table_schema = 'retail_sales_db'
  AND table_name = 'FactSales';


-- ============================================================
-- VERIFICATION 2
-- Confirm FactSales columns
-- ============================================================

SELECT
    column_name,
    column_type,
    is_nullable,
    column_key
FROM information_schema.columns
WHERE table_schema = 'retail_sales_db'
  AND table_name = 'FactSales'
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
  AND table_name = 'FactSales'
  AND constraint_type = 'PRIMARY KEY';
  
  
  
  USE retail_sales_db;

SHOW TABLES LIKE 'factsales';