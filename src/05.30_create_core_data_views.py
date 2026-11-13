
"""
05.30 - Create Core Data Views

Creates reusable reporting views using centralized
database configuration from src/config.py.

Views:
1. vw_executive_sales_performance
2. vw_monthly_targets_realization
"""

import mysql.connector
from config import DB_CONFIG


print("==================================================")
print("05.30 - CREATE CORE DATA VIEWS")
print("==================================================")

conn = None
cursor = None

try:
    print("Connecting to database...")

    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()

    print("Database connection: SUCCESS\n")
    print("Deploying core data warehouse reporting views...")
    print("--------------------------------------------------")

    # --------------------------------------------------
    # 1. Executive Sales and Financial Performance View
    # --------------------------------------------------

    print("-> Deploying View: vw_executive_sales_performance...")

    view_sales_sql = """
        CREATE OR REPLACE VIEW vw_executive_sales_performance AS

        SELECT
            fs.sales_line_id,
            fs.order_id,
            fs.order_date,
            fs.store_id,
            fs.product_id,
            fs.quantity,
            fs.unit_selling_price,

            COALESCE(fs.discount_pct, 0) AS discount_applied,

            (
                fs.quantity
                * fs.unit_selling_price
                * (
                    1 - COALESCE(fs.discount_pct, 0) / 100.0
                )
            ) AS net_sales_revenue,

            COALESCE(fr.associated_return_count, 0)
                AS associated_return_count,

            COALESCE(fr.associated_return_quantity, 0)
                AS associated_return_quantity,

            COALESCE(fr.associated_refund_amount, 0)
                AS associated_refund_amount,

            fr.return_reasons,
            fr.return_statuses

        FROM factsales fs

        LEFT JOIN (
            SELECT
                sales_line_id,
                COUNT(return_id) AS associated_return_count,
                SUM(quantity_returned) AS associated_return_quantity,
                SUM(COALESCE(refund_amount, 0))
                    AS associated_refund_amount,

                GROUP_CONCAT(
                    DISTINCT return_reason
                    ORDER BY return_reason
                    SEPARATOR ', '
                ) AS return_reasons,

                GROUP_CONCAT(
                    DISTINCT return_status
                    ORDER BY return_status
                    SEPARATOR ', '
                ) AS return_statuses

            FROM factreturns
            GROUP BY sales_line_id

        ) fr
            ON fs.sales_line_id = fr.sales_line_id;
    """

    cursor.execute(view_sales_sql)

    print("   SUCCESS: Executive sales view created.")

    # --------------------------------------------------
    # 2. Monthly Targets Realization vs Actuals View
    # --------------------------------------------------

    print("-> Deploying View: vw_monthly_targets_realization...")

    view_targets_sql = """
        CREATE OR REPLACE VIEW vw_monthly_targets_realization AS

        SELECT
            ft.target_id,
            ft.target_month,
            ft.store_id,
            ft.category,
            ft.revenue_target,
            ft.profit_target,
            ft.order_target,
            ft.return_rate_target_pct,

            COALESCE(
                SUM(
                    CASE
                        WHEN cp.category = ft.category
                        THEN
                            fs.quantity
                            * fs.unit_selling_price
                            * (
                                1 - COALESCE(fs.discount_pct, 0) / 100.0
                            )
                        ELSE 0
                    END
                ),
                0
            ) AS actual_revenue_achieved,

            COUNT(
                DISTINCT
                CASE
                    WHEN cp.category = ft.category
                    THEN fs.order_id
                    ELSE NULL
                END
            ) AS actual_orders_processed

        FROM facttargets ft

        LEFT JOIN factsales fs
            ON ft.store_id = fs.store_id

            AND fs.order_date >=
                DATE_SUB(
                    ft.target_month,
                    INTERVAL DAYOFMONTH(ft.target_month) - 1 DAY
                )

            AND fs.order_date <
                DATE_ADD(
                    DATE_SUB(
                        ft.target_month,
                        INTERVAL DAYOFMONTH(ft.target_month) - 1 DAY
                    ),
                    INTERVAL 1 MONTH
                )

        LEFT JOIN core_products cp
            ON fs.product_id = cp.product_id
            AND cp.is_current = 1

        GROUP BY
            ft.target_id,
            ft.target_month,
            ft.store_id,
            ft.category,
            ft.revenue_target,
            ft.profit_target,
            ft.order_target,
            ft.return_rate_target_pct;
    """

    cursor.execute(view_targets_sql)

    print("   SUCCESS: Monthly targets realization view created.")

    # --------------------------------------------------
    # 3. Verify View Deployment
    # --------------------------------------------------

    print("--------------------------------------------------")
    print("Verifying deployed reporting views...")

    cursor.execute("""
        SHOW FULL TABLES
        WHERE Table_type = 'VIEW'
    """)

    deployed_views = {
        row[0] for row in cursor.fetchall()
    }

    required_views = {
        "vw_executive_sales_performance",
        "vw_monthly_targets_realization"
    }

    missing_views = required_views - deployed_views

    if missing_views:
        raise RuntimeError(
            "View verification failed. Missing views: "
            + ", ".join(sorted(missing_views))
        )

    print("   SUCCESS: Both reporting views verified.")

    # --------------------------------------------------
    # 4. Verify Monthly Target View Returns Data
    # --------------------------------------------------

    print("--------------------------------------------------")
    print("Checking monthly target view output...")

    cursor.execute("""
        SELECT
            COUNT(*) AS total_target_rows,
            COUNT(DISTINCT category) AS total_categories
        FROM vw_monthly_targets_realization
    """)

    result = cursor.fetchone()

    print(f"   Target rows : {result[0]:,}")
    print(f"   Categories  : {result[1]:,}")

    print("==================================================")
    print("05.30 STATUS: PASS")
    print("==================================================")

except mysql.connector.Error as db_error:

    print(f"Database Error: {db_error}")
    print("05.30 STATUS: FAILED")
    raise

except Exception as error:

    print(f"Unexpected Error: {error}")
    print("05.30 STATUS: FAILED")
    raise

finally:

    if cursor is not None:
        cursor.close()

    if conn is not None and conn.is_connected():
        conn.close()
        print("Database connection closed.")
