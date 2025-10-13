# services/catalog_search.py
from __future__ import annotations
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.schema import ProductCard
from services.hybrid_search import hybrid_search

class TextSearchSpec(BaseModel):
    q: Optional[str] = None
    filters: Dict[str, Any] = Field(default_factory=dict)
    sort_spec: Optional[List[Dict[str, Any]]] = None
    limit: int = Field(default=3, ge=1, le=50)
    offset: int = Field(default=0, ge=0, le=5000)

def _row_to_card(r) -> Optional[ProductCard]:
    """Convert SQLite row to ProductCard."""
    try:
        return ProductCard(
            asin=r["asin"],
            title=r["title"],
            final_price=r["final_price"] if "final_price" in r.keys() else None,
            currency=r["currency"] if "currency" in r.keys() else None,
            rating=r["rating"] if "rating" in r.keys() else None,
            image_url=r["image_url"] if "image_url" in r.keys() else None,
            url=r["url"] if "url" in r.keys() else None,
        )
    except Exception:
        return None

def text_search(spec: TextSearchSpec) -> Dict[str, Any]:
    """Hybrid search using FAISS + lexical with SQLite filters."""
    rows, total, debug = hybrid_search(
        q=spec.q or "",
        filters=spec.filters or {},
        limit=spec.limit,
        offset=spec.offset
    )
    
    products = [pc.model_dump() for r in rows if (pc := _row_to_card(r))]
    return {"products": products, "total": total, "debug": debug}
