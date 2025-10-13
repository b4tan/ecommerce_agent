from fastapi import APIRouter, HTTPException
from langchain_core.messages import HumanMessage, ToolMessage
from typing import Any, Dict, List

from backend.agent.graph import agent, THREAD_ID
from backend.gateway.schema import ChatRequest, ChatResponse
from services.schema import ProductCard

router = APIRouter()

def _extract_products(messages: List[Any]) -> List[ProductCard]:
    """Pull product items from the most recent ToolMessage only."""
    import json
    items: List[ProductCard] = []
    
    # Only look at the most recent messages to avoid showing old products
    # Go through messages in reverse to find the most recent tool call
    for m in reversed(messages):
        try:
            if isinstance(m, ToolMessage):
                content = m.content
                # Handle if content is a JSON string
                if isinstance(content, str):
                    try:
                        content = json.loads(content)
                    except json.JSONDecodeError:
                        continue
                if isinstance(content, dict):
                    raw = content.get("products") or content.get("items")
                    if isinstance(raw, list):
                        for r in raw:
                            # Best-effort safe cast to ProductCard
                            try:
                                product = ProductCard(**r)
                                items.append(product)
                            except Exception:
                                continue
                        # If we found products in this tool message, return them
                        # (don't look at older tool messages)
                        if items:
                            return items
        except Exception:
            continue
    return items

# ---- TEXT CHAT ----
@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    q = (req.query or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail="Query text cannot be empty.")

    config = {"configurable": {"thread_id": THREAD_ID}}
    result = agent.invoke({"messages": [HumanMessage(content=q)]}, config)

    msgs = result["messages"]
    assistant_text = msgs[-1].content if msgs else ""
    products = _extract_products(msgs)
    
    # Parse AI's intent from structured output
    intent = None
    import re
    
    # Look for structured intent marker
    intent_match = re.search(r'\[INTENT:(\w+)\]', assistant_text)
    if intent_match:
        intent = intent_match.group(1)
    
    # Show products only if AI explicitly marked this as a recommendation
    should_show_products = (
        products and 
        len(products) > 0 and
        intent == 'RECOMMENDATION'
    )
    
    # Clean the response text by removing intent markers
    clean_response = re.sub(r'\[INTENT:\w+\]', '', assistant_text).strip()
    
    return ChatResponse(
        response=clean_response, 
        products=products if should_show_products else None,
        intent=intent
    )
