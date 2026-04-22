# syntax=docker/dockerfile:1
FROM nvidia/cuda:12.4.0-runtime-ubuntu22.04 AS base

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    python3.11 python3.11-pip python3.11-venv curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps
COPY pyproject.toml ./
RUN python3.11 -m pip install --no-cache-dir -e ".[inference]"

# Copy source
COPY duino_api/ ./duino_api/

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/v1/health || exit 1

EXPOSE 8000

CMD ["python3.11", "-m", "uvicorn", "duino_api.gateway.app:app", \
     "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
