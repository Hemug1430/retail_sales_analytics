-- ============================================================
-- Retail Sales Analytics
-- Phase 05 - Database Loading & Integration
-- Step 05.01 - Create Staging Tables
-- ============================================================

USE retail_sales_db;

-- ============================================================
-- 1. STG_CUSTOMERS
-- ============================================================

CREATE TABLE IF NOT EXISTS stg_customers (
    staging_id BIGINT AUTO_INCREMENT PRIMARY KEY,

    customer_id VARCHAR(12) NOT NULL,
    customer_name VARCHAR(100) NOT NULL,
    gender VARCHAR(15),
    date_of_birth DATE,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    region VARCHAR(20) NOT NULL,
    registration_date DATE NOT NULL,
    customer_segment VARCHAR(20) NOT NULL,
    email VARCHAR(150),
    phone VARCHAR(30),
    postal_code VARCHAR(20),
    preferred_channel VARCHAR(20),
    status VARCHAR(20) NOT NULL,

    batch_id VARCHAR(100) NOT NULL,
    source_file_name VARCHAR(255) NOT NULL,
    source_row_number BIGINT,
    record_hash CHAR(64),
    load_timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- ============================================================
-- 2. STG_PRODUCTS
-- ============================================================

CREATE TABLE IF NOT EXISTS stg_products (
    staging_id BIGINT AUTO_INCREMENT PRIMARY KEY,

    product_id VARCHAR(12) NOT NULL,
    product_name VARCHAR(150) NOT NULL,
    category VARCHAR(50) NOT NULL,
    subcategory VARCHAR(100) NOT NULL,
    brand VARCHAR(100) NOT NULL,
    unit_cost DECIMAL(14,2) NOT NULL,
    list_price DECIMAL(14,2) NOT NULL,
    tax_rate_pct DECIMAL(5,2) NOT NULL,
    launch_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL,

    batch_id VARCHAR(100) NOT NULL,
    source_file_name VARCHAR(255) NOT NULL,
    source_row_number BIGINT,
    record_hash CHAR(64),
    load_timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- ============================================================
-- 3. STG_STORES
-- ============================================================

CREATE TABLE IF NOT EXISTS stg_stores (
    staging_id BIGINT AUTO_INCREMENT PRIMARY KEY,

    store_id VARCHAR(12) NOT NULL,
    store_name VARCHAR(150) NOT NULL,
    store_type VARCHAR(30) NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    region VARCHAR(20) NOT NULL,
    postal_code VARCHAR(20) NOT NULL,
    opening_date DATE NOT NULL,
    status VARCHAR(30) NOT NULL,
    floor_area_sqft DECIMAL(12,2),
    manager_name VARCHAR(100),

    batch_id VARCHAR(100) NOT NULL,
    source_file_name VARCHAR(255) NOT NULL,
    source_row_number BIGINT,
    record_hash CHAR(64),
    load_timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- ============================================================
-- 4. STG_SALESPERSONS
-- ============================================================

CREATE TABLE IF NOT EXISTS stg_salespersons (
    staging_id BIGINT AUTO_INCREMENT PRIMARY KEY,

    salesperson_id VARCHAR(12) NOT NULL,
    salesperson_name VARCHAR(150) NOT NULL,
    store_id VARCHAR(12) NOT NULL,
    joining_date DATE NOT NULL,
    role VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,

    batch_id VARCHAR(100) NOT NULL,
    source_file_name VARCHAR(255) NOT NULL,
    source_row_number BIGINT,
    record_hash CHAR(64),
    load_timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- ============================================================
-- 5. STG_PROMOTIONS
-- ============================================================

CREATE TABLE IF NOT EXISTS stg_promotions (
    staging_id BIGINT AUTO_INCREMENT PRIMARY KEY,

    promotion_id VARCHAR(12) NOT NULL,
    promotion_name VARCHAR(150) NOT NULL,
    promotion_type VARCHAR(30) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    discount_pct DECIMAL(5,2) NOT NULL,
    applicable_channel VARCHAR(20) NOT NULL,
    applicable_category VARCHAR(50),
    minimum_order_value DECIMAL(14,2),
    status VARCHAR(20) NOT NULL,

    batch_id VARCHAR(100) NOT NULL,
    source_file_name VARCHAR(255) NOT NULL,
    source_row_number BIGINT,
    record_hash CHAR(64),
    load_timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- ============================================================
-- 6. STG_SALES
-- ============================================================

CREATE TABLE IF NOT EXISTS stg_sales (
    staging_id BIGINT AUTO_INCREMENT PRIMARY KEY,

    sales_line_id VARCHAR(20) NOT NULL,
    order_id VARCHAR(20) NOT NULL,
    order_date DATE NOT NULL,
    order_time TIME NOT NULL,
    customer_id VARCHAR(12),
    product_id VARCHAR(12) NOT NULL,
    store_id VARCHAR(12) NOT NULL,
    salesperson_id VARCHAR(12),
    promotion_id VARCHAR(12),
    sales_channel VARCHAR(20) NOT NULL,
    quantity INT NOT NULL,
    unit_selling_price DECIMAL(14,2) NOT NULL,
    discount_pct DECIMAL(5,2) NOT NULL,
    payment_method VARCHAR(30) NOT NULL,
    order_status VARCHAR(20) NOT NULL,

    batch_id VARCHAR(100) NOT NULL,
    source_file_name VARCHAR(255) NOT NULL,
    source_row_number BIGINT,
    record_hash CHAR(64),
    load_timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- ============================================================
-- 7. STG_RETURNS
-- ============================================================

CREATE TABLE IF NOT EXISTS stg_returns (
    staging_id BIGINT AUTO_INCREMENT PRIMARY KEY,

    return_id VARCHAR(20) NOT NULL,
    sales_line_id VARCHAR(20) NOT NULL,
    return_date DATE NOT NULL,
    quantity_returned INT NOT NULL,
    return_reason VARCHAR(50) NOT NULL,
    return_status VARCHAR(20) NOT NULL,
    refund_method VARCHAR(30),
    refund_amount DECIMAL(14,2),
    processed_store_id VARCHAR(12),

    batch_id VARCHAR(100) NOT NULL,
    source_file_name VARCHAR(255) NOT NULL,
    source_row_number BIGINT,
    record_hash CHAR(64),
    load_timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- ============================================================
-- 8. STG_TARGETS
-- ============================================================

CREATE TABLE IF NOT EXISTS stg_targets (
    staging_id BIGINT AUTO_INCREMENT PRIMARY KEY,

    target_id VARCHAR(20) NOT NULL,
    target_month DATE NOT NULL,
    store_id VARCHAR(12) NOT NULL,
    category VARCHAR(50) NOT NULL,
    revenue_target DECIMAL(14,2) NOT NULL,
    profit_target DECIMAL(14,2) NOT NULL,
    order_target INT NOT NULL,
    return_rate_target_pct DECIMAL(5,2) NOT NULL,

    batch_id VARCHAR(100) NOT NULL,
    source_file_name VARCHAR(255) NOT NULL,
    source_row_number BIGINT,
    record_hash CHAR(64),
    load_timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- ============================================================
-- 9. VERIFICATION
-- ============================================================

SELECT
    table_name
FROM information_schema.tables
WHERE table_schema = 'retail_sales_db'
  AND table_name IN (
      'stg_customers',
      'stg_products',
      'stg_stores',
      'stg_salespersons',
      'stg_promotions',
      'stg_sales',
      'stg_returns',
      'stg_targets'
  )
ORDER BY table_name;


USE retail_sales_db;

SHOW TABLES LIKE 'stg_%';


