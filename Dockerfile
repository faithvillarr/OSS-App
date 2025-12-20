# Multi-stage Dockerfile for Chat Service
FROM python:3.12-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy workspace files
COPY pyproject.toml ./
COPY src/ ./src/
# Note: uv.lock is optional - if it doesn't exist, uv sync will generate it

# Install dependencies (--all-packages ensures workspace members are installed)
# Use --frozen only if uv.lock exists, otherwise sync without it
RUN if [ -f uv.lock ]; then \
        uv sync --frozen --no-dev --all-packages; \
    else \
        uv sync --no-dev --all-packages; \
    fi

# Runtime stage
FROM python:3.12-slim

# Install uv for runtime
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/pyproject.toml ./
COPY --from=builder /app/src/ ./src/

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# Create directory for SSL certificates
RUN mkdir -p /app/certs

# Copy entrypoint script
COPY docker-entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Expose port
EXPOSE 8080

# Run the application
ENTRYPOINT ["/app/entrypoint.sh"]
