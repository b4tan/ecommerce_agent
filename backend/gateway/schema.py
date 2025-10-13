from pydantic import BaseModel
from typing import Optional, List
from services.schema import ProductCard

class ChatRequest(BaseModel):
    query: str

class ChatResponse(BaseModel):
    response: str
    products: Optional[List[ProductCard]] = None
    intent: Optional[str] = None  # RECOMMENDATION, QUESTION, or CONVERSATION
