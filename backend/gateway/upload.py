# gateway/upload.py
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from typing import Any, List, Optional
from base64 import b64encode
import os

from langchain_core.messages import HumanMessage, ToolMessage

from backend.agent.graph import agent, THREAD_ID
from services.schema import ProductCard
from backend.gateway.schema import ChatResponse

router = APIRouter()

# Accept common web image types
ALLOWED_MIME = {"image/png", "image/jpeg", "image/jpg", "image/gif", "image/webp"}
MAX_IMAGE_MB = float(os.getenv("MAX_IMAGE_MB", "20"))

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


@router.post("/chat/upload", response_model=ChatResponse)
async def chat_upload(
    file: UploadFile = File(...),
    query: str = Form(""),
):
    # ---- sanity checks ----
    ctype = (file.content_type or "").lower()
    if ctype not in ALLOWED_MIME:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ctype or 'unknown'}")
    raw = await file.read()
    size_mb = len(raw) / (1024 * 1024)
    if size_mb > MAX_IMAGE_MB:
        raise HTTPException(status_code=400, detail=f"Image too large ({size_mb:.1f} MB). Max is {MAX_IMAGE_MB} MB.")

    # ---- build multimodal message (image + optional text) ----
    b64 = b64encode(raw).decode("ascii")
    data_url = f"data:{ctype};base64,{b64}"
    user_text = (query or "").strip() or "Please identify the product in this image and find matches."

    content = [
        {"type": "text", "text": user_text},
        {"type": "image_url", "image_url": data_url},
    ]

    # ---- invoke agent (single LLM with tools) ----
    config = {"configurable": {"thread_id": THREAD_ID}}
    result = agent.invoke({"messages": [HumanMessage(content=content)]}, config)

    msgs: List[Any] = result.get("messages", [])
    assistant_text = (msgs[-1].content if msgs else "Processed image.")
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
