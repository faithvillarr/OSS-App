# Terraform Infrastructure for Chat Service

This directory contains Terraform configuration for deploying the Chat Service to Google Cloud Run.

## Prerequisites

1. Google Cloud Project with billing enabled
2. Cloud Run API enabled
3. Terraform >= 1.0 installed
4. Google Cloud SDK (`gcloud`) installed and authenticated
5. Docker image built and pushed to Google Container Registry or Artifact Registry

## Setup

1. **Configure Terraform variables:**

   Create a `terraform.tfvars` file (or use environment variables):

   ```hcl
   project_id = "your-gcp-project-id"
   region     = "us-central1"
   image      = "gcr.io/your-project-id/chat-service:latest"
   
   tasks_client_id     = "your-client-id"
   tasks_client_secret = "your-client-secret"
   tasks_refresh_token = "your-refresh-token"
   session_secret      = "your-session-secret"  # Optional, will be auto-generated if not provided
   ```

2. **Initialize Terraform:**

   ```bash
   cd terraform
   terraform init
   ```

3. **Review the deployment plan:**

   ```bash
   terraform plan
   ```

4. **Deploy the service:**

   ```bash
   terraform apply
   ```

5. **Get the service URL:**

   ```bash
   terraform output service_url
   ```

## Building and Pushing Docker Image

Before deploying, you need to build and push the Docker image:

```bash
# Build the image
docker build -t gcr.io/YOUR_PROJECT_ID/chat-service:latest .

# Push to Google Container Registry
docker push gcr.io/YOUR_PROJECT_ID/chat-service:latest
```

Or use Artifact Registry:

```bash
# Build the image
docker build -t us-central1-docker.pkg.dev/YOUR_PROJECT_ID/REPO_NAME/chat-service:latest .

# Push to Artifact Registry
docker push us-central1-docker.pkg.dev/YOUR_PROJECT_ID/REPO_NAME/chat-service:latest
```

## Variables

See `variables.tf` for all available variables. Key variables:

- `project_id` (required): GCP Project ID
- `image` (required): Container image URL
- `region` (optional): GCP region (default: us-central1)
- `tasks_client_id` (required): Google Tasks OAuth Client ID
- `tasks_client_secret` (required): Google Tasks OAuth Client Secret
- `tasks_refresh_token` (required): Google Tasks OAuth Refresh Token
- `allow_unauthenticated` (optional): Allow public access (default: true)

## Outputs

- `service_url`: HTTPS URL of the deployed service
- `service_name`: Name of the Cloud Run service
- `service_location`: Location of the service

## HTTPS

Cloud Run automatically provides HTTPS with managed certificates. The service URL will be:
`https://SERVICE_NAME-HASH-REGION.a.run.app`

## Cleanup

To destroy the infrastructure:

```bash
terraform destroy
```

## Service Identity

This Terraform configuration sets up a **service account** that Cloud Run uses as its **service identity**. This allows your service to call Google Cloud APIs automatically.

**Important**: 
- The service account is automatically created and assigned to your Cloud Run service
- You can grant additional IAM roles via the `service_account_roles` variable
- See [SERVICE_IDENTITY_SETUP.md](./SERVICE_IDENTITY_SETUP.md) for detailed documentation

To grant permissions, add roles to `terraform.tfvars`:

```hcl
service_account_roles = [
  "roles/storage.objectViewer",
  "roles/pubsub.publisher",
]
```

## Notes

- The service automatically scales based on traffic (min 0, max 10 instances by default)
- Environment variables are set securely in the Cloud Run service
- Session secret is auto-generated if not provided
- The service runs on port 8080 (Cloud Run default)
- A dedicated service account is created for service identity (recommended security practice)

