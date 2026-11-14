FROM node:20-alpine AS frontend-builder
WORKDIR /build

# Deterministic package installation
COPY package.json package-lock.json ./
RUN npm ci

# Copy frontend source files
COPY index.html vite.config.js tailwind.config.js postcss.config.js ./
COPY src/ ./src/

# Compile React SPA production bundle
RUN npm run build

# Runtime Stage
FROM python:3.11-slim AS runtime

# System utilities for runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    STATIC_DIR=/app/static \
    ENVIRONMENT=production

# Install Python backend dependencies
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application source
COPY backend/ ./backend

# Copy compiled frontend from builder stage
COPY --from=frontend-builder /build/dist ./static

# Ensure persistent storage volume mount directory exists
RUN mkdir -p /data && chmod 777 /data
VOLUME /data

EXPOSE 8000

# Start ASGI application with shell expansion for dynamic Railway PORT
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --app-dir /app/backend"]
