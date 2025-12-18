#!/bin/bash
# Setup script for Google Cloud authentication and Terraform prerequisites

set -e

echo "🔧 Google Cloud Setup for Terraform"
echo "===================================="
echo ""

# Ensure gcloud is in PATH
export PATH=/opt/homebrew/share/google-cloud-sdk/bin:"$PATH"

# Check if gcloud is available
if ! command -v gcloud &> /dev/null; then
    echo "❌ Error: gcloud not found. Please install Google Cloud SDK first."
    exit 1
fi

echo "✅ gcloud CLI is installed"
echo ""

# Get project ID from argument or use default
PROJECT_ID="${1:-sde-proj-472400}"

# List available projects
echo "📋 Available GCP Projects:"
gcloud projects list
echo ""

# Verify project exists
if ! gcloud projects describe "$PROJECT_ID" &> /dev/null; then
    echo "❌ Error: Project '$PROJECT_ID' not found or you don't have access"
    echo "   Available projects are listed above"
    exit 1
fi

# Set the project
echo ""
echo "🔧 Setting default project to: $PROJECT_ID"
gcloud config set project "$PROJECT_ID"

# Enable required APIs
echo ""
echo "🔧 Enabling required Google Cloud APIs..."
gcloud services enable run.googleapis.com
gcloud services enable cloudresourcemanager.googleapis.com
gcloud services enable iam.googleapis.com
gcloud services enable artifactregistry.googleapis.com

echo ""
echo "✅ APIs enabled successfully"
echo ""

# Set up Application Default Credentials
echo "🔐 Setting up Application Default Credentials for Terraform..."
echo "   (This will open a browser for authentication)"
gcloud auth application-default login

echo ""
echo "✅ Setup complete!"
echo ""
echo "📝 Next steps:"
echo "   1. Create a terraform.tfvars file in the terraform/ directory"
echo "   2. Set your project_id and other required variables"
echo "   3. Run 'terraform init' in the terraform/ directory"
echo "   4. Run 'terraform plan' to review changes"
echo "   5. Run 'terraform apply' to deploy"
echo ""

