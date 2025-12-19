# Terraform Infrastructure for main_service

This directory contains Terraform configuration for deploying the main_service Discord polling service to Google Cloud Run with Secret Manager integration and Cloud Monitoring telemetry.

**For detailed deployment instructions, see [DEPLOYMENT.md](./DEPLOYMENT.md)**

## Prerequisites

1. Google Cloud Project with billing enabled
2. Required APIs enabled:
   - Cloud Run API
   - Secret Manager API
   - Cloud Monitoring API
   - Container Registry API (or Artifact Registry API)
3. Terraform >= 1.0 installed
4. Google Cloud SDK (`gcloud`) installed and authenticated
5. Docker image built and pushed to Google Container Registry or Artifact Registry

## Setup

1. **Configure Terraform variables:**

   Create a `terraform.tfvars` file (or use environment variables):

   ```hcl
   project_id = "your-gcp-project-id"
   region     = "us-central1"
   service_name = "main-service"
   image      = "gcr.io/your-project-id/main-service:latest"
   
   # Google Tasks OAuth credentials
   tasks_client_id     = "your-client-id"
   tasks_client_secret = "your-client-secret"
   tasks_refresh_token = "your-refresh-token"
   
   # Secret Manager configuration
   create_secrets = false  # Set to true if Terraform should create secrets
   discord_bot_token_secret_name = "discord-bot-token"
   discord_channel_id_secret_name = "discord-channel-id"
   
   # Service configuration
   min_instances = 1  # Required for long-running polling service
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

Use the provided build script:

```bash
./build-and-push.sh
```

Or manually:

```bash
# Build the image
docker build -t gcr.io/YOUR_PROJECT_ID/main-service:latest .

# Push to Google Container Registry
docker push gcr.io/YOUR_PROJECT_ID/main-service:latest
```

## Variables

See `variables.tf` for all available variables. Key variables:

- `project_id` (required): GCP Project ID
- `image` (required): Container image URL
- `region` (optional): GCP region (default: us-central1)
- `service_name` (optional): Cloud Run service name (default: main-service)
- `tasks_client_id` (required): Google Tasks OAuth Client ID
- `tasks_client_secret` (required): Google Tasks OAuth Client Secret
- `tasks_refresh_token` (required): Google Tasks OAuth Refresh Token
- `discord_bot_token_secret_name` (optional): Secret Manager secret name for Discord bot token (default: discord-bot-token)
- `discord_channel_id_secret_name` (optional): Secret Manager secret name for Discord channel ID (default: discord-channel-id)
- `create_secrets` (optional): Whether Terraform should create secrets (default: false)
- `min_instances` (optional): Minimum instances (default: 1 for polling service)
- `max_instances` (optional): Maximum instances (default: 10)

## Outputs

- `service_url`: HTTPS URL of the deployed service
- `service_name`: Name of the Cloud Run service
- `service_location`: Location of the service
- `service_account_email`: Email of the service account
- `discord_bot_token_secret_name`: Name of the Discord bot token secret
- `discord_channel_id_secret_name`: Name of the Discord channel ID secret

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

## Telemetry and Monitoring

The service includes built-in Cloud Monitoring telemetry that tracks:

- **Message Processing Metrics**: Success/failure rates, latency, error types
- **Poll Cycle Metrics**: Cycle duration and frequency
- **Error Tracking**: Categorized by error type

Metrics are automatically sent to Cloud Monitoring. See [DEPLOYMENT.md](./DEPLOYMENT.md) for instructions on setting up monitoring dashboards.

## Secret Manager

Discord credentials are stored in Secret Manager and automatically injected as environment variables:

- `DISCORD_BOT_TOKEN`: From Secret Manager secret
- `DISCORD_CHANNEL_ID`: From Secret Manager secret

The service account is automatically granted Secret Manager access. See [DEPLOYMENT.md](./DEPLOYMENT.md) for secret setup instructions.

## Notes

- The service is a long-running polling service (not HTTP-based)
- Minimum instances is set to 1 to ensure continuous polling
- Environment variables are set securely via Secret Manager
- Session secret is auto-generated if not provided
- A dedicated service account is created for service identity (recommended security practice)
- Telemetry is automatically enabled when running on Cloud Run

