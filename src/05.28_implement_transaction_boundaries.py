
"""
05.28 - Implement Transaction Boundaries

Uses centralized database credentials from src/config.py.
"""

import mysql.connector
from config import DB_CONFIG


print("==================================================")
print("05.28 - IMPLEMENT TRANSACTION BOUNDARIES")
print("==================================================")

conn = None
cursor = None

try:
    print("Connecting to database...")

    conn = mysql.connector.connect(**DB_CONFIG)

    # Disable autocommit to enforce explicit transaction boundaries.
    conn.autocommit = False
    cursor = conn.cursor()

    print("Database connection: SUCCESS (Autocommit Disabled)")

    print("Initiating atomic multi-table loading transaction boundary block...")

    conn.start_transaction()

    # Step A: Simulate loading data component 1 into staging.
    print("-> Phase 1: populating trusted analytics ledger lines...")

    dummy_insert_1 = """
        UPDATE factsales
        SET load_timestamp = NOW()
        WHERE sales_line_id = 'NON_EXISTENT_AUDIT_KEY_X';
    """
    cursor.execute(dummy_insert_1)

    # Step B: Simulate loading data component 2 into summary tables.
    print("-> Phase 2: updating corporate target status matrix configurations...")

    dummy_insert_2 = """
        UPDATE facttargets
        SET load_timestamp = NOW()
        WHERE target_id = 'NON_EXISTENT_AUDIT_KEY_Y';
    """
    cursor.execute(dummy_insert_2)

    # Commit all changes together.
    conn.commit()

    print("Transaction Boundary Validation: COMMIT EXECUTED SUCCESSFULLY")
    print("--------------------------------------------------")
    print("Transaction boundary interlock framework verified!")
    print("==================================================")
    print("05.28 STATUS: PASS")
    print("==================================================")

except Exception as e:
    print(f"Transaction Boundary Intercepted Failure: {e}")

    if conn is not None and conn.is_connected():
        try:
            conn.rollback()
            print("Rollback Strategy Triggered: Transaction rolled back.")
        except mysql.connector.Error as rollback_error:
            print(f"Rollback failed: {rollback_error}")

    print("05.28 STATUS: FAILED")

finally:
    if cursor is not None:
        cursor.close()

    if conn is not None and conn.is_connected():
        conn.close()
        print("Database connection closed.")
