#!/bin/bash
# Test the chat-service container locally
# This script builds and runs the Docker container exactly as it would run in the cloud,
# ensuring local testing matches production behavior.

set -e

# Configuration
PROJECT_ID="${PROJECT_ID:-fabled-rookery-476623-g5}"
SERVICE_NAME="chat-service"
IMAGE_TAG="${IMAGE_TAG:-latest}"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}:${IMAGE_TAG}"
LOCAL_IMAGE="chat-service:local"

# Load environment variables from .env file if it exists
if [ -f .env ]; then
    echo "Loading environment variables from .env file..."
    set -a
    source .env
    set +a
fi

# Build the Docker image (always rebuild to ensure latest changes)
echo "Building local Docker image: ${LOCAL_IMAGE}"
docker build -t "${LOCAL_IMAGE}" .

# Create var directory for database persistence if it doesn't exist
mkdir -p var

# Create certs directory and generate self-signed SSL certificate if it doesn't exist
mkdir -p certs
if [ ! -f certs/server.crt ] || [ ! -f certs/server.key ]; then
    echo "Generating self-signed SSL certificate..."
    openssl req -x509 -newkey rsa:4096 -nodes \
        -keyout certs/server.key \
        -out certs/server.crt \
        -days 365 \
        -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost" \
        2>/dev/null || {
        echo "⚠️  Error: openssl not found. Please install openssl to generate SSL certificates."
        echo "   On macOS: brew install openssl"
        echo "   On Ubuntu/Debian: sudo apt-get install openssl"
        exit 1
    }
    echo "✓ SSL certificate generated in certs/"
fi

# Set environment variables with defaults where appropriate
export TASKS_CLIENT_ID="${TASKS_CLIENT_ID:-}"
export TASKS_CLIENT_SECRET="${TASKS_CLIENT_SECRET:-}"
export TASKS_REFRESH_TOKEN="${TASKS_REFRESH_TOKEN:-}"
export OAUTH_CLIENT_ID="${OAUTH_CLIENT_ID:-}"
export OAUTH_CLIENT_SECRET="${OAUTH_CLIENT_SECRET:-}"
export OAUTH_REDIRECT_URI="${OAUTH_REDIRECT_URI:-https://localhost:8080/auth/callback}"
export SESSION_SECRET="${SESSION_SECRET:-dev-secret-key-change-in-production}"
export DATABASE_URL="${DATABASE_URL:-sqlite:///./var/chat_tokens.db}"

# Check for required environment variables
missing_vars=()
if [ -z "${TASKS_CLIENT_ID}" ]; then
    missing_vars+=("TASKS_CLIENT_ID")
fi
if [ -z "${TASKS_CLIENT_SECRET}" ]; then
    missing_vars+=("TASKS_CLIENT_SECRET")
fi
if [ -z "${TASKS_REFRESH_TOKEN}" ]; then
    missing_vars+=("TASKS_REFRESH_TOKEN")
fi
if [ -z "${OAUTH_CLIENT_ID}" ]; then
    missing_vars+=("OAUTH_CLIENT_ID")
fi
if [ -z "${OAUTH_CLIENT_SECRET}" ]; then
    missing_vars+=("OAUTH_CLIENT_SECRET")
fi

if [ ${#missing_vars[@]} -gt 0 ]; then
    echo "⚠️  Warning: Missing required environment variables:"
    printf '   - %s\n' "${missing_vars[@]}"
    echo ""
    echo "Set these in your environment or create a .env file with:"
    echo "  TASKS_CLIENT_ID=your-google-client-id"
    echo "  TASKS_CLIENT_SECRET=your-google-client-secret"
    echo "  TASKS_REFRESH_TOKEN=your-google-refresh-token"
    echo "  OAUTH_CLIENT_ID=your-slack-client-id"
    echo "  OAUTH_CLIENT_SECRET=your-slack-client-secret"
    echo "  OAUTH_REDIRECT_URI=https://localhost:8080/auth/callback"
    echo ""
    echo "The service will start but may not function correctly without these variables."
    echo ""
fi

echo "Starting chat-service container locally..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Service URL:        https://localhost:8080"
echo "Health check:       https://localhost:8080/health"
echo "API docs:           https://localhost:8080/docs"
echo "Auth login:         https://localhost:8080/auth/login"
echo ""
echo "⚠️  Note: Using self-signed certificate. Your browser will show a security warning."
echo "   Click 'Advanced' and 'Proceed to localhost' to continue."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Press Ctrl+C to stop the container"
echo ""

# Run the container with all environment variables and volume mounts
# The database is mounted as a volume to persist data between runs
# SSL certificates are mounted to enable HTTPS
docker run --rm -it \
    -p 8080:8080 \
    -v "$(pwd)/var:/app/var" \
    -v "$(pwd)/certs:/app/certs" \
    -e TASKS_CLIENT_ID="${TASKS_CLIENT_ID}" \
    -e TASKS_CLIENT_SECRET="${TASKS_CLIENT_SECRET}" \
    -e TASKS_REFRESH_TOKEN="${TASKS_REFRESH_TOKEN}" \
    -e OAUTH_CLIENT_ID="${OAUTH_CLIENT_ID}" \
    -e OAUTH_CLIENT_SECRET="${OAUTH_CLIENT_SECRET}" \
    -e OAUTH_REDIRECT_URI="${OAUTH_REDIRECT_URI}" \
    -e SESSION_SECRET="${SESSION_SECRET}" \
    -e DATABASE_URL="${DATABASE_URL}" \
    "${LOCAL_IMAGE}"

