#!/bin/bash
# Build and push Docker image to Google Container Registry

set -e

# Configuration
PROJECT_ID="${PROJECT_ID:-fabled-rookery-476623-g5}"
SERVICE_NAME="chat-service"
IMAGE_TAG="${IMAGE_TAG:-latest}"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}:${IMAGE_TAG}"

echo "Building Docker image: ${IMAGE_NAME}"

# Build the Docker image
docker build -t "${IMAGE_NAME}" .

echo "Image built successfully!"

# Authenticate with GCP (if not already authenticated)
echo "Checking GCP authentication..."
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "Please authenticate with GCP:"
    gcloud auth login
fi

# Configure Docker to use gcloud as a credential helper
echo "Configuring Docker to use gcloud credential helper..."
gcloud auth configure-docker

# Push the image to GCR
echo "Pushing image to GCR: ${IMAGE_NAME}"
docker push "${IMAGE_NAME}"

echo "✅ Successfully pushed ${IMAGE_NAME}"
echo ""
echo "You can now run: cd terraform && terraform apply"

