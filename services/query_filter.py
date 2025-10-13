# Minimal, single-source-of-truth for filters → SQL WHERE.
from __future__ import annotations
from typing import Dict, Any, Tuple

SCHEMA = {
    "rating":            {"type": "num", "col": "rating"},
    "final_price":       {"type": "num", "col": "final_price"},
    "reviews_count":     {"type": "num", "col": "reviews_count"},
    "bought_past_month": {"type": "num", "col": "bought_past_month"},
    "availability":      {"type": "bool","col": "is_available"},
    "brand_in":          {"type": "in",  "col": "brand",      "lower": True},
    "department_in":     {"type": "in",  "col": "department", "lower": True},
    "category_in":       {"type": "in",  "col": "bs_category","lower": True},
}

def compile_sql_filters(filters: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    cl, p = [], {}
    for key, m in SCHEMA.items():
        t, col = m["type"], m["col"]
        if t == "num":
            lo, hi = filters.get(f"{key}_min"), filters.get(f"{key}_max")
            if lo is not None: cl.append(f"p.{col} >= :{key}_min"); p[f"{key}_min"] = float(lo)
            if hi is not None: cl.append(f"p.{col} <= :{key}_max"); p[f"{key}_max"] = float(hi)
        elif t == "bool":
            v = filters.get(key)
            if isinstance(v, bool): cl.append(f"p.{col} = :{key}"); p[key] = 1 if v else 0
        elif t == "in":
            vals = filters.get(key) or []
            if not isinstance(vals, list): vals = [vals]
            vals = [str(v).strip() for v in vals if str(v).strip()]
            if vals:
                if m.get("lower"): col_expr = f"LOWER(p.{col})"; vals = [v.lower() for v in dict.fromkeys(vals)]
                else:              col_expr = f"p.{col}"
                ph = ",".join(f":{key}{i}" for i in range(len(vals)))
                cl.append(f"{col_expr} IN ({ph})")
                for i,v in enumerate(vals): p[f"{key}{i}"] = v
    return (" AND ".join(cl), p)
