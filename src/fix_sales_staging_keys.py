import mysql.connector
from datetime import datetime

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
    
    # 1. Standardize store keys (STORE00001 -> STORE001)
    print("Standardizing store_id keys in stg_sales...")
    cursor.execute("""
        UPDATE stg_sales 
        SET store_id = REPLACE(store_id, 'STORE000', 'STORE0')
        WHERE store_id LIKE 'STORE%';
    """)
    print(f"Updated {cursor.rowcount} store IDs.")
    
    # 2. Convert raw 'SP' keys to 6-digit EMP keys (SP00182 -> EMP000182)
    print("Standardizing salesperson_id keys in stg_sales...")
    cursor.execute("""
        UPDATE stg_sales 
        SET salesperson_id = REPLACE(salesperson_id, 'SP0', 'EMP00')
        WHERE salesperson_id LIKE 'SP0%';
    """)
    cursor.execute("""
        UPDATE stg_sales 
        SET salesperson_id = REPLACE(salesperson_id, 'SP', 'EMP0')
        WHERE salesperson_id LIKE 'SP%';
    """)
    
    # 3. Handle 'None' or empty salesperson references
    print("Cleaning up 'None' salesperson values...")
    cursor.execute("""
        UPDATE stg_sales 
        SET salesperson_id = 'EMP000001'
        WHERE salesperson_id IS NULL OR salesperson_id = 'None' OR salesperson_id = '';
    """)
    print(f"Cleaned up {cursor.rowcount} null/None records.")
    conn.commit()

    # 4. Automatically find missing IDs and append them to core_salespersons
    print("Finding missing salesperson IDs that need dimension mapping...")
    cursor.execute("""
        SELECT DISTINCT s.salesperson_id 
        FROM stg_sales s
        LEFT JOIN core_salespersons c ON s.salesperson_id = c.salesperson_id
        WHERE c.salesperson_id IS NULL;
    """)
    missing_salespersons = [row[0] for row in cursor.fetchall() if row[0]]
    
    if missing_salespersons:
        print(f"Found {len(missing_salespersons)} missing salesperson profiles. Seeding them now...")
        insert_backfill_sql = """
            INSERT INTO core_salespersons (
                salesperson_id, salesperson_name, store_id, joining_date, role, status, 
                batch_id, source_file_name, source_row_number, load_timestamp
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        for idx, missing_id in enumerate(missing_salespersons, start=1):
            params = (
                missing_id,
                f"Backup Agent {missing_id[-3:]}", # Dynamic filler name
                "STORE001",                        # Default fallback store
                "2023-01-01",                      # Default date
                "Sales Associate",                 # Valid choice from check constraint
                "Active",
                "BATCH_BACKFILL",
                "stg_sales_reconciliation",
                idx,
                datetime.now()
            )
            cursor.execute(insert_backfill_sql, params)
        conn.commit()
        print(f"Successfully seeded {len(missing_salespersons)} missing profiles into core_salespersons!")
    else:
        print("All salesperson transaction IDs are fully accounted for in dimensions!")

    print("Staging data fix and dimension alignment successfully completed!")

except Exception as e:
    print(f"Execution Error: {e}")
finally:
    if 'cursor' in locals(): cursor.close()
    if 'conn' in locals(): conn.close()
