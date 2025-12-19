variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region for Cloud Run"
  type        = string
  default     = "us-central1"
}

variable "service_name" {
  description = "Name of the Cloud Run service"
  type        = string
  default     = "chat-service"
}

variable "image" {
  description = "Container image URL (e.g., gcr.io/PROJECT_ID/chat-service:latest)"
  type        = string
}

variable "allow_unauthenticated" {
  description = "Allow unauthenticated access to the service"
  type        = bool
  default     = true
}

variable "min_instances" {
  description = "Minimum number of instances"
  type        = number
  default     = 0
}

variable "max_instances" {
  description = "Maximum number of instances"
  type        = number
  default     = 10
}

variable "cpu" {
  description = "CPU allocation"
  type        = string
  default     = "1"
}

variable "memory" {
  description = "Memory allocation"
  type        = string
  default     = "512Mi"
}

variable "tasks_client_id" {
  description = "Google Tasks OAuth Client ID"
  type        = string
  sensitive   = true
}

variable "tasks_client_secret" {
  description = "Google Tasks OAuth Client Secret"
  type        = string
  sensitive   = true
}

variable "tasks_refresh_token" {
  description = "Google Tasks OAuth Refresh Token"
  type        = string
  sensitive   = true
}

variable "session_secret" {
  description = "Session secret for FastAPI middleware"
  type        = string
  sensitive   = true
  default     = ""
}

variable "service_account_roles" {
  description = "List of IAM roles to grant to the Cloud Run service account"
  type        = list(string)
  default = [
    # Add roles here based on what Google Cloud APIs your service needs
    # Examples:
    # "roles/cloudtasks.enqueuer"  # For Cloud Tasks API
    # "roles/pubsub.publisher"      # For Pub/Sub
    # "roles/storage.objectViewer"  # For Cloud Storage
    # "roles/secretmanager.secretAccessor"  # For Secret Manager
  ]
}

variable "slack_client_id" {
  description = "Slack OAuth Client ID"
  type        = string
  sensitive   = true
}

variable "slack_client_secret" {
  description = "Slack OAuth Client Secret"
  type        = string
  sensitive   = true
}

variable "slack_redirect_uri" {
  description = "Slack OAuth Redirect URI"
  type        = string
  default     = ""  # Will be auto-generated from service URL if not provided
}