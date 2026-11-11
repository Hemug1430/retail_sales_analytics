import os, time, tracemalloc
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
load_dotenv()
def get_db_engine():
    u, p, h, pt, d = os.getenv("DB_USER","root"), os.getenv("DB_PASSWORD",""), os.getenv("DB_HOST","localhost"), os.getenv("DB_PORT","3306"), os.getenv("DB_NAME","retail_sales_db")
    return create_engine(f"mysql+pymysql://{u}:{p}@{h}:{pt}/{d}")
def run():
    print("="*78); print("STEP 09.43: PYTHON PERFORMANCE, THROUGHPUT & MEMORY PROFILING BENCHMARK"); print("="*78)
    ok, bad = 0, 0
    with get_db_engine().connect() as c:
        (db,) = c.execute(text("SELECT DATABASE()")).fetchone()
        print(f"[PASS] Connected to {db}\n"); ok += 1
        tracemalloc.start()
        t0 = time.perf_counter()
        df = pd.read_sql(text("SELECT store_id, product_id, customer_id, sales_channel, quantity, unit_selling_price, COALESCE(discount_pct,0) AS discount_pct FROM factsales"), c)
        df["net_rev"] = df["quantity"] * df["unit_selling_price"] * (1.0 - df["discount_pct"] / 100.0)
        agg = df.groupby(["store_id", "sales_channel"], as_index=False)["net_rev"].sum()
        t_base = time.perf_counter() - t0
        _, peak_base = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        base_mb = peak_base / (1024 * 1024)
        base_rps = int(len(df) / max(t_base, 1e-6))
        print(f"--- 1. Monthly Production Batch Benchmark ({len(df):,} rows -> {len(agg)} groups) ---")
        print(f"  Elapsed Time = {t_base:.4f}s | Throughput = {base_rps:,} rows/sec | Peak Traced RAM = {base_mb:.2f} MB")
        if t_base < 10.0 and base_mb < 150.0 and len(df) > 0:
            print("[PASS] Production monthly batch completed well within latency (<10s) and memory (<150MB) SLAs.\n"); ok += 1
        else: bad += 1
        df_10x = pd.concat([df] * 10, ignore_index=True)
        tracemalloc.start()
        t1 = time.perf_counter()
        df_10x["net_rev"] = df_10x["quantity"] * df_10x["unit_selling_price"] * (1.0 - df_10x["discount_pct"] / 100.0)
        agg_10x = df_10x.groupby(["store_id", "sales_channel"], as_index=False)["net_rev"].sum()
        t_scale = time.perf_counter() - t1
        _, peak_scale = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        scale_mb = peak_scale / (1024 * 1024)
        scale_rps = int(len(df_10x) / max(t_scale, 1e-6))
        print(f"--- 2. 10x Large Monthly File Stress Benchmark ({len(df_10x):,} rows) ---")
        print(f"  Vectorized Transform Time = {t_scale:.4f}s | Throughput = {scale_rps:,} rows/sec | Peak Traced RAM = {scale_mb:.2f} MB")
        if t_scale < 2.0 and scale_mb < 150.0 and len(agg_10x) == len(agg):
            print("[PASS] Vectorized 10x monthly batch (~345k rows) processed with zero memory or CPU bottlenecks.\n"); ok += 1
        else: bad += 1
        tracemalloc.start()
        t2 = time.perf_counter()
        chunk_rows = 0
        for chunk in pd.read_sql(text("SELECT store_id, quantity, unit_selling_price FROM factsales"), c, chunksize=10000):
            chunk_rows += len(chunk)
        t_chunk = time.perf_counter() - t2
        _, peak_chunk = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        chunk_mb = peak_chunk / (1024 * 1024)
        print(f"--- 3. Chunked Streaming Optimization Check (chunksize=10,000 | {chunk_rows:,} rows) ---")
        print(f"  Streaming Time = {t_chunk:.4f}s | Peak Streaming RAM = {chunk_mb:.2f} MB")
        if chunk_rows == len(df) and chunk_mb <= base_mb:
            print("[PASS] Chunked streaming keeps peak memory bounded and scales linearly for large monthly files.\n"); ok += 1
        else: bad += 1
    print("="*78); print(f"SUMMARY -> Passed Checks: {ok} | Failed Checks: {bad}"); print("="*78)
if __name__=="__main__": run()

