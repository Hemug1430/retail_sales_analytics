USE retail_sales_db;

-- ============================================================
-- 05.23 - FIX FACTSALES PAYMENT METHOD CHECK CONSTRAINT
-- ============================================================

-- Remove the incorrect payment-method constraint
ALTER TABLE factsales
DROP CHECK chk_fact_sales_payment;


-- Recreate the constraint using the approved project values
ALTER TABLE factsales
ADD CONSTRAINT chk_fact_sales_payment
CHECK (
    payment_method IN (
        'Cash',
        'Credit Card',
        'Debit Card',
        'Net Banking',
        'UPI',
        'Wallet'
    )
);


-- ============================================================
-- VERIFY THE CONSTRAINT
-- ============================================================

SELECT
    CONSTRAINT_NAME,
    CHECK_CLAUSE
FROM information_schema.CHECK_CONSTRAINTS
WHERE CONSTRAINT_SCHEMA = 'retail_sales_db'
  AND CONSTRAINT_NAME = 'chk_fact_sales_payment';


-- ============================================================
-- VERIFY STAGING PAYMENT METHODS
-- ============================================================

SELECT
    payment_method,
    COUNT(*) AS row_count
FROM stg_sales
GROUP BY payment_method
ORDER BY payment_method;