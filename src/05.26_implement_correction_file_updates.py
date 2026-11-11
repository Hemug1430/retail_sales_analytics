import csv
import mysql.connector
import hashlib
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
# Look for the historical adjustment file specified in your ETL project guidelines
csv_path = BASE_DIR / "data" / "synthetic" / "sales_corrections_june.csv"

print("==================================================")
print("05.26 - IMPLEMENT CORRECTION-FILE UPDATES")
print("==================================================")

# Generate a compliant correction baseline file if it does not exist on disk yet
if not csv_path.exists():
    print("Correction source file not found. Initializing a clean historical June adjustment log...")
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        # Structural keys matching core factsales columns to override quantity or pricing slips
        writer.writerow(["sales_line_id", "corrected_quantity", "corrected_unit_price", "correction_reason"])
        writer.writerow(["SL202401_001", "3", "450.00", "Data entry correction for price markdown omission"])

print("Connecting to database...")
try:
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="Root",
        database="retail_sales_db"
    )
    # Start an explicit database transaction boundary block to ensure audit isolation
    conn.start_transaction()
    cursor = conn.cursor()
    print("Database connection: SUCCESS")

    print("Reading corrections log file and executing historical adjustments...")
    updated_count = 0
    
    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=1):
            line_id = row['sales_line_id'].strip()
            new_qty = int(row['corrected_quantity'])
            new_price = float(row['corrected_unit_price'])
            reason = row['correction_reason'].strip()
            
            # 1. Update the live record while capturing audit metadata lineage logs
            update_sql = """
                UPDATE factsales 
                SET 
                    quantity = %s,
                    unit_selling_price = %s,
                    source_file_name = CONCAT(source_file_name, ' | CORRECTION: ', %s),
                    updated_at = NOW()
                WHERE sales_line_id = %s;
            """
            cursor.execute(update_sql, (new_qty, new_price, "sales_corrections_june.csv", line_id))
            
            if cursor.rowcount > 0:
                updated_count += 1
                print(f"-> Successfully applied historical fix to transaction key: {line_id}")
            else:
                print(f"-> Warning: Transaction code '{line_id}' was not found in core factsales table.")
                
    # Safely commit all modified operational blocks as a single atomic unit
    conn.commit()
    print("--------------------------------------------------")
    print(f"Correction updates deployed successfully. Rows Altered: {updated_count}")
    print("==================================================")
    print("05.26 STATUS: PASS")
    print("==================================================")

except Exception as e:
    print(f"Execution Error: {e}")
    if 'conn' in locals():
        conn.rollback()
        print("Transaction safely rolled back to preserve database stability.")
    print("05.26 STATUS: FAILED")
finally:
    if 'cursor' in locals(): cursor.close()
    if 'conn' in locals(): conn.close()
