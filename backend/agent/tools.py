# agent/tools.py
import json
from typing import Dict, Any, Union
from langchain_core.tools import tool

from services.catalog_search import TextSearchSpec, text_search

# ---- Tool: TEXT SEARCH ----
@tool("product_search")
def product_search(payload: Union[Dict[str, Any], str]) -> Dict[str, Any]:
    """
    Search for products in the catalog. Call this when users ask about products.
    
    Args:
        payload: Dict with "q" (search query), "filters" (optional), "limit" (max 3)
    
    Returns: {"products":[...], "total":int, "debug":{...}}
    """
    # Handle if payload is a JSON string
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError as e:
            return {"products": [], "total": 0, "debug": {"error": f"invalid JSON: {e}"}}
    
    payload = payload or {}
    try:
        spec = TextSearchSpec(
            q=(payload.get("q") or None),
            filters=(payload.get("filters") or {}),
            sort_spec=payload.get("sort_spec"),
            limit=max(1, min(3, int(payload.get("limit", 3)))),
            offset=int(payload.get("offset", 0)),
        )
    except Exception as e:
        return {"products": [], "total": 0, "debug": {"error": f"bad payload: {e}"}}

    try:
        result = text_search(spec)
        # Convert Pydantic models to JSON-serializable dicts
        if result.get("products"):
            result["products"] = [
                p.model_dump(mode='json') if hasattr(p, 'model_dump') else p
                for p in result["products"]
            ]
            
            # Adjust number of products returned based on what was found:
            # - If found 1 item: return 1
            # - If found 2 items: return 2
            # - If found >= 3 items: return 3
            total_found = result.get("total", 0)
            if total_found == 1:
                result["products"] = result["products"][:1]
            elif total_found == 2:
                result["products"] = result["products"][:2]
            else:  # total_found >= 3
                result["products"] = result["products"][:3]
                
        return result
    except Exception as e:
        return {"products": [], "total": 0, "debug": {"error": f"exec: {type(e).__name__}: {e}"}}
