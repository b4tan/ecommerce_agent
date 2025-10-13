# syntax=docker/dockerfile:1
FROM python:3.11-slim

# 1) System deps (add others as your pip deps require)
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential \
      libffi-dev \
      libsqlite3-0 \
      curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 2) Copy only requirements first (better caching)
COPY requirements.txt .

# Optional: use a pip cache to speed up local builds:
RUN pip install --no-cache-dir -r requirements.txt

# 3) Copy your code and data
COPY backend/  ./backend/
COPY services/ ./services/
COPY data/     ./data/

# 4) Python & runtime env
ENV PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 5) Non-root user
RUN useradd -ms /bin/bash appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8001

CMD ["sh","-c","uvicorn backend.gateway.app:app --host 0.0.0.0 --port ${PORT:-8001}"]
