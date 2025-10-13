#!/usr/bin/env python3
import csv, sqlite3, sys, tempfile
from pathlib import Path

csv.field_size_limit(1024*1024*200)  # allow very large cells

NULL_LITERALS = {"", "na", "n/a", "none", "null", "nil", "-"}

NUM_REAL  = {"final_price","initial_price","rating"}
NUM_INT   = {"reviews_count","number_of_sellers","root_bs_rank","answered_questions",
             "images_count","video_count","bought_past_month","bs_rank","subcategory_rank"}
BOOL_LIKE = {"is_available","amazon_choice"}

# --- Typing & DDL helpers -----------------------------------------------------
def infer_affinity(col: str) -> str:
    if col in NUM_INT:   return "INTEGER"
    if col in NUM_REAL:  return "REAL"
    if col in BOOL_LIKE: return "INTEGER"  # store as 0/1
    return "TEXT"

def create_typed_table(cur: sqlite3.Cursor, table: str, cols: list[str]):
    pk = "asin" if "asin" in cols else None
    defs = []
    for c in cols:
        aff = infer_affinity(c)
        # Make asin PRIMARY KEY but DON'T use WITHOUT ROWID
        # FTS5 needs numeric rowid, and asin is TEXT
        defs.append(f'"{c}" {aff}{" PRIMARY KEY" if pk==c else ""}')
    cur.execute(f'DROP TABLE IF EXISTS "{table}";')
    # Never use WITHOUT ROWID - we need the numeric rowid for FTS5
    cur.execute(f'CREATE TABLE "{table}" ({", ".join(defs)});')

def create_btree_indexes(cur: sqlite3.Cursor, table: str, cols: list[str]):
    has = cols.__contains__
    # equality / facets
    for c in ["brand","department","availability","root_bs_category","bs_category",
              "seller_name","buybox_seller","is_available"]:
        if has(c): cur.execute(f'CREATE INDEX IF NOT EXISTS ix_{table}_{c} ON "{table}"({c});')
    # ranges / sorts
    for c in ["final_price","rating","reviews_count","bs_rank","subcategory_rank","bought_past_month"]:
        if has(c): cur.execute(f'CREATE INDEX IF NOT EXISTS ix_{table}_{c} ON "{table}"({c});')
    # combos: equality + range
    if has("brand") and has("final_price"):
        cur.execute(f'CREATE INDEX IF NOT EXISTS ix_{table}_brand_price ON "{table}"(brand, final_price);')
    if has("department") and has("final_price"):
        cur.execute(f'CREATE INDEX IF NOT EXISTS ix_{table}_dept_price ON "{table}"(department, final_price);')
    if has("availability") and has("final_price"):
        cur.execute(f'CREATE INDEX IF NOT EXISTS ix_{table}_avail_price ON "{table}"(availability, final_price);')
    if has("is_available") and has("final_price"):
        cur.execute(f'CREATE INDEX IF NOT EXISTS ix_{table}_isa_price ON "{table}"(is_available, final_price);')
    # browse rank combos
    if has("root_bs_category") and has("bs_rank"):
        cur.execute(f'CREATE INDEX IF NOT EXISTS ix_{table}_rootcat_bsr ON "{table}"(root_bs_category, bs_rank);')
    if has("bs_category") and has("subcategory_rank"):
        cur.execute(f'CREATE INDEX IF NOT EXISTS ix_{table}_cat_subrank ON "{table}"(bs_category, subcategory_rank);')
    # case-insensitive prefix search on title
    if has("title"):
        cur.execute(f'CREATE INDEX IF NOT EXISTS ix_{table}_title_nocase ON "{table}"(title COLLATE NOCASE);')

# --- FTS5 (external content) ---------------------------------------------------
FTS_CANDIDATE_ORDER = [
    "title","brand","categories","description","features",
    "plus_content","top_review","department"
]
FTS_TOKENIZE = "unicode61 remove_diacritics 1 tokenchars '._-'"

def create_fts_index(cur: sqlite3.Cursor, table: str, cols: list[str]):
    fts_cols = [c for c in FTS_CANDIDATE_ORDER if c in cols]
    if not fts_cols:
        return
    fts_table = f"{table}_fts"
    col_list = ", ".join(fts_cols)
    
    # Always use 'rowid' - we're not using WITHOUT ROWID anymore
    # SQLite will create an implicit numeric rowid column even with TEXT PRIMARY KEY

    cur.execute(f'DROP TABLE IF EXISTS "{fts_table}";')
    cur.execute(
        f'''CREATE VIRTUAL TABLE "{fts_table}" USING fts5(
                {col_list},
                content='{table}', content_rowid='rowid',
                tokenize="{FTS_TOKENIZE}"
            );'''
    )
    # initial sync - rebuild FTS index
    cur.execute(f'INSERT INTO "{fts_table}"("{fts_table}") VALUES(\'rebuild\');')

    # triggers to keep FTS in sync
    cur.execute(f'''
        CREATE TRIGGER IF NOT EXISTS trg_{table}_ai AFTER INSERT ON "{table}" BEGIN
            INSERT INTO "{fts_table}"(rowid, {col_list})
            VALUES (new.rowid, {", ".join(f"new.{c}" for c in fts_cols)});
        END;
    ''')
    cur.execute(f'''
        CREATE TRIGGER IF NOT EXISTS trg_{table}_ad AFTER DELETE ON "{table}" BEGIN
            INSERT INTO "{fts_table}"("{fts_table}", rowid, {col_list})
            VALUES ('delete', old.rowid, {", ".join(["NULL"]*len(fts_cols))});
        END;
    ''')
    cur.execute(f'''
        CREATE TRIGGER IF NOT EXISTS trg_{table}_au AFTER UPDATE ON "{table}" BEGIN
            INSERT INTO "{fts_table}"("{fts_table}", rowid, {col_list})
            VALUES ('delete', old.rowid, {", ".join(["NULL"]*len(fts_cols))});
            INSERT INTO "{fts_table}"(rowid, {col_list})
            VALUES (new.rowid, {", ".join(f"new.{c}" for c in fts_cols)});
        END;
    ''')

def finalize_db(conn: sqlite3.Connection):
    cur = conn.cursor()
    cur.execute("ANALYZE;")
    cur.execute("PRAGMA optimize;")
    conn.commit()

def resolve_db_path(db_arg: str) -> Path:
    p = Path(db_arg)
    if p.exists() and p.is_dir():
        return p / "catalog.sqlite"
    if not p.parent.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
    return p

def clean_text(v: str|None) -> str:
    if v is None: return ""
    s = v.replace("\xa0"," ").strip()  # strip NBSP then trim
    return "" if s.lower() in NULL_LITERALS else s

def norm_real(s: str) -> str:
    s = s.replace("$","").replace(",","")
    return s if s and all(ch in "0123456789+-.eE" for ch in s) else ""

def norm_int(s: str) -> str:
    s = s.replace("$","").replace(",","")
    try:
        return str(int(float(s))) if s else ""
    except Exception:
        return ""

def norm_bool(s: str) -> str:
    t = s.lower()
    if t in {"true","t","yes","y","1"}: return "1"
    if t in {"false","f","no","n","0"}: return "0"
    return ""

def norm_department(s: str) -> str:
    t = s.lower()
    if t in {"men","mens"}: return "Men"
    if t in {"women","womens"}: return "Women"
    return s

def norm_availability(s: str) -> str:
    t = s.lower()
    if t.startswith("in stock"): return "in_stock"
    if t.startswith("out of stock"): return "out_of_stock"
    return t

def normalize_row(row: dict[str,str], columns: list[str]) -> dict[str,str]:
    out = {}
    for c in columns:
        val = clean_text(row.get(c))
        if not val:
            out[c] = ""
            continue
        if c in NUM_REAL:         out[c] = norm_real(val)
        elif c in NUM_INT:        out[c] = norm_int(val)
        elif c in BOOL_LIKE:      out[c] = norm_bool(val)
        elif c == "department":   out[c] = norm_department(val)
        elif c == "availability": out[c] = norm_availability(val)
        else:                     out[c] = val
    return out

def write_clean_csv(in_csv: Path, out_csv: Path) -> list[str]:
    with in_csv.open("r", encoding="utf-8-sig", newline="") as fin, \
         out_csv.open("w", encoding="utf-8", newline="") as fout:
        reader = csv.DictReader(fin)     # comma-delimited
        cols = [h.strip() for h in (reader.fieldnames or [])]
        writer = csv.DictWriter(fout, fieldnames=cols)
        writer.writeheader()
        for row in reader:
            writer.writerow(normalize_row(row, cols))
    return cols

def load_into_sqlite(clean_csv: Path, db_path: Path, table: str, cols: list[str]) -> int:
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    cur = conn.cursor()
    cur.execute(f'DROP TABLE IF EXISTS "{table}";')
    create_typed_table(cur, table, cols)

    placeholders = ", ".join(f":{c}" for c in cols)
    ins = f'INSERT INTO "{table}" ({", ".join(f"""\"{c}\"""" for c in cols)}) VALUES ({placeholders});'

    total, batch, B = 0, [], 1000
    with clean_csv.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # convert empty strings to None (NULL) on insert
            batch.append({k: (v if (v is not None and v != "") else None) for k, v in row.items()})
            if len(batch) >= B:
                cur.executemany(ins, batch); conn.commit(); total += len(batch); batch.clear()
        if batch:
            cur.executemany(ins, batch); conn.commit(); total += len(batch)

    # Create indexes and FTS after bulk inserts
    create_btree_indexes(cur, table, cols)
    create_fts_index(cur, table, cols)
    finalize_db(conn)

    n = cur.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
    conn.close()
    return n

def main(csv_path: str, db_path: str, table: str = "products"):
    in_csv = Path(csv_path)
    if not in_csv.exists(): sys.exit(f"CSV not found: {in_csv}")
    db_p = resolve_db_path(db_path)

    with tempfile.TemporaryDirectory() as td:
        out_csv = Path(td) / "clean.csv"
        cols = write_clean_csv(in_csv, out_csv)
        rows = load_into_sqlite(out_csv, db_p, table, cols)

    print(f"Done. Cleaned → loaded {rows} rows into {db_p} (table '{table}').")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit("Usage: python build_db.py <csv_path> <db_path_or_file> [table_name]")
    csv_path = sys.argv[1]
    db_path = sys.argv[2]
    table = sys.argv[3] if len(sys.argv) > 3 else "products"
    main(csv_path, db_path, table)
