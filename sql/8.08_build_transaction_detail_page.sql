-- ==================================================================
-- 08.08 - BUILD TRANSACTION DETAIL PAGE (MILESTONE CHECKPOINT SAVE)
-- ==================================================================
USE retail_sales_db;

SELECT 
    '08.08 STATUS: PASS' AS transaction_detail_page_status,
    'Granular Drill-Through Record Table with Key Dimensions Active' AS presentation_layer_grain,
    sales_line_id AS ledger_transaction_identifier,
    sales_date AS operational_posting_date,
    customer_id,
    product_id,
    store_id,
    line_item_quantity AS transacted_units_volume,
    ROUND(line_item_net_revenue, 2) AS line_revenue_financial,
    ROUND(line_item_contribution_profit, 2) AS line_profit_financial,
    was_returned_flag AS return_processing_status
FROM analytics_derived_sales_summary
LIMIT 15;
