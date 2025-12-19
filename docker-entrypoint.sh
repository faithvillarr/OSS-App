#!/bin/sh
# Entrypoint script for Discord message polling service container

echo "Starting Discord message polling service..."
exec python -m main_service.main

