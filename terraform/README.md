# Terraform Infrastructure for main_service

This directory contains Terraform configuration for deploying the main_service Discord polling service to Google Cloud Run with Secret Manager integration and Cloud Monitoring telemetry.

## Quick Start: Automated Deployment

**The recommended way to deploy is using the automated deployment script:**

1. **Configure Terraform variables:**
   ```bash
   cd terraform
   cp terraform.tfvars.example terraform.tfvars
   ```

2. **Edit `terraform.tfvars`** and fill in all required values (see [Configuration](#configuration) below)

3. **Run the deployment script from the project root:**
   ```bash
   ./deploy.sh
   ```

   The script automates:
   - Prerequisite checks (gcloud, docker, terraform)
   - GCP API enabling
   - Secret Manager secret creation
   - Docker image building and pushing
   - Terraform initialization and deployment

4. **Get the service URL:**
   ```bash
   cd terraform
   terraform output service_url
   ```

For detailed information about the deployment script, see the [root README.md](../README.md#deployment).

## Manual Deployment

If you prefer to deploy manually or need more control:

### Prerequisites

1. Google Cloud Project with billing enabled
2. Required APIs enabled:
   - Cloud Run API
   - Secret Manager API
   - Cloud Monitoring API
   - Container Registry API (or Artifact Registry API)
3. Terraform >= 1.0 installed
4. Google Cloud SDK (`gcloud`) installed and authenticated
5. Docker installed and running

### Configuration

1. **Copy the example variables file:**
   ```bash
   cd terraform
   cp terraform.tfvars.example terraform.tfvars
   ```

2. **Edit `terraform.tfvars`** and fill in all required values:

   ```hcl
   project_id = "your-gcp-project-id"
   region     = "us-central1"
   image      = "gcr.io/your-project-id/main-service:latest"
   
   # Google Tasks OAuth credentials (REQUIRED)
   tasks_client_id     = "your-client-id.apps.googleusercontent.com"
   tasks_client_secret = "your-client-secret"
   tasks_refresh_token = "your-refresh-token"
   
   # OpenAI API key (REQUIRED)
   openai_api_key = "your-openai-api-key-here"
   
   # Optional: Service configuration
   # service_name         = "main-service"
   # min_instances        = 1
   # max_instances        = 10
   ```

   **Important**: You must fill in all the required values before deploying. The deployment will fail if any required variables are missing.

3. **Set up Secret Manager secrets** (if not using `deploy.sh`):
   ```bash
   # Discord bot token
   echo -n "your-discord-bot-token" | gcloud secrets create discord-bot-token \
     --data-file=- --project=your-project-id
   
   # Discord channel ID
   echo -n "your-discord-channel-id" | gcloud secrets create discord-channel-id \
     --data-file=- --project=your-project-id
   ```

4. **Build and push Docker image:**
   ```bash
   # From project root
   docker build --platform linux/amd64 -t gcr.io/YOUR_PROJECT_ID/main-service:latest .
   gcloud auth configure-docker
   docker push gcr.io/YOUR_PROJECT_ID/main-service:latest
   ```

5. **Initialize Terraform:**
   ```bash
   cd terraform
   terraform init
   ```

6. **Review the deployment plan:**
   ```bash
   terraform plan
   ```

7. **Deploy the service:**
   ```bash
   terraform apply
   ```

8. **Get the service URL:**
   ```bash
   terraform output service_url
   ```

## Variables

See `variables.tf` for all available variables. Key variables:

### Required Variables

- **`project_id`**: GCP Project ID
- **`image`**: Container image URL (e.g., `gcr.io/your-project-id/main-service:latest`)
- **`tasks_client_id`**: Google Tasks OAuth Client ID (format: `xxx.apps.googleusercontent.com`)
- **`tasks_client_secret`**: Google Tasks OAuth Client Secret
- **`tasks_refresh_token`**: Google Tasks OAuth Refresh Token
- **`openai_api_key`**: OpenAI API key for AI operations

### Optional Variables

- **`region`**: GCP region (default: `us-central1`)
- **`service_name`**: Cloud Run service name (default: `main-service`)
- **`min_instances`**: Minimum instances (default: `1` - required for polling service)
- **`max_instances`**: Maximum instances (default: `10`)
- **`discord_bot_token_secret_name`**: Secret Manager secret name for Discord bot token (default: `discord-bot-token`)
- **`discord_channel_id_secret_name`**: Secret Manager secret name for Discord channel ID (default: `discord-channel-id`)
- **`create_secrets`**: Whether Terraform should create secrets (default: `false` - use `deploy.sh` instead)

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

- `DISCORD_BOT_TOKEN`: From Secret Manager secret (name: `discord-bot-token` by default)
- `DISCORD_CHANNEL_ID`: From Secret Manager secret (name: `discord-channel-id` by default)

The service account is automatically granted Secret Manager access.

**Setting up secrets:**

If using `deploy.sh`, secrets are created automatically. If deploying manually:

```bash
# Discord bot token
echo -n "your-discord-bot-token" | gcloud secrets create discord-bot-token \
  --data-file=- --project=your-project-id \
  --replication-policy=automatic

# Discord channel ID
echo -n "your-discord-channel-id" | gcloud secrets create discord-channel-id \
  --data-file=- --project=your-project-id \
  --replication-policy=automatic
```

**Updating secrets:**

```bash
# Update Discord bot token
echo -n "new-token" | gcloud secrets versions add discord-bot-token \
  --data-file=- --project=your-project-id

# Update Discord channel ID
echo -n "new-channel-id" | gcloud secrets versions add discord-channel-id \
  --data-file=- --project=your-project-id
```

## Important Notes

- **The service is a long-running polling service** (not HTTP-based), so `min_instances` is set to 1 to ensure continuous polling
- **Environment variables are set securely via Secret Manager** - never hardcode secrets in Terraform variables
- **A dedicated service account is created** for service identity (recommended security practice)
- **Telemetry is automatically enabled** when running on Cloud Run via OpenTelemetry Collector sidecar
- **The `deploy.sh` script** handles most of the setup automatically - use it unless you need manual control

## Troubleshooting

### Terraform apply fails with "variable not set"

Ensure you've copied `terraform.tfvars.example` to `terraform.tfvars` and filled in all required values.

### Docker image not found

Ensure you've built and pushed the Docker image before running `terraform apply`. The `deploy.sh` script handles this automatically.

### Secret Manager access denied

Ensure the service account has the `roles/secretmanager.secretAccessor` role. This is automatically granted by the Terraform configuration.

### Service not polling

- Check that `min_instances` is set to at least 1
- Verify Discord credentials in Secret Manager are correct
- Check Cloud Run logs: `gcloud run services logs read main-service --region=us-central1`

