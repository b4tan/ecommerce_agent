# agent/graph.py
import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Literal
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import SystemMessage, ToolMessage
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from backend.agent.tools import product_search
from backend.agent.schema import StructuredResponse

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path, override=False)

THREAD_ID = "global"

import pathlib
SYSTEM_PROMPT = (pathlib.Path(__file__).parent / "system_prompt.txt").read_text()

TOOLS = [product_search]
TOOL_REG = {t.name: t for t in TOOLS}

# Get API key from environment
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise RuntimeError("GOOGLE_API_KEY not found in environment")

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",  # Switch to avoid quota limit
    temperature=0,
    google_api_key=api_key
)

# Create structured output LLM
llm_structured = llm.with_structured_output(StructuredResponse)
llm_with_tools = llm.bind_tools(TOOLS)

def llm_call(state: MessagesState):
    msgs = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = llm_with_tools.invoke(msgs)
    
    # If no tool calls, add structured intent
    if not getattr(response, 'tool_calls', None):
        # Use structured LLM to get intent for non-tool responses
        structured_response = llm_structured.invoke(msgs)
        from langchain_core.messages import AIMessage
        response_text = f"{structured_response.response} [INTENT:{structured_response.intent.value}]"
        return {"messages": [AIMessage(content=response_text)]}
    
    return {"messages": [response]}

def final_response(state: MessagesState):
    """Add structured intent to the final response if not already present."""
    last_message = state["messages"][-1]
    
    # If already has intent marker, don't add another
    if hasattr(last_message, 'content') and '[INTENT:' in last_message.content:
        return {"messages": []}
    
    # Add structured intent to the final response
    msgs = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    structured_response = llm_structured.invoke(msgs)
    
    from langchain_core.messages import AIMessage
    response_text = f"{structured_response.response} [INTENT:{structured_response.intent.value}]"
    return {"messages": [AIMessage(content=response_text)]}

def tool_node(state: MessagesState):
    import json
    from pydantic import BaseModel
    
    def make_serializable(obj):
        """Convert Pydantic models and other objects to JSON-serializable format."""
        if isinstance(obj, BaseModel):
            return obj.model_dump(mode='json')
        elif isinstance(obj, dict):
            return {k: make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [make_serializable(item) for item in obj]
        elif hasattr(obj, '__str__') and not isinstance(obj, (str, int, float, bool, type(None))):
            return str(obj)
        return obj
    
    last = state["messages"][-1]
    out = []
    for tc in getattr(last, "tool_calls", []) or []:
        tool = TOOL_REG.get(tc["name"])
        if not tool:
            continue
        observation = tool.invoke(tc.get("args") or {})
        # Convert to JSON-serializable format then to string
        serializable = make_serializable(observation)
        content = json.dumps(serializable) if isinstance(serializable, (dict, list)) else str(observation)
        out.append(ToolMessage(content=content, tool_call_id=tc["id"]))
    return {"messages": out}

def should_continue(state: MessagesState) -> Literal["Action", "final_response"]:
    last = state["messages"][-1]
    return "Action" if getattr(last, "tool_calls", None) else "final_response"

builder = StateGraph(MessagesState)
builder.add_node("llm_call", llm_call)
builder.add_node("environment", tool_node)
builder.add_node("final_response", final_response)
builder.add_edge(START, "llm_call")
builder.add_conditional_edges("llm_call", should_continue, {"Action": "environment", "final_response": "final_response"})
builder.add_edge("environment", "llm_call")
builder.add_edge("final_response", END)

memory = MemorySaver()  # in-process, resets on restart as you wanted
agent = builder.compile(checkpointer=memory)
