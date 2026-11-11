import csv
import mysql.connector
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
csv_path = BASE_DIR / "data" / "synthetic" / "salespersons_master.csv"

print("Connecting to database...")
try:
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="Root",
        database="retail_sales_db"
    )
    cursor = conn.cursor()
    print("Database connection: SUCCESS")
    
    print("Clearing old records from core_salespersons...")
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
    cursor.execute("TRUNCATE TABLE core_salespersons;")
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
    conn.commit()
    
    insert_sql = """
        INSERT INTO core_salespersons (
            salesperson_id, salesperson_name, store_id, joining_date, role, status, 
            batch_id, source_file_name, source_row_number, load_timestamp
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    print("Reading CSV and loading rows...")
    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=1):
            
            # Extract numerical part of 'SP00182' -> '182'
            raw_id = row['salesperson_id'].strip()
            numeric_part = ''.join(filter(str.isdigit, raw_id))
            
            # Format to 6-digit zero padding: 'EMP000182' to match core database setup
            clean_emp_id = f"EMP{int(numeric_part):06d}"
            
            current_role = row['role'].strip()
            if current_role == "Sales Executive":
                current_role = "Store Supervisor"
            
            params = (
                clean_emp_id, 
                row['salesperson_name'].strip(), 
                row['store_id'].strip(), 
                row['joining_date'].strip(), 
                current_role, 
                row['status'].strip(),
                "BATCH_001",
                "salespersons_master.csv",
                idx,
                datetime.now()
            )
            cursor.execute(insert_sql, params)
            
    conn.commit()
    print("Successfully re-loaded salesperson records with 'EMP' mapping format!")

except Exception as e:
    print(f"Execution Error: {e}")
finally:
    if 'cursor' in locals(): cursor.close()
    if 'conn' in locals(): conn.close()
