import csv
import mysql.connector
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
csv_path = BASE_DIR / "data" / "synthetic" / "returns_master.csv"

CORE_TABLE_NAME = "factreturns" 

print("==================================================")
print("05.24 - RUN RETURNS INCREMENTAL INSERT")
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
    print("Database connection: SUCCESS")

    print("Clearing returns staging layer (stg_returns)...")
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
    cursor.execute("TRUNCATE TABLE stg_returns;")
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
    conn.commit()

    insert_staging_sql = """
        INSERT INTO stg_returns (
            return_id, sales_line_id, return_date,
            quantity_returned, refund_amount, return_reason, return_status, 
            processed_store_id, batch_id, source_file_name, source_row_number, 
            record_hash, load_timestamp
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    # Clean text profiles to satisfy database constraint schemas
    valid_reasons = {"Damaged", "Wrong Product", "Quality Issue", "Size/Fit Issue", "Customer Changed Mind", "Late Delivery", "Other"}
    valid_statuses = {"Pending", "Completed", "Refunded", "Processed"}

    print("Reading CSV and mapping parameters into staging table...")
    inserted_count = 0
    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=1):
            clean_store_id = row['store_id'].strip().replace("STORE000", "STORE0")
            row_hash = f"hash_{row['return_id'].strip()}"
            
            reason_input = row['return_reason'].strip()
            clean_reason = reason_input if reason_input in valid_reasons else "Other"
            
            # Map any incoming status text directly to the required valid database status
            status_input = row['status'].strip().title()
            if status_input == "Processed":
                clean_status = "Completed"
            elif status_input in valid_statuses:
                clean_status = status_input
            else:
                clean_status = "Completed"
            
            params = (
                row['return_id'].strip(),
                row['order_id'].strip(),        
                row['return_date'].strip(),
                int(row['quantity']),           
                float(row['refund_amount']),
                clean_reason,
                clean_status,          
                clean_store_id,                 
                "BATCH_001",
                "returns_master.csv",
                idx,
                row_hash,
                datetime.now()
            )
            cursor.execute(insert_staging_sql, params)
            inserted_count += 1
            
    conn.commit()
    print(f"Staging records populated: {inserted_count}")

    print(f"Executing incremental migration into core {CORE_TABLE_NAME} table...")
    merge_sql = f"""
        INSERT INTO {CORE_TABLE_NAME} (
            return_id, sales_line_id, return_date,
            quantity_returned, refund_amount, return_reason, return_status, 
            processed_store_id, batch_id, source_file_name, source_row_number, 
            record_hash, load_timestamp
        )
        SELECT 
            return_id, sales_line_id, return_date,
            quantity_returned, refund_amount, return_reason, return_status, 
            processed_store_id, batch_id, source_file_name, source_row_number, 
            record_hash, NOW()
        FROM stg_returns
        ON DUPLICATE KEY UPDATE
            return_status = VALUES(return_status),
            refund_amount = VALUES(refund_amount);
    """
    cursor.execute(merge_sql)
    conn.commit()
    
    print("Database integration completed successfully!")
    print("==================================================")
    print("05.24 STATUS: PASS")
    print("==================================================")

except Exception as e:
    print(f"Execution Error: {e}")
    if 'conn' in locals():
        conn.rollback()
        print("Transaction was rolled back safely.")
    print("05.24 STATUS: FAILED")
finally:
    if 'cursor' in locals(): cursor.close()
    if 'conn' in locals(): conn.close()
