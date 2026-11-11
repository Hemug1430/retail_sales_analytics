import sqlite3
import unittest
import pandas as pd

def connect_with_retry(connect_fn, max_retries=3):
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            conn = connect_fn()
            return conn, attempt, None
        except Exception as exc:
            last_error = str(exc)
    return None, max_retries, last_error

def load_dataframe_in_chunks(conn, table_name, df, chunk_size=2):
    cursor = conn.cursor()
    total_inserted = 0
    chunks_processed = 0

    try:
        conn.execute("BEGIN")
        for start in range(0, len(df), chunk_size):
            chunk = df.iloc[start : start + chunk_size]
            records = list(chunk.itertuples(index=False, name=None))
            cursor.executemany(
                f"INSERT INTO {table_name} (transaction_id, store_id, amount) VALUES (?, ?, ?)",
                records
            )
            total_inserted += len(records)
            chunks_processed += 1
        conn.commit()
        return True, total_inserted, chunks_processed, None
    except Exception as exc:
        conn.rollback()
        return False, 0, chunks_processed, str(exc)


class TestDatabaseConnectionAndLoad(unittest.TestCase):

    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.execute("""
            CREATE TABLE fact_sales_test (
                transaction_id TEXT PRIMARY KEY,
                store_id TEXT NOT NULL,
                amount REAL NOT NULL CHECK (amount >= 0)
            )
        """)
        self.conn.commit()

    def tearDown(self):
        self.conn.close()

    def test_connection_failure_and_error_capture(self):
        def failing_connector():
            raise ConnectionError("Simulated DB host unreachable (2003)")

        conn, attempts, err = connect_with_retry(failing_connector, max_retries=3)
        self.assertIsNone(conn)
        self.assertEqual(attempts, 3)
        self.assertIn("Simulated DB host unreachable", err)

    def test_connection_retry_recovers_on_second_attempt(self):
        state = {"calls": 0}

        def flaky_connector():
            state["calls"] += 1
            if state["calls"] < 2:
                raise TimeoutError("Transient lock timeout")
            return sqlite3.connect(":memory:")

        conn, attempts, err = connect_with_retry(flaky_connector, max_retries=3)
        self.assertIsNotNone(conn)
        self.assertEqual(attempts, 2)
        self.assertIsNone(err)
        conn.close()

    def test_single_insert_and_chunk_load_commit(self):
        df = pd.DataFrame({
            "transaction_id": list(("TXN101", "TXN102", "TXN103", "TXN104", "TXN105")),
            "store_id": list(("STR01", "STR01", "STR02", "STR02", "STR03")),
            "amount": list((150.0, 299.5, 450.0, 89.0, 1200.0))
        })

        success, inserted, chunks, err = load_dataframe_in_chunks(self.conn, "fact_sales_test", df, chunk_size=2)
        self.assertTrue(success, f"Expected load success, got error: {err}")
        self.assertEqual(inserted, 5)
        self.assertEqual(chunks, 3)

        (row_count,) = self.conn.execute("SELECT COUNT(*) FROM fact_sales_test").fetchone()
        self.assertEqual(row_count, 5)

    def test_transaction_rollback_on_chunk_failure(self):
        # Chunk 1 succeeds (TXN201, TXN202); Chunk 2 fails due to duplicate PK (TXN201) -> full rollback expected
        bad_df = pd.DataFrame({
            "transaction_id": list(("TXN201", "TXN202", "TXN201")),
            "store_id": list(("STR01", "STR02", "STR01")),
            "amount": list((100.0, 200.0, 100.0))
        })

        success, inserted, chunks, err = load_dataframe_in_chunks(self.conn, "fact_sales_test", bad_df, chunk_size=2)
        self.assertFalse(success)
        self.assertEqual(inserted, 0)
        self.assertIsNotNone(err)

        # Verify rollback left 0 partial rows in table
        (row_count,) = self.conn.execute("SELECT COUNT(*) FROM fact_sales_test").fetchone()
        self.assertEqual(row_count, 0)


if __name__ == "__main__":
    print("=" * 75)
    print("STEP 09.09: UNIT-TEST DATABASE CONNECTION, CHUNK LOAD & ROLLBACK")
    print("=" * 75)
    unittest.main(verbosity=2)
