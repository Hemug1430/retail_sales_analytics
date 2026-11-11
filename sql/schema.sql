USE retail_sales_db;

-- =========================
-- Customer Master Table
-- =========================

CREATE TABLE customers_master (
    customer_id VARCHAR(12) PRIMARY KEY,
    customer_name VARCHAR(100),
    gender VARCHAR(15),
    date_of_birth DATE,
    email VARCHAR(120),
    phone VARCHAR(15),
    city VARCHAR(60),
    state VARCHAR(60),
    region VARCHAR(20),
    postal_code VARCHAR(10),
    registration_date DATE,
    customer_segment VARCHAR(20),
    preferred_channel VARCHAR(20),
    status VARCHAR(15)
);

-- =========================
-- Products Master Table
-- =========================

CREATE TABLE products_master (
    product_id VARCHAR(12) PRIMARY KEY,
    product_name VARCHAR(120),
    category VARCHAR(40),
    subcategory VARCHAR(60),
    brand VARCHAR(60),
    unit_cost DECIMAL(12,2),
    list_price DECIMAL(12,2),
    tax_rate_pct DECIMAL(5,2),
    launch_date DATE,
    status VARCHAR(20)
);


-- =========================
-- Store Master Table
-- =========================
CREATE TABLE stores_master (
    store_id VARCHAR(10) PRIMARY KEY,
    store_name VARCHAR(100),
    store_type VARCHAR(25),
    city VARCHAR(60),
    state VARCHAR(60),
    region VARCHAR(20),
    postal_code VARCHAR(10),
    opening_date DATE,
    floor_area_sqft INT,
    manager_name VARCHAR(100),
    status VARCHAR(20)
);


-- =========================
-- Salespersons Master Table
-- =========================
CREATE TABLE salespersons_master (
    salesperson_id VARCHAR(12) PRIMARY KEY,
    salesperson_name VARCHAR(100),
    store_id VARCHAR(10),
    joining_date DATE,
    role VARCHAR(40),
    status VARCHAR(20),

    FOREIGN KEY (store_id)
        REFERENCES stores_master(store_id)
);


-- =========================
-- Promotions Master Table
-- =========================
CREATE TABLE promotions_master (
    promotion_id VARCHAR(12) PRIMARY KEY,
    promotion_name VARCHAR(100),
    promotion_type VARCHAR(30),
    start_date DATE,
    end_date DATE,
    discount_pct DECIMAL(5,2),
    applicable_category VARCHAR(40),
    applicable_channel VARCHAR(20),
    minimum_order_value DECIMAL(12,2),
    status VARCHAR(20)
);


-- =========================
-- Monthly Sales Transaction Table
-- =========================
CREATE TABLE sales_YYYY_MM (
    sales_line_id VARCHAR(18) PRIMARY KEY,
    order_id VARCHAR(16),
    order_date DATE,
    order_time TIME,
    customer_id VARCHAR(12),
    product_id VARCHAR(12),
    store_id VARCHAR(10),
    salesperson_id VARCHAR(12),
    promotion_id VARCHAR(12),
    sales_channel VARCHAR(20),
    quantity INT,
    unit_selling_price DECIMAL(12,2),
    discount_pct DECIMAL(5,2),
    payment_method VARCHAR(25),
    order_status VARCHAR(20),

    FOREIGN KEY (customer_id)
        REFERENCES customers_master(customer_id),

    FOREIGN KEY (product_id)
        REFERENCES products_master(product_id),

    FOREIGN KEY (store_id)
        REFERENCES stores_master(store_id),

    FOREIGN KEY (salesperson_id)
        REFERENCES salespersons_master(salesperson_id),

    FOREIGN KEY (promotion_id)
        REFERENCES promotions_master(promotion_id)
);

-- =========================
-- Monthly Returns Transaction Table
-- =========================
CREATE TABLE returns_YYYY_MM (
    return_id VARCHAR(18) PRIMARY KEY,
    sales_line_id VARCHAR(18),
    return_date DATE,
    return_reason VARCHAR(40),
    return_quantity INT,
    refund_amount DECIMAL(12,2),
    return_status VARCHAR(20),

    FOREIGN KEY (sales_line_id)
        REFERENCES sales_YYYY_MM(sales_line_id)
);

-- =========================
-- Monthly Sales Targets Table
-- =========================
CREATE TABLE targets_YYYY_MM (
    target_id VARCHAR(16) PRIMARY KEY,
    target_month DATE,
    store_id VARCHAR(10),
    salesperson_id VARCHAR(12),
    sales_target_amount DECIMAL(14,2),
    sales_target_orders INT,
    sales_target_customers INT,

    FOREIGN KEY (store_id)
        REFERENCES stores_master(store_id),

    FOREIGN KEY (salesperson_id)
        REFERENCES salespersons_master(salesperson_id)
);