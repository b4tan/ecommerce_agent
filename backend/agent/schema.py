from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from enum import Enum
from services.schema import ProductCard

class IntentType(str, Enum):
    RECOMMENDATION = "RECOMMENDATION"
    QUESTION = "QUESTION"
    CONVERSATION = "CONVERSATION"

class StructuredResponse(BaseModel):
    """Structured response from the AI agent."""
    response: str = Field(description="The main response text to show the user")
    intent: IntentType = Field(description="The intent of this response - whether recommending products, asking questions, or just conversing")

class AgentRequest(BaseModel):
    conversation_id: Optional[str] = None
    inputs: Dict[str, Optional[str]] = Field(default_factory=dict) 

class AgentResponse(BaseModel):
    message: str
    products: Optional[List[ProductCard]] = None
