from __future__ import annotations
import os, json, sqlite3, math
from typing import Dict, Any, List, Tuple, Set
import numpy as np, faiss
import google.generativeai as genai
from services.query_filter import compile_sql_filters
from dotenv import load_dotenv

load_dotenv()
load_dotenv("backend/.env")

DB_PATH   = os.getenv("DB_PATH", "./data/catalog.sqlite")
FAISS_DIR = os.getenv("FAISS_DIR", "./data/faiss")
MODEL     = os.getenv("EMBED_MODEL", "text-embedding-004")

K_VEC = int(os.getenv("FAISS_K_VEC", "200"))
K_LEX = int(os.getenv("FAISS_K_LEX", "200"))

W_SEM = float(os.getenv("W_SEM", "0.70"))
W_LEX = float(os.getenv("W_LEX", "0.20"))
W_RTG = float(os.getenv("W_RATING", "0.20"))
W_REV = float(os.getenv("W_REVIEWS", "0.25"))

api_key = os.getenv("GOOGLE_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

_index = None; _ids = None; _fields: List[str] = []

def _connect():
    c = sqlite3.connect(DB_PATH); c.row_factory = sqlite3.Row
    return c

def _load_index():
    global _index, _ids
    if _index is not None: return
    _index = faiss.read_index(os.path.join(FAISS_DIR, "index.faiss"))
    _ids   = np.load(os.path.join(FAISS_DIR, "ids.npy"), allow_pickle=True)

def _discover_fields(conn) -> List[str]:
    global _fields
    if _fields: return _fields
    pref = ["title","brand","categories","description","features","plus_content","top_review","department"]
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(products)").fetchall()}
    _fields = [f for f in pref if f in cols]
    return _fields

def _embed_query(q: str) -> np.ndarray:
    if not os.getenv("GOOGLE_API_KEY"):
        raise RuntimeError("GOOGLE_API_KEY missing")
    # Ensure model name has models/ prefix
    model_name = MODEL if MODEL.startswith("models/") else f"models/{MODEL}"
    r = genai.embed_content(model=model_name, content=q.strip())
    v = np.asarray(r["embedding"], dtype="float32")
    v /= (np.linalg.norm(v) + 1e-9)
    return v[None, :]  # shape (1, d)

def _lexical_asins(conn, q: str, k: int) -> Set[str]:
    toks = [t for t in q.split() if len(t) >= 2][:6]
    if not toks: return set()
    fields = [f"p.{f}" for f in _discover_fields(conn)]
    params, clauses = {}, []
    for i, t in enumerate(toks):
        or_expr = " OR ".join(f"{col} LIKE :t{i}" for col in fields)
        clauses.append(f"({or_expr})")
        params[f"t{i}"] = f"%{t}%"
    sql = f"SELECT p.asin FROM products p WHERE {' AND '.join(clauses)} LIMIT :k"
    return {r["asin"] for r in conn.execute(sql, {**params, "k": k}).fetchall()}

def _nr_rating(x): 
    try: return max(0.0, min(1.0, float(x or 0)/5.0))
    except: return 0.0

def _nr_reviews(x):
    try: x = float(x or 0); return math.log1p(x)/math.log1p(50000.0)
    except: return 0.0

def hybrid_search(q: str, filters: Dict[str, Any], limit: int, offset: int):
    if not q:
        # no text: just filtered browse
        with _connect() as conn:
            where_sql, params = compile_sql_filters(filters or {})
            where_all = f"WHERE {where_sql}" if where_sql else ""
            order_by = "p.rating DESC, p.reviews_count DESC, p.final_price ASC"
            total = conn.execute(f"SELECT COUNT(*) FROM products p {where_all}", params).fetchone()[0]
            rows = conn.execute(
                f"SELECT * FROM products p {where_all} ORDER BY {order_by} LIMIT :L OFFSET :O",
                {**params, "L": limit, "O": offset}
            ).fetchall()
            return rows, int(total), {"via":"no_query"}

    idx_path = os.path.join(FAISS_DIR, "index.faiss")
    if not os.path.exists(idx_path):
        return [], 0, {"via":"like_only", "reason":"faiss_index_missing"}

    _load_index()
    with _connect() as conn:
        # ANN
        qv = _embed_query(q)
        D, I = _index.search(qv, max(K_VEC, limit*50))
        sem = { _ids[i]: float(D[0][j]) for j,i in enumerate(I[0]) if i != -1 }

        # Lexical
        lex = _lexical_asins(conn, q, K_LEX)

        cand_asins = list(dict.fromkeys(list(sem.keys()) + list(lex)))
        if not cand_asins:
            return [], 0, {"via":"faiss_hybrid","candidates":0}

        # Filter in SQL - use named parameters for everything
        where_sql, params = compile_sql_filters(filters or {})
        
        # Add ASINs as named parameters
        asin_placeholders = ",".join(f":asin{i}" for i in range(len(cand_asins)))
        for i, asin in enumerate(cand_asins):
            params[f"asin{i}"] = asin
        
        base = f"SELECT * FROM products p WHERE p.asin IN ({asin_placeholders})"
        sql  = base + (f" AND {where_sql}" if where_sql else "")
        rows = conn.execute(sql, params).fetchall()

        ql = q.lower()

        # Precompute raw lexical overlap + phrase hits per row (unbounded)
        def lex_raw(r):
            # Concise text bag: title + brand + categories + short description
            title = (r["title"] or "").lower()
            brand = (r["brand"] or "").lower() if "brand" in r.keys() else ""
            cats  = (r["categories"] or "").lower() if "categories" in r.keys() else ""
            desc  = (r["description"] or "").lower() if "description" in r.keys() else ""

            doc_text = " ".join([title, brand, cats, desc])

            # token overlap (set Jaccard against doc)
            q_tokens = {t for t in ql.split() if len(t) >= 2}
            if not q_tokens:
                overlap = 0.0
            else:
                doc_tokens = set(w for w in doc_text.split() if len(w) >= 2)
                inter = len(q_tokens & doc_tokens)
                overlap = inter / max(1, len(q_tokens))  # ∈ [0,1]

            # phrase bonus (bounded)
            phrase = 0.0
            if ql and ql in title:
                phrase = 1.0                 
            elif ql and ql in doc_text:
                phrase = 0.5                 
            # favors phrase presence, then token coverage
            return 0.7 * phrase + 0.3 * overlap

        # Collect raw component scores for candidates
        rows_ = list(rows)  
        sem_raw = [max(0.0, sem.get(r["asin"], 0.0)) for r in rows_]
        lex_raws = [lex_raw(r) for r in rows_]
        rtg_raw = [float(r["rating"] or 0.0) / 5.0 for r in rows_]  # already [0,1]
        rev_raw = [math.log1p(float(r["reviews_count"] or 0.0)) for r in rows_]

        # Per-query min-max normalization so each term is 0..1
        def _norm(arr):
            lo = min(arr) if arr else 0.0
            hi = max(arr) if arr else 0.0
            denom = (hi - lo) if (hi - lo) > 1e-9 else 1.0
            return [(x - lo) / denom for x in arr] if arr else []

        sem_n = _norm(sem_raw)     
        lex_n = _norm(lex_raws)    
        rtg_n = _norm(rtg_raw)
        rev_n = _norm(rev_raw)

        # Final weighted score
        scored = []
        for i, r in enumerate(rows_):
            s = (
                W_SEM * sem_n[i] +
                W_LEX * lex_n[i] +
                W_RTG * rtg_n[i] +
                W_REV * rev_n[i]
            )
            scored.append((s, sem_n[i], lex_n[i], r))

        scored.sort(key=lambda x: x[0], reverse=True)
        ranked = [r for _, _, _, r in scored]
        total  = len(ranked)

        debug_info = {
            "via": "faiss_hybrid",
            "candidates": len(rows_),
            "weights": {"sem": W_SEM, "lex": W_LEX, "rating": W_RTG, "reviews": W_REV},
            "top_scores": [
                {"total": scored[i][0], "sem": scored[i][1], "lex": scored[i][2]}
                for i in range(min(3, len(scored)))
            ],
        }

        return ranked[offset:offset+limit], int(total), debug_info
