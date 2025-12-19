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
  default     = "main-service"
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
  description = "Minimum number of instances (set to 1 for long-running polling service)"
  type        = number
  default     = 1
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
    "roles/secretmanager.secretAccessor"  # For Secret Manager access
  ]
}

variable "discord_bot_token_secret_name" {
  description = "Name of the Secret Manager secret containing DISCORD_BOT_TOKEN"
  type        = string
  default     = "discord-bot-token"
}

variable "discord_channel_id_secret_name" {
  description = "Name of the Secret Manager secret containing DISCORD_CHANNEL_ID"
  type        = string
  default     = "discord-channel-id"
}

variable "create_secrets" {
  description = "Whether to create Secret Manager secrets via Terraform (false if secrets already exist)"
  type        = bool
  default     = false
}

variable "discord_bot_token" {
  description = "Discord bot token (only used if create_secrets is true)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "discord_channel_id" {
  description = "Discord channel ID (only used if create_secrets is true)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "openai_api_key" {
  description = "OpenAI API key for AI client"
  type        = string
  sensitive   = true
}
