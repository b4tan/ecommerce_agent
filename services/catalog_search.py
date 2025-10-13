# services/db_search.py
from __future__ import annotations
from typing import Dict, Any, List, Tuple, Optional
from pydantic import BaseModel, Field
import os, sqlite3

from services.schema import ProductCard

DB_PATH = os.getenv("DB_PATH", "./data/catalog.sqlite")

# ---------- Public spec ----------
class TextSearchSpec(BaseModel):
    q: Optional[str] = None
    filters: Dict[str, Any] = Field(default_factory=dict)   # rating_min/max, price_min/max, brand_in, department_in, category_in, availability
    sort_spec: Optional[List[Dict[str, Any]]] = None        # [{"key":"rating","dir":"desc"}]
    limit: int = Field(default=3, ge=1, le=50)
    offset: int = Field(default=0, ge=0, le=5000)

# ---------- SQLite helpers ----------
def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def _has_fts(conn: sqlite3.Connection) -> bool:
    try:
        conn.execute("SELECT 1 FROM products_fts LIMIT 1")
        return True
    except sqlite3.Error:
        return False

def _safe_str(row: sqlite3.Row, key: str) -> Optional[str]:
    v = row.get(key) if isinstance(row, dict) else row[key]
    if v is None: return None
    s = str(v).strip()
    return s or None

def _safe_float(row: sqlite3.Row, key: str) -> Optional[float]:
    try:
        v = row.get(key) if isinstance(row, dict) else row[key]
        if v in (None, ""): return None
        return float(v)
    except Exception:
        return None

def _row_to_card(r: sqlite3.Row) -> Optional[ProductCard]:
    asin = _safe_str(r, "asin"); title = _safe_str(r, "title")
    if not asin or not title: return None
    return ProductCard(
        asin=asin,
        title=title,
        final_price=_safe_float(r, "final_price"),
        currency=_safe_str(r, "currency"),
        rating=_safe_float(r, "rating"),
        image_url=_safe_str(r, "image_url"),
        url=_safe_str(r, "url"),
    )

# ---------- Query builders ----------
SORTABLE = {"rating", "final_price", "reviews_count", "bought_past_month", "score"}

def _compile_sort(sort_spec: Optional[List[Dict[str, Any]]], use_fts: bool) -> str:
    if not sort_spec:
        return "p.rating DESC, p.reviews_count DESC, p.final_price ASC"
    parts: List[str] = []
    for it in sort_spec:
        key = str(it.get("key", "")).strip().lower()
        direction = "ASC" if str(it.get("dir", "desc")).lower() == "asc" else "DESC"
        if key == "score" and use_fts:
            parts.append("score ASC")  # bm25 lower is better
        elif key in SORTABLE:
            parts.append(f"p.{key} {direction}")
    return ", ".join(parts) if parts else "p.rating DESC, p.reviews_count DESC"

def _clip(v: Optional[float], lo: float, hi: float) -> Optional[float]:
    if v is None: return None
    try:
        return max(lo, min(hi, float(v)))
    except Exception:
        return None

def _cap_list_str(arr: Optional[List[str]], max_n: int = 50) -> Optional[List[str]]:
    if not arr: return None
    seen, out = set(), []
    for s in arr:
        t = (s or "").strip()
        if not t: continue
        k = t.lower()
        if k in seen: continue
        seen.add(k); out.append(t)
        if len(out) >= max_n: break
    return out or None

def _compile_filters(filters: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    where, params = [], {}

    # rating / price / reviews
    rmin = _clip(filters.get("rating_min"), 0.0, 5.0)
    rmax = _clip(filters.get("rating_max"), 0.0, 5.0)
    if rmin is not None: where.append("p.rating >= :rating_min"); params["rating_min"] = rmin
    if rmax is not None: where.append("p.rating <= :rating_max"); params["rating_max"] = rmax

    pmin = _clip(filters.get("price_min"), 0.0, 10**9)
    pmax = _clip(filters.get("price_max"), 0.0, 10**9)
    if pmin is not None: where.append("p.final_price >= :price_min"); params["price_min"] = pmin
    if pmax is not None: where.append("p.final_price <= :price_max"); params["price_max"] = pmax

    rvmin = filters.get("reviews_min")
    rvmax = filters.get("reviews_max")
    if isinstance(rvmin, (int, float)): where.append("p.reviews_count >= :rvmin"); params["rvmin"] = int(rvmin)
    if isinstance(rvmax, (int, float)): where.append("p.reviews_count <= :rvmax"); params["rvmax"] = int(rvmax)

    # availability (bool-ish)
    avail = filters.get("availability")
    if isinstance(avail, bool):
        where.append("p.is_available = :avail")
        params["avail"] = 1 if avail else 0

    # brand / department / category
    for key, col in [("brand_in","brand"), ("department_in","department"), ("category_in","bs_category")]:
        vals = _cap_list_str(filters.get(key))
        if vals:
            placeholders = ",".join(f":{key}{i}" for i in range(len(vals)))
            where.append(f"LOWER(p.{col}) IN ({placeholders})")
            for i, v in enumerate(vals):
                params[f"{key}{i}"] = v.lower()

    return (" AND ".join(where), params)

# ---------- Main search ----------
def text_search(spec: TextSearchSpec) -> Dict[str, Any]:
    """
    Returns: {"products":[ProductCard dicts], "total":int, "debug":{...}}
    Uses FTS5 (products_fts) if present and q provided; otherwise falls back to LIKE tokens.
    """
    q = (spec.q or "").strip() or None
    filters = spec.filters or {}
    limit, offset = spec.limit, spec.offset

    with _connect() as conn:
        use_fts = _has_fts(conn) and bool(q)
        where_sql, params = _compile_filters(filters)

        if use_fts:
            # FTS path with bm25 score and relevance boosting
            # Note: 8 weights for 8 FTS columns (title, brand, categories, description, features, plus_content, top_review, department)
            select_cols = "p.*, bm25(products_fts, 8.0, 5.0, 4.0, 3.0, 2.0, 1.5, 1.2, 1.0) AS score, " \
                         "CASE WHEN LOWER(p.title) LIKE LOWER('%' || :original_q || '%') THEN 10 ELSE 0 END AS title_boost, " \
                         "CASE WHEN LOWER(p.description) LIKE LOWER('%' || :original_q || '%') THEN 5 ELSE 0 END AS desc_boost"
            join_sql = "FROM products_fts JOIN products p ON p.rowid = products_fts.rowid"
            # Convert multi-word queries to AND logic for better precision
            # "black shirt" becomes "black AND shirt" instead of "black OR shirt"
            params["original_q"] = q  # Keep original for title/description boosting
            if ' ' in q:
                # Clean and escape query for FTS5
                clean_words = []
                for word in q.split():
                    # Remove apostrophes and quotes that break FTS5
                    clean_word = word.replace("'", "").replace('"', '').replace("'", "").replace('"', '')
                    if clean_word:  # Only add non-empty words
                        clean_words.append(clean_word)
                if clean_words:
                    and_query = ' AND '.join(clean_words)
                    where_q = f"products_fts MATCH :and_query"; params["and_query"] = and_query
                else:
                    where_q = "1=0"  # No valid words, return nothing
            else:
                # Single word - clean it
                clean_q = q.replace("'", "").replace('"', '').replace("'", "").replace('"', '')
                where_q = "products_fts MATCH :q"; params["q"] = clean_q
            # Add semantic filtering to exclude obviously irrelevant categories
            semantic_filter = ""
            if 'shirt' in q.lower() or 'tshirt' in q.lower() or 't-shirt' in q.lower():
                # If looking for shirts, exclude accessories, electronics, etc.
                semantic_filter = " AND p.categories NOT LIKE '%Accessories%' AND p.categories NOT LIKE '%Electronics%' AND p.categories NOT LIKE '%Office%' AND p.title NOT LIKE '%Tie%' AND p.title NOT LIKE '%Tie%' AND p.title NOT LIKE '%Bag%'"
            elif 'laptop' in q.lower() or 'computer' in q.lower():
                # If looking for laptops, exclude accessories
                semantic_filter = " AND p.categories NOT LIKE '%Accessories%' AND p.title NOT LIKE '%Bag%' AND p.title NOT LIKE '%Case%' AND p.title NOT LIKE '%Sleeve%'"
            
            where_all = f"WHERE {where_q}{semantic_filter}" + (f" AND {where_sql}" if where_sql else "")
            # Order by relevance: title matches first, then description matches, then bm25 score
            order_by = "title_boost DESC, desc_boost DESC, score ASC"

            total = conn.execute(f"SELECT COUNT(*) {join_sql} {where_all}", params).fetchone()[0]
            rows = conn.execute(
                f"SELECT {select_cols} {join_sql} {where_all} "
                f"ORDER BY {order_by} LIMIT :limit OFFSET :offset",
                {**params, "limit": limit, "offset": offset}
            ).fetchall()
        else:
            # LIKE fallback across title/brand/description/categories (AND across tokens)
            like_params, like_clauses = {}, []
            if q:
                tokens = [t for t in q.split() if len(t) >= 2][:8]
                fields = ["p.title","p.brand","p.description","p.categories"]
                for i, t in enumerate(tokens):
                    or_expr = " OR ".join(f"{fld} LIKE :t{i}" for fld in fields)
                    like_clauses.append(f"({or_expr})")
                    like_params[f"t{i}"] = f"%{t}%"
            text_where = " AND ".join(like_clauses) if like_clauses else "1=1"
            where_all = f"WHERE {text_where}" + (f" AND {where_sql}" if where_sql else "")
            order_by = _compile_sort(spec.sort_spec, use_fts=False)

            total = conn.execute(
                f"SELECT COUNT(*) FROM products p {where_all}",
                {**like_params, **params}
            ).fetchone()[0]
            rows = conn.execute(
                f"SELECT p.* FROM products p {where_all} "
                f"ORDER BY {order_by} LIMIT :limit OFFSET :offset",
                {**like_params, **params, "limit": limit, "offset": offset}
            ).fetchall()

    products = [pc.model_dump() for r in rows if (pc := _row_to_card(r))]
    return {"products": products, "total": int(total), "debug": {"use_fts": str(use_fts), "order_by": order_by}}
