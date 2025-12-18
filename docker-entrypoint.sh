#!/bin/sh
# Entrypoint script for chat service container
# Enables HTTPS if SSL certificates are available, otherwise falls back to HTTP

if [ -f /app/certs/server.key ] && [ -f /app/certs/server.crt ]; then
    echo "Starting with HTTPS..."
    exec uvicorn main_service.app:app --host 0.0.0.0 --port 8080 \
        --ssl-keyfile /app/certs/server.key \
        --ssl-certfile /app/certs/server.crt
else
    echo "Starting with HTTP (no SSL certificates found)..."
    exec uvicorn main_service.app:app --host 0.0.0.0 --port 8080
fi

