-- ==================================================================
-- 06.17 - CREATE PROMOTION EFFECTIVENESS OUTPUTS (NATIVE SQL)
-- ==================================================================
USE retail_sales_db;

-- Drop previous view if it exists to refresh database structures
DROP VIEW IF EXISTS vw_promotion_effectiveness_analytics;

-- Compile a reusable reporting layer for Power BI dashboard connectivity
CREATE VIEW vw_promotion_effectiveness_analytics AS
SELECT 
    CASE 
        WHEN fs.promotion_id IS NULL OR fs.promotion_id = '' OR fs.promotion_id = 'PROMO000' THEN 'Non-Promoted'
        ELSE 'Promoted Campaign'
    END AS promotional_segment,
    
    -- Campaign metadata attributes
    COALESCE(fs.promotion_id, 'No Promo') AS applied_promotion_id,
    
    -- Volume and transactional reach checks
    COUNT(DISTINCT fs.sales_line_id) AS total_orders_processed,
    SUM(fs.quantity) AS total_units_sold,
    
    -- Financial performance indicators
    SUM(fs.quantity * fs.unit_selling_price) AS gross_sales_revenue,
    SUM(fs.quantity * fs.unit_selling_price * COALESCE(fs.discount_pct, 0)) AS total_markdown_discounts,
    SUM(fs.quantity * fs.unit_selling_price * (1 - COALESCE(fs.discount_pct, 0))) AS net_sales_revenue,
    
    -- Margin impact indicators
    SUM(fs.quantity * fs.unit_selling_price * (1 - COALESCE(fs.discount_pct, 0))) - 
    SUM(fs.quantity * COALESCE(fs.unit_selling_price * 0.60, 15.00)) AS estimated_contribution_margin

FROM factsales fs
GROUP BY 
    CASE 
        WHEN fs.promotion_id IS NULL OR fs.promotion_id = '' OR fs.promotion_id = 'PROMO000' THEN 'Non-Promoted'
        ELSE 'Promoted Campaign'
    END,
    COALESCE(fs.promotion_id, 'No Promo');

-- Visual verification summary matrix run
SELECT 
    promotional_segment,
    applied_promotion_id,
    total_orders_processed,
    total_units_sold,
    ROUND(net_sales_revenue, 2) AS net_revenue,
    ROUND(estimated_contribution_margin, 2) AS profit_margin
FROM vw_promotion_effectiveness_analytics
ORDER BY net_revenue DESC;
