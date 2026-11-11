import mysql.connector

print("==================================================")
print("05.30 - CREATE CORE DATA VIEWS")
print("==================================================")

print("Connecting to database...")
try:
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="Root",
        database="retail_sales_db"
    )
    cursor = conn.cursor()
    print("Database connection: SUCCESS\n")

    print("Deploying core data warehouse virtual reporting views...")
    print("--------------------------------------------------")

    # 1. View 1: Trusted Corporate Executive Sales & Financial Performance View
    print("-> Deploying View: 'vw_executive_sales_performance'...")
    cursor.execute("DROP VIEW IF EXISTS vw_executive_sales_performance;")
    view_sales_sql = """
        CREATE VIEW vw_executive_sales_performance AS
        SELECT 
            fs.sales_line_id,
            fs.order_date,
            fs.store_id,
            fs.quantity,
            fs.unit_selling_price,
            COALESCE(fs.discount_pct, 0) as discount_applied,
            (fs.quantity * fs.unit_selling_price * (1 - COALESCE(fs.discount_pct, 0))) as net_sales_revenue,
            fr.return_id,
            COALESCE(fr.refund_amount, 0) as associated_refund_amount,
            fr.return_reason,
            fr.return_status
        FROM factsales fs
        LEFT JOIN factreturns fr ON fs.sales_line_id = fr.sales_line_id;
    """
    cursor.execute(view_sales_sql)

    # 2. View 2: High-Level Targets Realization vs Actuals View
    print("-> Deploying View: 'vw_monthly_targets_realization'...")
    cursor.execute("DROP VIEW IF EXISTS vw_monthly_targets_realization;")
    view_targets_sql = """
        CREATE VIEW vw_monthly_targets_realization AS
        SELECT 
            ft.target_id,
            ft.target_month,
            ft.store_id,
            ft.category,
            ft.revenue_target,
            ft.order_target,
            COALESCE(SUM(fs.quantity * fs.unit_selling_price * (1 - COALESCE(fs.discount_pct, 0))), 0) as actual_revenue_achieved,
            COUNT(DISTINCT fs.sales_line_id) as actual_orders_processed
        FROM facttargets ft
        LEFT JOIN factsales fs ON ft.store_id = fs.store_id AND DATE_FORMAT(fs.order_date, '%Y-%m-01') = ft.target_month
        GROUP BY ft.target_id, ft.target_month, ft.store_id, ft.category, ft.revenue_target, ft.order_target;
    """
    cursor.execute(view_targets_sql)

    conn.commit()
    print("--------------------------------------------------")
    print("Core reusable relational reporting views compiled successfully!")
    print("==================================================")
    print("05.30 STATUS: PASS")
    print("==================================================")

except Exception as e:
    print(f"Execution Error: {e}")
    if 'conn' in locals():
        conn.rollback()
        print("Transaction safely rolled back.")
    print("05.30 STATUS: FAILED")
finally:
    if 'cursor' in locals(): cursor.close()
    if 'conn' in locals(): conn.close()
