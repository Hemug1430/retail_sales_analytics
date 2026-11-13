
"""
05.29 - Implement Database Error Recovery

Tests database error handling and transaction rollback
using centralized database configuration.
"""

import mysql.connector
from config import DB_CONFIG


print("==================================================")
print("05.29 - IMPLEMENT DATABASE ERROR RECOVERY")
print("==================================================")

pipeline_run_status = "READY_TO_RUN"

conn = None
cursor = None

try:
    print("Connecting to database...")

    conn = mysql.connector.connect(**DB_CONFIG)
    conn.autocommit = False

    conn.start_transaction()
    cursor = conn.cursor()

    print("Database connection: SUCCESS")
    print("Transaction started successfully.")

    # Intentionally execute invalid SQL to trigger a predictable
    # MySQL database error without modifying business data.
    print("Simulating a database error to test recovery...")

    faulty_query = """
        SELECT * FROM intentionally_invalid_recovery_test_table;
    """

    cursor.execute(faulty_query)

    # This should not execute because the query above should fail.
    conn.commit()

    pipeline_run_status = "UNEXPECTED_SUCCESS"
    print("ERROR: The expected database error was not triggered.")
    print("05.29 STATUS: FAILED")

except mysql.connector.Error as db_err:

    print(f"\n[EXPECTED DATABASE ERROR CAPTURED]: {db_err}")

    if conn is not None and conn.is_connected():
        try:
            conn.rollback()

            pipeline_run_status = "ROLLBACK_SUCCESSFUL"

            print("-> SUCCESSFUL DATABASE RECOVERY: Rollback completed.")
            print("-> No business data was modified by this test.")
            print("-> Database transaction returned to a safe state.")

            print("--------------------------------------------------")
            print("Database error interception and rollback verified!")
            print("==================================================")
            print("05.29 STATUS: PASS")
            print("==================================================")

        except mysql.connector.Error as rollback_error:
            pipeline_run_status = "ROLLBACK_FAILED"
            print(f"Rollback failed: {rollback_error}")
            print("05.29 STATUS: FAILED")
    else:
        pipeline_run_status = "CONNECTION_LOST"
        print("Database connection unavailable for rollback.")
        print("05.29 STATUS: FAILED")

except Exception as general_err:

    pipeline_run_status = "GENERAL_FAILURE"

    print(f"General Pipeline Error: {general_err}")

    if conn is not None and conn.is_connected():
        try:
            conn.rollback()
            print("Rollback completed after general error.")
        except mysql.connector.Error as rollback_error:
            print(f"Rollback failed: {rollback_error}")

    print("05.29 STATUS: FAILED")

finally:

    if cursor is not None:
        cursor.close()

    if conn is not None and conn.is_connected():
        conn.close()
        print("Database connection closed.")
