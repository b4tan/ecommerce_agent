#!/usr/bin/env python3
# inspect_sqlite.py — simple SQLite table checker

import argparse
import sqlite3
from pathlib import Path
from textwrap import shorten

def connect(db_path: str) -> sqlite3.Connection:
    p = Path(db_path)
    if not p.exists():
        raise SystemExit(f"DB not found: {p}")
    conn = sqlite3.connect(str(p))
    conn.row_factory = sqlite3.Row
    return conn

def get_columns(conn: sqlite3.Connection, table: str):
    cur = conn.execute(f'PRAGMA table_info("{table}");')
    cols = [r["name"] for r in cur.fetchall()]
    if not cols:
        raise SystemExit(f"Table not found or empty schema: {table}")
    return cols

def count_rows(conn: sqlite3.Connection, table: str) -> int:
    cur = conn.execute(f'SELECT COUNT(*) AS c FROM "{table}";')
    return cur.fetchone()["c"]

def head(conn: sqlite3.Connection, table: str, limit: int, sample_cols=None):
    cols = get_columns(conn, table)
    if sample_cols:
        use = [c for c in sample_cols if c in cols]
        if not use:
            use = cols
    else:
        use = cols
    sel = ", ".join(f'"{c}"' for c in use)
    cur = conn.execute(f'SELECT {sel} FROM "{table}" LIMIT ?;', (limit,))
    rows = cur.fetchall()
    # Print a simple table
    print("\n== Sample rows ==")
    print(" | ".join(use))
    for r in rows:
        print(" | ".join(shorten(str(r[c]), width=80, placeholder="…") for c in use))

def quick_stats(conn: sqlite3.Connection, table: str):
    print("\n== Quick stats (if columns exist) ==")
    def stat(col, cast="REAL"):
        cur = conn.execute(
            f'SELECT '
            f'COUNT(*) AS n, '
            f'COUNT(NULLIF(TRIM("{col}"), "")) AS nonnull, '
            f'MIN(CAST("{col}" AS {cast})) AS min_v, '
            f'MAX(CAST("{col}" AS {cast})) AS max_v, '
            f'AVG(CAST("{col}" AS {cast})) AS avg_v '
            f'FROM "{table}";'
        )
        r = cur.fetchone()
        print(f"- {col}: rows={r['n']}, non-null={r['nonnull']}, min={r['min_v']}, max={r['max_v']}, avg={r['avg_v']}")
    cols = get_columns(conn, table)
    if "final_price" in cols: stat("final_price", "REAL")
    if "initial_price" in cols: stat("initial_price", "REAL")
    if "rating" in cols: stat("rating", "REAL")
    if "reviews_count" in cols: stat("reviews_count", "INTEGER")

def top_k(conn: sqlite3.Connection, table: str, col: str, k: int = 10):
    print(f"\n== Top {k} by '{col}' ==")
    cur = conn.execute(
        f'SELECT "{col}" AS val, COUNT(*) AS c '
        f'FROM "{table}" '
        f'GROUP BY "{col}" '
        f'ORDER BY c DESC, val ASC LIMIT ?;', (k,)
    )
    for val, c in cur.fetchall():
        print(f"{val!r}: {c}")

def maybe_show_freqs(conn: sqlite3.Connection, table: str):
    cols = get_columns(conn, table)
    if "department" in cols:
        top_k(conn, table, "department", 10)
    if "bs_category" in cols:
        top_k(conn, table, "bs_category", 10)

def main():
    ap = argparse.ArgumentParser(description="Inspect a SQLite table quickly.")
    ap.add_argument("--db", required=True, help="Path to SQLite DB (e.g., ./db/catalog.sqlite)")
    ap.add_argument("--table", default="products", help="Table name (default: products)")
    ap.add_argument("--limit", type=int, default=5, help="How many sample rows to show (default: 5)")
    ap.add_argument("--sample-cols", nargs="*", help="Optional list of columns to show in the sample")
    ap.add_argument("--sql", help="Optional custom SQL to run (prints first 50 rows)")
    args = ap.parse_args()

    conn = connect(args.db)

    print(f"DB: {args.db}")
    print(f"Table: {args.table}")

    cols = get_columns(conn, args.table)
    print("\n== Columns ==")
    print(", ".join(cols))

    total = count_rows(conn, args.table)
    print(f"\n== Row count ==\n{total}")

    head(conn, args.table, args.limit, args.sample_cols)
    quick_stats(conn, args.table)
    maybe_show_freqs(conn, args.table)

    if args.sql:
        print("\n== Custom SQL (first 50 rows) ==")
        cur = conn.execute(args.sql)
        for i, row in enumerate(cur.fetchall()):
            if i >= 50: break
            print(dict(row))

    conn.close()

if __name__ == "__main__":
    main()
