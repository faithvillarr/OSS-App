# Deployment Guide for main_service

This guide walks you through deploying the main_service Discord polling service to Google Cloud Run with Terraform, Secret Manager, and Cloud Monitoring.

## Prerequisites

1. **Google Cloud Project** with billing enabled
2. **Required APIs enabled**:
   - Cloud Run API
   - Secret Manager API
   - Cloud Monitoring API
   - Container Registry API (or Artifact Registry API)

3. **Tools installed**:
   - Terraform >= 1.0
   - Google Cloud SDK (`gcloud`)
   - Docker
   - Bash

4. **Authentication**:
   ```bash
   gcloud auth login
   gcloud auth application-default login
   ```

## Step 1: Enable Required APIs

```bash
gcloud services enable \
  run.googleapis.com \
  secretmanager.googleapis.com \
  monitoring.googleapis.com \
  containerregistry.googleapis.com \
  --project=YOUR_PROJECT_ID
```

## Step 2: Prepare Secrets

You have two options for managing secrets:

### Option A: Create Secrets Manually (Recommended for Production)

Create secrets in Secret Manager before running Terraform:

```bash
# Set your project ID
export PROJECT_ID="your-gcp-project-id"

# Create Discord bot token secret
echo -n "YOUR_DISCORD_BOT_TOKEN" | gcloud secrets create discord-bot-token \
  --data-file=- \
  --project=$PROJECT_ID \
  --replication-policy="automatic"

# Create Discord channel ID secret
echo -n "YOUR_DISCORD_CHANNEL_ID" | gcloud secrets create discord-channel-id \
  --data-file=- \
  --project=$PROJECT_ID \
  --replication-policy="automatic"
```

Then set `create_secrets = false` in your `terraform.tfvars` (or omit the Discord variables).

### Option B: Let Terraform Create Secrets

Set `create_secrets = true` in your `terraform.tfvars` and provide the values:

```hcl
create_secrets = true
discord_bot_token = "YOUR_DISCORD_BOT_TOKEN"
discord_channel_id = "YOUR_DISCORD_CHANNEL_ID"
```

**Note**: This stores secrets in Terraform state. For production, prefer Option A.

## Step 3: Configure Terraform Variables

Create a `terraform.tfvars` file:

```hcl
project_id = "your-gcp-project-id"
region     = "us-central1"
service_name = "main-service"

# Container image (will be set after building)
image = "gcr.io/your-project-id/main-service:latest"

# Google Tasks OAuth credentials
tasks_client_id     = "your-client-id.apps.googleusercontent.com"
tasks_client_secret = "your-client-secret"
tasks_refresh_token = "your-refresh-token"

# Secret Manager configuration
create_secrets = false  # Set to true if Terraform should create secrets
discord_bot_token_secret_name = "discord-bot-token"
discord_channel_id_secret_name = "discord-channel-id"

# Service configuration
min_instances = 1  # Required for long-running polling service
max_instances = 10
cpu           = "1"
memory        = "512Mi"
```

## Step 4: Build and Push Docker Image

From the project root:

```bash
# Set your project ID
export PROJECT_ID="your-gcp-project-id"

# Build and push the image
./build-and-push.sh
```

Or manually:

```bash
export PROJECT_ID="your-gcp-project-id"
export IMAGE_TAG="latest"
export IMAGE_NAME="gcr.io/${PROJECT_ID}/main-service:${IMAGE_TAG}"

docker build -t "${IMAGE_NAME}" .
gcloud auth configure-docker
docker push "${IMAGE_NAME}"
```

Update `terraform.tfvars` with the image URL if it differs from the default.

## Step 5: Initialize Terraform

```bash
cd terraform
terraform init
```

## Step 6: Review Deployment Plan

```bash
terraform plan
```

Review the plan to ensure:
- Service account is created with Secret Manager access
- Cloud Run service is configured correctly
- Secrets are referenced (not created if `create_secrets = false`)
- `min_instances = 1` for the polling service

## Step 7: Deploy Infrastructure

```bash
terraform apply
```

Confirm when prompted. This will:
- Create service account with Secret Manager permissions
- Deploy Cloud Run service
- Configure environment variables from Secret Manager

## Step 8: Verify Deployment

### Check Service Status

```bash
# Get service URL
terraform output service_url

# Check service logs
gcloud run services logs read main-service \
  --region=us-central1 \
  --project=YOUR_PROJECT_ID \
  --limit=50
```

### Verify Secrets Are Loaded

Check logs for:
- "✓ Discord channel ID configured: ..."
- No errors about missing environment variables

### Test the Service

The service should be polling Discord. Check logs to see:
- "Starting polling loop..."
- "Found X new message(s)" when messages arrive

## Step 9: Set Up Monitoring Dashboard

### Access Cloud Monitoring

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Navigate to **Monitoring** > **Dashboards**
3. Create a new dashboard

### Add Metrics

Add the following custom metrics to your dashboard:

1. **Message Processing Duration**:
   - Metric: `custom.googleapis.com/main_service/message_processing_duration`
   - Aggregation: Mean, P50, P95, P99
   - Chart type: Line chart

2. **Message Processing Success/Failure Rate**:
   - Metric: `custom.googleapis.com/main_service/message_processing_total`
   - Group by: `status` label
   - Aggregation: Sum
   - Chart type: Stacked area chart

3. **Error Rate by Type**:
   - Metric: `custom.googleapis.com/main_service/message_processing_errors_total`
   - Group by: `error_type` label
   - Aggregation: Sum
   - Chart type: Bar chart

4. **Poll Cycle Duration**:
   - Metric: `custom.googleapis.com/main_service/poll_cycle_duration`
   - Aggregation: Mean
   - Chart type: Line chart

5. **Poll Cycles Total**:
   - Metric: `custom.googleapis.com/main_service/poll_cycles_total`
   - Aggregation: Sum
   - Chart type: Counter

### Create Alert Policies (Optional)

Set up alerts for:
- High error rate (> 10% failures)
- High latency (P95 > 5 seconds)
- Service downtime (no poll cycles for 5 minutes)

## Monitoring Metrics Reference

### Custom Metrics

| Metric Name | Type | Description |
|------------|------|-------------|
| `custom.googleapis.com/main_service/message_processing_duration` | Histogram | Time to process each message (seconds) |
| `custom.googleapis.com/main_service/message_processing_total` | Counter | Total messages processed (with `status` label: success/failure) |
| `custom.googleapis.com/main_service/message_processing_errors_total` | Counter | Total errors (with `error_type` label) |
| `custom.googleapis.com/main_service/poll_cycle_duration` | Histogram | Time for each poll cycle (seconds) |
| `custom.googleapis.com/main_service/poll_cycles_total` | Counter | Total poll cycles executed |

### Built-in Cloud Run Metrics

- Container CPU usage
- Container memory usage
- Request count
- Request latency
- Container instance count

## Troubleshooting

### Service Won't Start

1. **Check logs**:
   ```bash
   gcloud run services logs read main-service --region=us-central1
   ```

2. **Common issues**:
   - Missing environment variables: Check Secret Manager secrets exist and service account has access
   - Authentication errors: Verify Discord bot token is valid
   - Initialization failures: Check ticket client and AI client initialization in logs

### Metrics Not Appearing

1. **Verify telemetry is enabled**:
   - Check logs for "✓ Telemetry enabled" or "⚠ Telemetry disabled"
   - Ensure `GOOGLE_CLOUD_PROJECT` environment variable is set (Cloud Run sets this automatically)

2. **Check service account permissions**:
   - Service account needs `roles/monitoring.metricWriter` (usually granted automatically to Cloud Run)

3. **Wait a few minutes**: Metrics may take 1-2 minutes to appear in Cloud Monitoring

### Secrets Not Loading

1. **Verify secrets exist**:
   ```bash
   gcloud secrets list --project=YOUR_PROJECT_ID
   ```

2. **Check service account has access**:
   ```bash
   gcloud secrets get-iam-policy discord-bot-token --project=YOUR_PROJECT_ID
   ```

3. **Verify secret names match**:
   - Check `terraform.tfvars` secret names match actual secret names
   - Check Cloud Run service environment variables reference correct secrets

## Updating the Service

### Update Container Image

1. Build and push new image:
   ```bash
   ./build-and-push.sh
   ```

2. Update Terraform (if image tag changed):
   ```bash
   terraform apply -var="image=gcr.io/PROJECT_ID/main-service:NEW_TAG"
   ```

### Update Secrets

```bash
# Update Discord bot token
echo -n "NEW_TOKEN" | gcloud secrets versions add discord-bot-token \
  --data-file=- \
  --project=YOUR_PROJECT_ID

# Cloud Run will automatically use the latest version
```

### Update Configuration

1. Edit `terraform.tfvars`
2. Run `terraform plan` to review changes
3. Run `terraform apply` to apply changes

## Cleanup

To destroy all resources:

```bash
cd terraform
terraform destroy
```

**Note**: This will NOT delete Secret Manager secrets. Delete them manually if needed:

```bash
gcloud secrets delete discord-bot-token --project=YOUR_PROJECT_ID
gcloud secrets delete discord-channel-id --project=YOUR_PROJECT_ID
```

## Security Best Practices

1. **Never commit secrets**: Use Secret Manager, not Terraform variables
2. **Least privilege**: Service account only has Secret Manager access, not full project access
3. **Secret rotation**: Regularly rotate Discord bot tokens
4. **Monitoring**: Set up alerts for suspicious activity
5. **Logging**: Review logs regularly for security issues

## Cost Considerations

- **Cloud Run**: Charged per request and compute time (min_instances=1 means always-on)
- **Secret Manager**: $0.06 per secret version per month
- **Cloud Monitoring**: First 150MB of logs free, then $0.50 per GB

For a single instance running 24/7, expect approximately $20-30/month in Cloud Run costs.

## Support

For issues or questions:
1. Check service logs: `gcloud run services logs read main-service --region=us-central1`
2. Check Terraform state: `terraform show`
3. Review Cloud Monitoring metrics and alerts
