# ==============================================================================
# ASTRA SENSE – ORBITAL GUARD
# Single-Service Production Container: React Frontend + FastAPI Backend + SQLite
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Frontend Builder (Node.js 20 Alpine)
# ------------------------------------------------------------------------------
FROM node:20-alpine AS frontend-builder
WORKDIR /build

# Install dependencies deterministically
COPY package.json package-lock.json ./
RUN npm ci

# Copy frontend source code & configuration
COPY index.html vite.config.js tailwind.config.js postcss.config.js ./
COPY public/ ./public/
COPY src/ ./src/

# Build production static bundle -> /build/dist
RUN npm run build

# ------------------------------------------------------------------------------
# Stage 2: Production Runtime (Python 3.11 Slim)
# ------------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

# System dependencies: curl for health checks, sqlite3 tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Configure Python execution environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    STATIC_DIR=/app/static \
    ENVIRONMENT=production

# Install Python requirements
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application code
COPY backend/ ./backend

# Copy compiled frontend from Stage 1 into STATIC_DIR
COPY --from=frontend-builder /build/dist ./static

# Ensure persistent storage mount point exists
RUN mkdir -p /data && chmod 777 /data
VOLUME /data

# Railway dynamically assigns $PORT at runtime
EXPOSE 8000

# Container health probe
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Launch ASGI production server using the runtime PORT environment variable
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --app-dir /app/backend"]
