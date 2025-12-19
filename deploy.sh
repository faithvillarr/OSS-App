#!/bin/bash
# Complete deployment script for main_service to Google Cloud Run

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="${PROJECT_ID:-fabled-rookery-476623-g5}"
SERVICE_NAME="main-service"
REGION="${REGION:-us-central1}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}:${IMAGE_TAG}"

# Secret names
DISCORD_BOT_TOKEN_SECRET="discord-bot-token"
DISCORD_CHANNEL_ID_SECRET="discord-channel-id"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  main_service Deployment Script${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Function to print status
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Step 1: Check prerequisites
echo -e "${BLUE}Step 1: Checking prerequisites...${NC}"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    print_error "gcloud CLI is not installed. Please install it first."
    exit 1
fi
print_status "gcloud CLI found"

# Check if docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install it first."
    exit 1
fi
print_status "Docker found"

# Check if terraform is installed
if ! command -v terraform &> /dev/null; then
    print_error "Terraform is not installed. Please install it first."
    exit 1
fi
print_status "Terraform found"

# Check authentication
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    print_warning "Not authenticated with gcloud. Please authenticate..."
    gcloud auth login
    gcloud auth application-default login
fi
print_status "Authenticated with gcloud"

# Set project
gcloud config set project "$PROJECT_ID" 2>/dev/null || true
print_status "Using project: $PROJECT_ID"

echo ""

# Step 2: Enable required APIs
echo -e "${BLUE}Step 2: Enabling required APIs...${NC}"

APIS=(
    "run.googleapis.com"
    "secretmanager.googleapis.com"
    "monitoring.googleapis.com"
    "containerregistry.googleapis.com"
)

for api in "${APIS[@]}"; do
    if gcloud services list --enabled --project="$PROJECT_ID" --filter="name:$api" --format="value(name)" | grep -q "$api"; then
        print_status "$api is already enabled"
    else
        echo "Enabling $api..."
        gcloud services enable "$api" --project="$PROJECT_ID" || true
        print_status "$api enabled"
    fi
done

echo ""

# Step 3: Handle secrets
echo -e "${BLUE}Step 3: Setting up Secret Manager secrets...${NC}"

# Check if secrets already exist
BOT_TOKEN_EXISTS=$(gcloud secrets list --project="$PROJECT_ID" --filter="name:$DISCORD_BOT_TOKEN_SECRET" --format="value(name)" 2>/dev/null || echo "")
CHANNEL_ID_EXISTS=$(gcloud secrets list --project="$PROJECT_ID" --filter="name:$DISCORD_CHANNEL_ID_SECRET" --format="value(name)" 2>/dev/null || echo "")

if [ -n "$BOT_TOKEN_EXISTS" ] && [ -n "$CHANNEL_ID_EXISTS" ]; then
    print_status "Secrets already exist: $DISCORD_BOT_TOKEN_SECRET, $DISCORD_CHANNEL_ID_SECRET"
    echo "Skipping secret creation. If you need to update secrets, do it manually:"
    echo "  echo -n 'NEW_TOKEN' | gcloud secrets versions add $DISCORD_BOT_TOKEN_SECRET --data-file=-"
else
    echo "Secrets need to be created. Please provide the following:"
    
    if [ -z "$BOT_TOKEN_EXISTS" ]; then
        read -sp "Enter Discord Bot Token: " DISCORD_BOT_TOKEN
        echo ""
        if [ -z "$DISCORD_BOT_TOKEN" ]; then
            print_error "Discord Bot Token cannot be empty"
            exit 1
        fi
        
        echo -n "$DISCORD_BOT_TOKEN" | gcloud secrets create "$DISCORD_BOT_TOKEN_SECRET" \
            --data-file=- \
            --project="$PROJECT_ID" \
            --replication-policy="automatic" 2>/dev/null || {
            print_warning "Secret $DISCORD_BOT_TOKEN_SECRET might already exist or creation failed"
        }
        print_status "Created secret: $DISCORD_BOT_TOKEN_SECRET"
    fi
    
    if [ -z "$CHANNEL_ID_EXISTS" ]; then
        read -p "Enter Discord Channel ID: " DISCORD_CHANNEL_ID
        if [ -z "$DISCORD_CHANNEL_ID" ]; then
            print_error "Discord Channel ID cannot be empty"
            exit 1
        fi
        
        echo -n "$DISCORD_CHANNEL_ID" | gcloud secrets create "$DISCORD_CHANNEL_ID_SECRET" \
            --data-file=- \
            --project="$PROJECT_ID" \
            --replication-policy="automatic" 2>/dev/null || {
            print_warning "Secret $DISCORD_CHANNEL_ID_SECRET might already exist or creation failed"
        }
        print_status "Created secret: $DISCORD_CHANNEL_ID_SECRET"
    fi
fi

echo ""

# Step 4: Check for Terraform variables
echo -e "${BLUE}Step 4: Checking Terraform configuration...${NC}"

if [ ! -f "terraform/terraform.tfvars" ]; then
    print_warning "terraform/terraform.tfvars not found"
    echo "Creating terraform.tfvars from example..."
    
    if [ ! -f "terraform/terraform.tfvars.example" ]; then
        print_error "terraform/terraform.tfvars.example not found. Please create terraform.tfvars manually."
        exit 1
    fi
    
    cp terraform/terraform.tfvars.example terraform/terraform.tfvars
    
    # Update with current values
    sed -i.bak "s|your-gcp-project-id|$PROJECT_ID|g" terraform/terraform.tfvars
    sed -i.bak "s|gcr.io/your-project-id/chat-service:latest|$IMAGE_NAME|g" terraform/terraform.tfvars
    sed -i.bak "s|chat-service|$SERVICE_NAME|g" terraform/terraform.tfvars
    rm terraform/terraform.tfvars.bak 2>/dev/null || true
    
    print_warning "Please edit terraform/terraform.tfvars and add your Google Tasks OAuth credentials:"
    echo "  - tasks_client_id"
    echo "  - tasks_client_secret"
    echo "  - tasks_refresh_token"
    echo ""
    read -p "Press Enter after you've updated terraform.tfvars, or Ctrl+C to cancel..."
else
    print_status "terraform.tfvars found"
    
    # Update image if it's different
    CURRENT_IMAGE=$(grep "^image" terraform/terraform.tfvars | cut -d'"' -f2 || echo "")
    if [ "$CURRENT_IMAGE" != "$IMAGE_NAME" ]; then
        print_warning "Updating image in terraform.tfvars to: $IMAGE_NAME"
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            sed -i.bak "s|^image.*|image = \"$IMAGE_NAME\"|g" terraform/terraform.tfvars
        else
            # Linux
            sed -i "s|^image.*|image = \"$IMAGE_NAME\"|g" terraform/terraform.tfvars
        fi
        rm terraform/terraform.tfvars.bak 2>/dev/null || true
    fi
fi

echo ""

# Step 5: Build and push Docker images
echo -e "${BLUE}Step 5: Building and pushing Docker images...${NC}"

# Build and push main service image
echo "Building main service Docker image: $IMAGE_NAME"
docker build --platform linux/amd64 -t "$IMAGE_NAME" . || {
    print_error "Docker build failed"
    exit 1
}
print_status "Main service Docker image built successfully"

# Configure Docker authentication
gcloud auth configure-docker --quiet 2>/dev/null || true

echo "Pushing main service image to GCR: $IMAGE_NAME"
docker push "$IMAGE_NAME" || {
    print_error "Docker push failed"
    exit 1
}
print_status "Main service Docker image pushed successfully"

# Optional: Build and push OpenTelemetry Collector image with config
# Note: The Terraform config uses the official collector image by default.
# Building a custom image with config baked in is optional but recommended for production.
COLLECTOR_IMAGE_NAME="gcr.io/${PROJECT_ID}/otel-collector:${IMAGE_TAG}"
echo ""
read -p "Build custom OpenTelemetry Collector image with config? (y/N): " BUILD_COLLECTOR
if [[ "$BUILD_COLLECTOR" =~ ^[Yy]$ ]]; then
    echo "Building OpenTelemetry Collector image: $COLLECTOR_IMAGE_NAME"
    docker build --platform linux/amd64 -f Dockerfile.otel-collector -t "$COLLECTOR_IMAGE_NAME" . || {
        print_error "Collector Docker build failed"
        exit 1
    }
    print_status "Collector Docker image built successfully"
    
    echo "Pushing collector image to GCR: $COLLECTOR_IMAGE_NAME"
    docker push "$COLLECTOR_IMAGE_NAME" || {
        print_error "Collector Docker push failed"
        exit 1
    }
    print_status "Collector Docker image pushed successfully"
    
    # Automatically update terraform.tfvars with the collector image
    if [ -f "terraform/terraform.tfvars" ]; then
        if grep -q "^otel_collector_image" terraform/terraform.tfvars; then
            # Update existing otel_collector_image line
            if [[ "$OSTYPE" == "darwin"* ]]; then
                sed -i.bak "s|^otel_collector_image.*|otel_collector_image = \"$COLLECTOR_IMAGE_NAME\"|g" terraform/terraform.tfvars
            else
                sed -i "s|^otel_collector_image.*|otel_collector_image = \"$COLLECTOR_IMAGE_NAME\"|g" terraform/terraform.tfvars
            fi
            rm terraform/terraform.tfvars.bak 2>/dev/null || true
        else
            # Add otel_collector_image line
            echo "" >> terraform/terraform.tfvars
            echo "otel_collector_image = \"$COLLECTOR_IMAGE_NAME\"" >> terraform/terraform.tfvars
        fi
        print_status "Updated terraform.tfvars with collector image: $COLLECTOR_IMAGE_NAME"
    else
        print_warning "terraform.tfvars not found. Please manually add: otel_collector_image = \"$COLLECTOR_IMAGE_NAME\""
    fi
    echo ""
else
    print_warning "Using official OpenTelemetry Collector image (otel/opentelemetry-collector-contrib:latest)"
    print_warning "WARNING: The official image does NOT include a config file and will fail to start!"
    print_warning "You MUST build a custom collector image for the sidecar to work properly."
    echo ""
    read -p "Do you want to build the collector image now? (y/N): " BUILD_NOW
    if [[ "$BUILD_NOW" =~ ^[Yy]$ ]]; then
        echo "Building OpenTelemetry Collector image: $COLLECTOR_IMAGE_NAME"
        docker build --platform linux/amd64 -f Dockerfile.otel-collector -t "$COLLECTOR_IMAGE_NAME" . || {
            print_error "Collector Docker build failed"
            exit 1
        }
        print_status "Collector Docker image built successfully"
        
        echo "Pushing collector image to GCR: $COLLECTOR_IMAGE_NAME"
        docker push "$COLLECTOR_IMAGE_NAME" || {
            print_error "Collector Docker push failed"
            exit 1
        }
        print_status "Collector Docker image pushed successfully"
        
        # Update terraform.tfvars
        if [ -f "terraform/terraform.tfvars" ]; then
            if grep -q "^otel_collector_image" terraform/terraform.tfvars; then
                if [[ "$OSTYPE" == "darwin"* ]]; then
                    sed -i.bak "s|^otel_collector_image.*|otel_collector_image = \"$COLLECTOR_IMAGE_NAME\"|g" terraform/terraform.tfvars
                else
                    sed -i "s|^otel_collector_image.*|otel_collector_image = \"$COLLECTOR_IMAGE_NAME\"|g" terraform/terraform.tfvars
                fi
                rm terraform/terraform.tfvars.bak 2>/dev/null || true
            else
                echo "" >> terraform/terraform.tfvars
                echo "otel_collector_image = \"$COLLECTOR_IMAGE_NAME\"" >> terraform/terraform.tfvars
            fi
            print_status "Updated terraform.tfvars with collector image: $COLLECTOR_IMAGE_NAME"
        fi
    fi
fi

echo ""

# Step 6: Deploy with Terraform
echo -e "${BLUE}Step 6: Deploying with Terraform...${NC}"

cd terraform

# Initialize Terraform if needed
if [ ! -d ".terraform" ]; then
    echo "Initializing Terraform..."
    terraform init || {
        print_error "Terraform initialization failed"
        exit 1
    }
    print_status "Terraform initialized"
fi

# Plan
echo "Running terraform plan..."
terraform plan -out=tfplan || {
    print_error "Terraform plan failed"
    exit 1
}

# Ask for confirmation
echo ""
read -p "Review the plan above. Apply these changes? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    print_warning "Deployment cancelled"
    rm -f tfplan
    exit 0
fi

# Apply
echo "Applying Terraform configuration..."
terraform apply tfplan || {
    print_error "Terraform apply failed"
    rm -f tfplan
    exit 1
}

rm -f tfplan
print_status "Terraform apply completed"

cd ..

echo ""

# Step 7: Display deployment information
echo -e "${BLUE}Step 7: Deployment Summary${NC}"
echo ""

cd terraform
SERVICE_URL=$(terraform output -raw service_url 2>/dev/null || echo "N/A")
cd ..

if [ "$SERVICE_URL" != "N/A" ]; then
    print_status "Service URL: $SERVICE_URL"
else
    print_warning "Could not retrieve service URL. Check with: terraform output service_url"
fi

echo ""
print_status "Deployment completed successfully!"
echo ""
echo -e "${GREEN}Next steps:${NC}"
echo "1. View main service logs: gcloud run services logs read $SERVICE_NAME --region=$REGION --project=$PROJECT_ID"
echo "2. View collector logs: gcloud run services logs read $SERVICE_NAME --region=$REGION --project=$PROJECT_ID --container=otel-collector"
echo "3. View metrics: https://console.cloud.google.com/monitoring/metrics-explorer?project=$PROJECT_ID"
echo "4. Check service status: gcloud run services describe $SERVICE_NAME --region=$REGION --project=$PROJECT_ID"
echo ""
echo -e "${BLUE}OpenTelemetry Collector:${NC}"
echo "The service now includes an OpenTelemetry Collector sidecar container."
echo "Metrics are exported via OTLP and appear in GCP Cloud Monitoring."
echo ""
echo -e "${BLUE}To view telemetry metrics:${NC}"
echo "1. Go to: https://console.cloud.google.com/monitoring/metrics-explorer?project=$PROJECT_ID"
echo "2. Search for: custom.googleapis.com/opentelemetry/main_service/message_processing_total"
echo "3. Or use the view-telemetry.sh script: ./view-telemetry.sh"
echo "4. Available metrics:"
echo "   - message_processing_duration (End-to-end latency from message processing start to response posting)"
echo "   - message_processing_total{status=\"success\"} (Count of successful message processing calls)"
echo "   - message_processing_total{status=\"failure\"} (Count of failed message processing calls)"
echo ""
echo "   Success rate = message_processing_total{status=\"success\"} / message_processing_total"
echo "   Failure rate = message_processing_total{status=\"failure\"} / message_processing_total"
echo "   Rates can be calculated in GCP Cloud Monitoring using MQL or the UI"
echo ""
echo -e "${YELLOW}Note:${NC} If this is an update to an existing deployment, Terraform will"
echo "update the Cloud Run service with the new sidecar container configuration."
echo "Cloud Run will perform a rolling update with minimal downtime."
echo ""
