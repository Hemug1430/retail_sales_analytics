-- ==================================================================
-- 06.19 - CREATE RANKING OUTPUTS (FIXED JOIN)
-- ==================================================================
USE retail_sales_db;

DROP VIEW IF EXISTS vw_warehouse_ranking_analytics;

CREATE VIEW vw_warehouse_ranking_analytics AS
SELECT 
    fs.store_id,
    fs.product_id,
    p.category AS category,
    fs.customer_id,
    SUM(fs.quantity * fs.unit_selling_price * (1 - COALESCE(fs.discount_pct, 0))) AS net_revenue,
    SUM(fs.quantity) AS total_units_sold,
    
    DENSE_RANK() OVER (
        PARTITION BY p.category 
        ORDER BY SUM(fs.quantity * fs.unit_selling_price * (1 - COALESCE(fs.discount_pct, 0))) DESC
    ) AS product_rank_in_category,
    
    DENSE_RANK() OVER (
        ORDER BY SUM(fs.quantity * fs.unit_selling_price * (1 - COALESCE(fs.discount_pct, 0))) DESC
    ) AS global_store_rank,

    DENSE_RANK() OVER (
        ORDER BY SUM(fs.quantity * fs.unit_selling_price * (1 - COALESCE(fs.discount_pct, 0))) DESC
    ) AS customer_spending_rank

FROM factsales fs
INNER JOIN core_products p ON fs.product_id = p.product_id
GROUP BY fs.store_id, fs.product_id, p.category, fs.customer_id;
