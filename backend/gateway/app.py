from __future__ import annotations
import os
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .chat import router as chat_router
from .upload import router as upload_router

env_path = find_dotenv() or (Path(__file__).parent / ".env")
load_dotenv(env_path, override=False)

# Optional: fail fast if missing
if not os.getenv("GOOGLE_API_KEY"):
    raise RuntimeError("GOOGLE_API_KEY not found. Put it in backend/.env or export it in your shell.")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def check_health():
    return {"message": "OK"}

@app.get("/stats")
def get_stats():
    """Get rate limit statistics (for monitoring)."""
    from backend.gateway.rate_limiter import _api_call_count, ENABLE_RATE_LIMITING
    return {
        "rate_limiting_enabled": ENABLE_RATE_LIMITING,
        "api_calls_today": _api_call_count["count"],
        "api_calls_reset_time": _api_call_count["reset_time"].isoformat(),
    }

# Endpoints
app.include_router(chat_router, tags=["chat"])
app.include_router(upload_router, tags=["upload"])