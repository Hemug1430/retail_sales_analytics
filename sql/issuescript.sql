USE retail_sales_db;

ALTER TABLE core_customers
DROP CHECK chk_core_customers_channel;

ALTER TABLE core_customers
ADD CONSTRAINT chk_core_customers_channel
CHECK (
    preferred_channel IS NULL
    OR preferred_channel IN ('Store', 'Online')
);


SHOW CREATE TABLE core_customers;