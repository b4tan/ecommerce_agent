"""Rate limiting and cost safeguards for the commerce agent."""
from __future__ import annotations
import time
import os
from collections import defaultdict
from typing import Dict, Tuple
from fastapi import HTTPException, Request, status
from datetime import datetime, timedelta

# Rate limiting configuration
MAX_REQUESTS_PER_MINUTE = int(os.getenv("MAX_REQUESTS_PER_MINUTE", "10"))
MAX_REQUESTS_PER_HOUR = int(os.getenv("MAX_REQUESTS_PER_HOUR", "100"))
MAX_REQUESTS_PER_DAY = int(os.getenv("MAX_REQUESTS_PER_DAY", "500"))
MAX_IMAGE_UPLOADS_PER_HOUR = int(os.getenv("MAX_IMAGE_UPLOADS_PER_HOUR", "20"))
MAX_IMAGE_UPLOADS_PER_DAY = int(os.getenv("MAX_IMAGE_UPLOADS_PER_DAY", "100"))

# Cost safeguards
MAX_DAILY_API_CALLS = int(os.getenv("MAX_DAILY_API_CALLS", "1000"))  # Total Gemini API calls
ENABLE_RATE_LIMITING = os.getenv("ENABLE_RATE_LIMITING", "true").lower() == "true"

# In-memory storage (for production, use Redis)
_request_counts: Dict[str, list] = defaultdict(list)
_image_counts: Dict[str, list] = defaultdict(list)
_api_call_count = {"count": 0, "reset_time": datetime.now() + timedelta(days=1)}


def _get_client_id(request: Request) -> str:
    """Get client identifier (IP address)."""
    # Try to get real IP from headers (if behind proxy)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fallback to direct client IP
    if request.client:
        return request.client.host
    
    return "unknown"


def _clean_old_timestamps(timestamps: list, window_seconds: int) -> list:
    """Remove timestamps older than the window."""
    cutoff = time.time() - window_seconds
    return [ts for ts in timestamps if ts > cutoff]


def check_rate_limit(request: Request, is_image: bool = False):
    """
    Check if the request is within rate limits.
    
    Args:
        request: FastAPI request object
        is_image: Whether this is an image upload request
        
    Raises:
        HTTPException: If rate limit is exceeded
    """
    if not ENABLE_RATE_LIMITING:
        return
    
    client_id = _get_client_id(request)
    current_time = time.time()
    
    # Clean old timestamps
    _request_counts[client_id] = _clean_old_timestamps(_request_counts[client_id], 86400)  # 24 hours
    
    # Add current request
    _request_counts[client_id].append(current_time)
    
    # Check per-minute limit
    recent_minute = [ts for ts in _request_counts[client_id] if ts > current_time - 60]
    if len(recent_minute) > MAX_REQUESTS_PER_MINUTE:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: Maximum {MAX_REQUESTS_PER_MINUTE} requests per minute. Please try again later.",
            headers={"Retry-After": "60"}
        )
    
    # Check per-hour limit
    recent_hour = [ts for ts in _request_counts[client_id] if ts > current_time - 3600]
    if len(recent_hour) > MAX_REQUESTS_PER_HOUR:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: Maximum {MAX_REQUESTS_PER_HOUR} requests per hour. Please try again later.",
            headers={"Retry-After": "3600"}
        )
    
    # Check per-day limit
    recent_day = [ts for ts in _request_counts[client_id] if ts > current_time - 86400]
    if len(recent_day) > MAX_REQUESTS_PER_DAY:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: Maximum {MAX_REQUESTS_PER_DAY} requests per day. Please try again tomorrow.",
            headers={"Retry-After": "86400"}
        )
    
    # Additional checks for image uploads
    if is_image:
        _image_counts[client_id] = _clean_old_timestamps(_image_counts[client_id], 86400)
        _image_counts[client_id].append(current_time)
        
        # Check image upload per-hour limit
        recent_image_hour = [ts for ts in _image_counts[client_id] if ts > current_time - 3600]
        if len(recent_image_hour) > MAX_IMAGE_UPLOADS_PER_HOUR:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Image upload limit exceeded: Maximum {MAX_IMAGE_UPLOADS_PER_HOUR} images per hour.",
                headers={"Retry-After": "3600"}
            )
        
        # Check image upload per-day limit
        recent_image_day = [ts for ts in _image_counts[client_id] if ts > current_time - 86400]
        if len(recent_image_day) > MAX_IMAGE_UPLOADS_PER_DAY:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Image upload limit exceeded: Maximum {MAX_IMAGE_UPLOADS_PER_DAY} images per day.",
                headers={"Retry-After": "86400"}
            )


def check_api_call_limit():
    """
    Check if the total API call limit has been exceeded.
    This is a global limit to prevent excessive Gemini API costs.
    
    Raises:
        HTTPException: If API call limit is exceeded
    """
    if not ENABLE_RATE_LIMITING:
        return
    
    # Reset counter if it's a new day
    if datetime.now() > _api_call_count["reset_time"]:
        _api_call_count["count"] = 0
        _api_call_count["reset_time"] = datetime.now() + timedelta(days=1)
    
    # Check limit
    if _api_call_count["count"] >= MAX_DAILY_API_CALLS:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Daily API call limit reached. Service will resume tomorrow. Please contact the administrator if you need higher limits.",
            headers={"Retry-After": str(int((_api_call_count["reset_time"] - datetime.now()).total_seconds()))}
        )
    
    # Increment counter
    _api_call_count["count"] += 1


def get_rate_limit_stats(client_id: str) -> Dict[str, int]:
    """Get current rate limit statistics for a client."""
    current_time = time.time()
    
    _request_counts[client_id] = _clean_old_timestamps(_request_counts[client_id], 86400)
    _image_counts[client_id] = _clean_old_timestamps(_image_counts[client_id], 86400)
    
    return {
        "requests_last_minute": len([ts for ts in _request_counts[client_id] if ts > current_time - 60]),
        "requests_last_hour": len([ts for ts in _request_counts[client_id] if ts > current_time - 3600]),
        "requests_last_day": len([ts for ts in _request_counts[client_id] if ts > current_time - 86400]),
        "images_last_hour": len([ts for ts in _image_counts[client_id] if ts > current_time - 3600]),
        "images_last_day": len([ts for ts in _image_counts[client_id] if ts > current_time - 86400]),
        "api_calls_today": _api_call_count["count"],
        "limits": {
            "requests_per_minute": MAX_REQUESTS_PER_MINUTE,
            "requests_per_hour": MAX_REQUESTS_PER_HOUR,
            "requests_per_day": MAX_REQUESTS_PER_DAY,
            "images_per_hour": MAX_IMAGE_UPLOADS_PER_HOUR,
            "images_per_day": MAX_IMAGE_UPLOADS_PER_DAY,
            "api_calls_per_day": MAX_DAILY_API_CALLS,
        }
    }

