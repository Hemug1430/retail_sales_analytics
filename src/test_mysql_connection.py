import mysql.connector

try:
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="Root",
        database="retail_sales_db"
    )
    cursor = conn.cursor()
    
    # Query MySQL check clause metadata definition rules
    query = """
        SELECT CHECK_CLAUSE 
        FROM INFORMATION_SCHEMA.CHECK_CONSTRAINTS 
        WHERE CONSTRAINT_NAME = 'chk_fact_targets_category';
    """
    cursor.execute(query)
    result = cursor.fetchone()
    
    print("\n--- ALLOWED CATEGORY CONSTRAINT CLAUSE ---")
    print(result if result else "Constraint definition not found.")
    
    cursor.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
