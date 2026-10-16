"""
Usage (from backend/):
    python bench/bench.py            # 1,000,000 rows (~100 MB CSV)
    python bench/bench.py 300000     # custom row count
Each library runs in its own process so peak memory is measured cleanly.
"""
import json
import os
import subprocess
import sys
import threading
import time

import numpy as np
import pandas as pd
import psutil


def make_csv(path, rows):
    rng = np.random.default_rng(0)
    df = pd.DataFrame({
        "id": rng.integers(0, rows // 2, rows),
        "age": rng.integers(18, 90, rows).astype(float),
        "score": rng.normal(50, 10, rows),
        "name": rng.choice([" Ann ", "bob", "CY", "Dee ", "eve"], rows),
        "city": rng.choice([f"city_{i}" for i in range(500)], rows),
        "note": rng.choice([f"some longer free text value number {i}" for i in range(2000)], rows),
    })
    for c in ("age", "score", "name", "city"):
        df.loc[rng.random(rows) < 0.05, c] = None
    df.to_csv(path, index=False)


class Peak:
    def __init__(self):
        self.p, self.peak, self.run = psutil.Process(), 0, True
        self.t = threading.Thread(target=self._loop, daemon=True)

    def _loop(self):
        while self.run:
            self.peak = max(self.peak, self.p.memory_info().rss)
            time.sleep(0.02)

    def __enter__(self):
        self.t.start()
        return self

    def __exit__(self, *a):
        self.run = False
        self.t.join()


def timed(T, key, fn):
    t = time.perf_counter()
    r = fn()
    T[key] = round(time.perf_counter() - t, 2)
    return r


def run_pandas(path, out):
    T = {}
    df = timed(T, "load", lambda: pd.read_csv(path))
    timed(T, "profile", lambda: (df.isna().sum(), df.duplicated().sum(),
                                 df.describe(include="all")))
    def fill():
        df["age"] = df["age"].fillna(df["age"].median())
        df["score"] = df["score"].fillna(df["score"].median())
    timed(T, "fill_nulls", fill)
    def text():
        df["name"] = df["name"].str.strip().str.lower()
    timed(T, "text_clean", text)
    df = timed(T, "dedupe", lambda: df.drop_duplicates())
    df = timed(T, "sort", lambda: df.sort_values("score"))
    timed(T, "export", lambda: df.to_csv(out, index=False))
    return T, len(df)


def run_polars(path, out):
    import polars as pl
    T = {}
    df = timed(T, "load", lambda: pl.read_csv(path))
    timed(T, "profile", lambda: (df.null_count(), df.is_duplicated().sum(), df.describe()))
    def fill():
        return df.with_columns(
            pl.col("age").fill_null(pl.col("age").median()),
            pl.col("score").fill_null(pl.col("score").median()))
    df = timed(T, "fill_nulls", fill)
    df = timed(T, "text_clean", lambda: df.with_columns(
        pl.col("name").str.strip_chars().str.to_lowercase()))
    df = timed(T, "dedupe", lambda: df.unique(maintain_order=True))
    df = timed(T, "sort", lambda: df.sort("score"))
    timed(T, "export", lambda: df.write_csv(out))
    return T, df.height


def worker(lib, path):
    out = path + f".{lib}.out.csv"
    with Peak() as pk:
        T, rows = run_pandas(path, out) if lib == "pandas" else run_polars(path, out)
    os.remove(out)
    T["total"] = round(sum(T.values()), 2)
    print(json.dumps({"lib": lib, "times": T, "rows_out": rows,
                      "peak_mb": round(pk.peak / 1024 / 1024)}))


def main():
    rows = int(sys.argv[1]) if len(sys.argv) > 1 else 1_000_000
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bench_data.csv")
    print(f"Generating {rows:,} rows ...")
    make_csv(path, rows)
    print(f"CSV size: {os.path.getsize(path) / 1024 / 1024:.0f} MB\n")
    results = []
    for lib in ("pandas", "polars"):
        print(f"Running {lib} ...")
        r = subprocess.run([sys.executable, __file__, "worker", lib, path],
                           capture_output=True, text=True)
        if r.returncode != 0:
            print(f"{lib} FAILED:\n{r.stderr[-800:]}")
            continue
        results.append(json.loads(r.stdout.strip().splitlines()[-1]))
    os.remove(path)
    if not results:
        return
    keys = list(results[0]["times"])
    print(f"\n{'step':<12}" + "".join(f"{r['lib']:>10}" for r in results))
    for k in keys:
        print(f"{k:<12}" + "".join(f"{r['times'][k]:>9}s" for r in results))
    print(f"{'peak RAM':<12}" + "".join(f"{r['peak_mb']:>8}MB" for r in results))
    print(f"{'rows out':<12}" + "".join(f"{r['rows_out']:>10,}" for r in results))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "worker":
        worker(sys.argv[2], sys.argv[3])
    else:
        main()  