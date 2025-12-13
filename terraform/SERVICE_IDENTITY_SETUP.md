# Cloud Run Service Identity Setup Guide

This guide explains how Cloud Run service identity works and how it's configured in this project.

## What is Service Identity?

**Service identity** is the service account that Cloud Run uses when your application calls Google Cloud APIs. It's different from:

- **User credentials** (OAuth tokens) - Used for user-specific API access (like accessing a user's Google Tasks)
- **Terraform credentials** - Used to deploy infrastructure

Service identity is automatically used when your code:
- Uses Google Cloud Client Libraries (e.g., `google-cloud-storage`, `google-cloud-pubsub`)
- Calls other Cloud Run services
- Accesses Google Cloud services that require authentication

## How It Works

According to the [Google Cloud documentation](https://docs.cloud.google.com/run/docs/securing/service-identity#call-apis-with-service-identity):

1. Your code uses Cloud Client Libraries to make requests to Google Cloud APIs
2. The client library requests an OAuth 2.0 access token from the instance metadata server
3. The metadata server provides an access token for the service account configured as service identity
4. The request is sent with the OAuth 2.0 access token
5. IAM verifies the service identity has necessary permissions
6. The Google Cloud API performs the operation

## Configuration in This Project

### 1. Service Account Creation

The Terraform configuration creates a dedicated service account:

```hcl
resource "google_service_account" "chat_service_account" {
  account_id   = "${var.service_name}-sa"
  display_name = "Service account for ${var.service_name}"
  ...
}
```

### 2. Assigning Service Identity

The Cloud Run service is configured to use this service account:

```hcl
template {
  spec {
    service_account_name = google_service_account.chat_service_account.email
    ...
  }
}
```

This tells Cloud Run: "When this service calls Google Cloud APIs, use this service account's credentials."

### 3. Granting Permissions

Permissions are granted via IAM roles:

```hcl
resource "google_project_iam_member" "service_account_permissions" {
  for_each = toset(var.service_account_roles)
  project  = var.project_id
  role     = each.value
  member   = "serviceAccount:${google_service_account.chat_service_account.email}"
}
```

## Setting Up Permissions

### Step 1: Identify Required APIs

Determine which Google Cloud APIs your service needs to call. For example:
- **Cloud Storage** - If you need to read/write files
- **Pub/Sub** - If you need to publish/subscribe to messages
- **Secret Manager** - If you need to access secrets
- **Cloud Tasks** - If you need to enqueue tasks
- **Cloud Logging** - Usually granted automatically

### Step 2: Add Roles to Terraform

Edit `terraform/variables.tf` and add roles to the `service_account_roles` variable:

```hcl
variable "service_account_roles" {
  description = "List of IAM roles to grant to the Cloud Run service account"
  type        = list(string)
  default = [
    "roles/storage.objectViewer",           # Read Cloud Storage objects
    "roles/pubsub.publisher",                # Publish Pub/Sub messages
    "roles/secretmanager.secretAccessor",    # Access Secret Manager secrets
  ]
}
```

### Step 3: Deploy

After updating the roles, deploy:

```bash
cd terraform
terraform plan  # Review changes
terraform apply # Apply changes
```

## Using Service Identity in Your Code

### With Cloud Client Libraries

When using Google Cloud Client Libraries, they automatically use service identity:

```python
from google.cloud import storage

# This automatically uses the service identity configured in Cloud Run
client = storage.Client()
bucket = client.bucket('my-bucket')
blob = bucket.blob('my-file.txt')
content = blob.download_as_text()
```

### Manual Token Fetching

If you need to fetch tokens manually (not recommended for most cases):

```python
import requests

# Fetch access token from metadata server
response = requests.get(
    "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token",
    headers={"Metadata-Flavor": "Google"}
)
token = response.json()["access_token"]

# Use token in API calls
headers = {"Authorization": f"Bearer {token}"}
```

## Important Notes

### ⚠️ Never Set GOOGLE_APPLICATION_CREDENTIALS

**Warning**: Never set `GOOGLE_APPLICATION_CREDENTIALS` as an environment variable in Cloud Run. This would override service identity and is a security risk.

### User OAuth vs Service Identity

Your application uses **two different authentication methods**:

1. **Service Identity** (service account) - For calling Google Cloud APIs on behalf of the service
2. **User OAuth** (TASKS_CLIENT_ID, TASKS_CLIENT_SECRET, TASKS_REFRESH_TOKEN) - For accessing user-specific Google Tasks data

These work together:
- Service identity handles infrastructure-level API calls
- User OAuth handles user-specific data access

### Default Service Account

If you don't specify a service account, Cloud Run uses the Compute Engine default service account (`PROJECT_NUMBER-compute@developer.gserviceaccount.com`). This is **not recommended** because:

- It might have overly broad permissions (Editor role)
- It's shared across all services in your project
- It's harder to audit and manage

## Troubleshooting

### "Permission denied" errors

1. Check that the service account has the required roles:
   ```bash
   gcloud projects get-iam-policy PROJECT_ID \
     --flatten="bindings[].members" \
     --filter="bindings.members:serviceAccount:SERVICE_ACCOUNT_EMAIL"
   ```

2. Verify the service is using the correct service account:
   ```bash
   gcloud run services describe SERVICE_NAME \
     --region=REGION \
     --format="value(spec.template.spec.serviceAccountName)"
   ```

### "No credentials found" errors

- Ensure `service_account_name` is set in Terraform
- Verify the service account exists and is active
- Check that you're not setting `GOOGLE_APPLICATION_CREDENTIALS` in environment variables

## Next Steps

1. **Review your code** - Identify which Google Cloud APIs you're calling
2. **Add required roles** - Update `service_account_roles` in `variables.tf`
3. **Deploy** - Run `terraform apply` to create the service account and assign it
4. **Test** - Verify your service can call the required APIs

## References

- [Google Cloud: Service Identity Documentation](https://docs.cloud.google.com/run/docs/securing/service-identity#call-apis-with-service-identity)
- [Application Default Credentials](https://cloud.google.com/docs/authentication/application-default-credentials)
- [IAM Roles for Cloud Run](https://cloud.google.com/run/docs/securing/service-identity#permissions)

