# ==============================================================================
# Multi-stage Slim Python Dockerfile for Render Free Tier (< 250 MB RAM Budget)
# Base: python:3.11-slim-bookworm
# Excludes development & testing dependencies for minimal image footprint
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Build & wheels generation
# ------------------------------------------------------------------------------
FROM python:3.11-slim-bookworm AS builder

# Prevent Python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /install

# Install essential build dependencies for C extensions (asyncpg / bcrypt)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Exclude test and development dependencies (pytest, pytest-asyncio) for lean production image
RUN grep -v -E '^(pytest|pytest-asyncio)' requirements.txt > /tmp/requirements-prod.txt && \
    pip install --no-cache-dir --prefix=/install -r /tmp/requirements-prod.txt

# ------------------------------------------------------------------------------
# Stage 2: Final Lightweight Runtime Container
# ------------------------------------------------------------------------------
FROM python:3.11-slim-bookworm AS runner

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8000

WORKDIR /app

# Install runtime postgres client library and curl for health check
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder stage
COPY --from=builder /install /usr/local

# Copy application source code
COPY . /app

# Strip tests and cache artifacts from production image to ensure minimal container size
RUN rm -rf /app/tests /app/.pytest_cache /app/.ruff_cache

# Non-root user for production security hardening
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Health check matching Render/cloud specifications (/api/v1/health with /health fallback)
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/api/v1/health || curl -f http://localhost:${PORT:-8000}/health || exit 1

# Start uvicorn with a single worker to respect the strictly under 250 MB RAM limit
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
