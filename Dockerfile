# ==============================================================================
# Stage 1: Frontend Builder (Svelte + Vite)
# ==============================================================================
FROM node:22-slim AS frontend-builder

ENV NODE_OPTIONS="--tls-max-v1.2"

WORKDIR /app/frontend

# Install pnpm version 9 matching pnpm-lock.yaml
RUN npm install -g pnpm@9

# Install dependencies with frozen lockfile for deterministic builds
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

# Copy frontend source and build static bundle (outputs to ../static/svelte)
COPY frontend/ ./
RUN pnpm run build

# ==============================================================================
# Stage 2: Backend Runtime (Django + Python 3.12 + Gunicorn)
# ==============================================================================
FROM python:3.12-slim-bookworm AS backend

# Configure Python runtime
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

# Install system dependencies (curl for healthchecks, libpq5 for PostgreSQL)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Install official uv binary for ultra-fast and reliable package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Create virtual environment and install Python dependencies
COPY pyproject.toml ./
RUN uv venv $VIRTUAL_ENV && \
    uv pip install --no-cache -r pyproject.toml

# Copy application source code
COPY . /app

# Copy compiled frontend assets from Stage 1 into Django's static directory
COPY --from=frontend-builder /app/static/svelte /app/static/svelte

# Create persistent storage directories and ensure correct permissions
RUN mkdir -p /app/data /app/media /app/staticfiles

# Collect static files with WhiteNoise using build-time dummy settings
RUN DEBUG=False \
    SECRET_KEY=build-time-secret-key-placeholder \
    ALLOWED_HOSTS=* \
    DATABASE_URL=sqlite:///tmp/build_db.sqlite3 \
    python manage.py collectstatic --no-input

# Set up non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app && \
    chmod +x /app/docker-entrypoint.sh

USER appuser

EXPOSE 8000

# Container healthcheck testing the HTTP server response
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -f http://127.0.0.1:8000/ || exit 1

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["gunicorn", "caliber.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]

