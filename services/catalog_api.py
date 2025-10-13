# services/db_api.py
from __future__ import annotations
from typing import Dict, Any, List, Optional
import os

from services.schema import ProductCard
from services.catalog_search import TextSearchSpec, text_search, _connect, _row_to_card  # reuse internals

class CatalogAPI:
    """
    API catalog. Tools/routes call this, not SQL.
    Easy to swap later (Postgres/Elastic/etc.) without changing callers.
    """
    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or os.getenv("DB_PATH", "catalog.sqlite")

    def search_products(
        self,
        *,
        q: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        sort_spec: Optional[List[Dict[str, Any]]] = None,
        limit: int = 3,
        offset: int = 0,
    ) -> Dict[str, Any]:
        spec = TextSearchSpec(
            q=(q or None),
            filters=(filters or {}),
            sort_spec=sort_spec,
            limit=max(1, min(3, int(limit))),
            offset=max(0, min(5000, int(offset))),
        )
        return text_search(spec)

    def get_product(self, asin: str) -> Optional[ProductCard]:
        """Single-item lookup (useful for detail panels or debugging)."""
        try:
            with _connect() as conn:
                row = conn.execute("SELECT * FROM products WHERE asin = :asin LIMIT 1", {"asin": asin}).fetchone()
            return _row_to_card(row) if row else None
        except Exception:
            return None

# simple singleton accessor
_catalog_api: Optional[CatalogAPI] = None

def get_catalog_api() -> CatalogAPI:
    global _catalog_api
    if _catalog_api is None:
        _catalog_api = CatalogAPI()
    return _catalog_api
