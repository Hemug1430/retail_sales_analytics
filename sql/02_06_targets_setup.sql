-- Tracker 02.06 - Target Data Setup

CREATE TABLE IF NOT EXISTS targets (
    target_id VARCHAR(18) PRIMARY KEY,
    target_month DATE NOT NULL,
    store_id VARCHAR(10) NOT NULL,
    category VARCHAR(40) NOT NULL,
    revenue_target DECIMAL(14,2) NOT NULL,
    profit_target DECIMAL(14,2) NOT NULL,
    order_target INT NOT NULL,
    return_rate_target_pct DECIMAL(5,2) NOT NULL
);
