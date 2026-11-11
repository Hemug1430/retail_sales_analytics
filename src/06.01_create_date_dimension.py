import mysql.connector
from datetime import datetime, timedelta

print("==================================================")
print("06.01 - CREATE DATE DIMENSION DATA")
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

    print("Dropping old table cache...")
    cursor.execute("DROP TABLE IF EXISTS dim_date;")
    conn.commit()

    print("Initializing clean structural dim_date storage layout...")
    # Fixed query string with clear column definitions and correct comma mapping syntax
    cursor.execute("""
        CREATE TABLE dim_date (
            date_key DATE PRIMARY KEY,
            day_number INT,
            day_name VARCHAR(15),
            week_number INT,
            month_number INT,
            month_name VARCHAR(15),
            quarter_number INT,
            year_number INT,
            year_month VARCHAR(10),
            is_weekend INT
        );
    """)
    conn.commit()

    start_date = datetime(2024, 1, 1)
    end_date = datetime(2026, 12, 31)
    current_date = start_date

    print("Generating comprehensive calendar matrix entries...")
    insert_sql = """
        INSERT INTO dim_date (
            date_key, day_number, day_name, week_number, 
            month_number, month_name, quarter_number, year_number, 
            year_month, is_weekend
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
    """

    inserted_count = 0
    while current_date <= end_date:
        date_str = current_date.strftime("%Y-%m-%d")
        day_num = current_date.day
        day_nm = current_date.strftime("%A")
        
        # Safely extract the integer index [1] from the isocalendar tuple structure
        week_num = int(current_date.isocalendar()[1])
        month_num = current_date.month
        month_nm = current_date.strftime("%B")
        quarter_num = (month_num - 1) // 3 + 1
        year_num = current_date.year
        year_month_str = current_date.strftime("%Y-%m")
        is_wknd = 1 if current_date.weekday() in (5, 6) else 0

        params = (
            date_str, day_num, day_nm, week_num,
            month_num, month_nm, quarter_num, year_num,
            year_month_str, is_wknd
        )
        
        cursor.execute(insert_sql, params)
        inserted_count += 1
        current_date += timedelta(days=1)

    conn.commit()
    print(f"Calendar generation successfully populated: {inserted_count} consecutive days inserted.")
    print("--------------------------------------------------")
    print("==================================================")
    print("06.01 STATUS: PASS")
    print("==================================================")

except Exception as e:
    print(f"Execution Error: {e}")
    if 'conn' in locals():
        conn.rollback()
    print("06.01 STATUS: FAILED")
finally:
    if 'cursor' in locals(): cursor.close()
    if 'conn' in locals(): conn.close()
