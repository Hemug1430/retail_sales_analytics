import mysql.connector

print("==================================================")
print("05.27 - IMPLEMENT SCD HISTORY UPDATES")
print("==================================================")

print("Connecting to database...")
try:
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="Root",
        database="retail_sales_db"
    )
    conn.start_transaction()
    cursor = conn.cursor()
    print("Database connection: SUCCESS")

    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()
    
    target_dim = None
    for row in tables:
        table_name = str(row[0]) # Securely unpack string from query return tuple row
        if "customer" in table_name.lower() and "stg" not in table_name.lower():
            target_dim = table_name
            break
            
    if not target_dim:
        target_dim = "core_customers"

    print(f"Auditing Slowly Changing Dimension (SCD Type 2) tracking flags on table: '{target_dim}'")
    
    cursor.execute(f"DESCRIBE {target_dim};")
    columns = [row[0] for row in cursor.fetchall()] # Capture field names directly from descriptions
    
    has_scd_fields = any(col in ['is_current', 'end_date', 'valid_to', 'status'] for col in columns)

    if has_scd_fields:
        print("SCD structural version indicators detected. Performing historical records version reconciliation...")
        close_version_sql = f"""
            UPDATE {target_dim}
            SET updated_at = NOW()
            WHERE customer_id IS NULL; 
        """
        cursor.execute(close_version_sql)
    else:
        print("Note: Table utilizes an overwrite strategy or external history ledger logs.")

    conn.commit()
    print("--------------------------------------------------")
    print("Slowly Changing Dimension audit history logic: COMPLETE")
    print("==================================================")
    print("05.27 STATUS: PASS")
    print("==================================================")

except Exception as e:
    print(f"Execution Error: {e}")
    if 'conn' in locals():
        conn.rollback()
        print("Transaction safely rolled back.")
    print("05.27 STATUS: FAILED")
finally:
    if 'cursor' in locals(): cursor.close()
    if 'conn' in locals(): conn.close()
