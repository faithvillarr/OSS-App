output "service_url" {
  description = "URL of the deployed Cloud Run service"
  value       = google_cloud_run_service.main_service.status[0].url
}

output "service_name" {
  description = "Name of the Cloud Run service"
  value       = google_cloud_run_service.main_service.name
}

output "service_location" {
  description = "Location of the Cloud Run service"
  value       = google_cloud_run_service.main_service.location
}

output "service_account_email" {
  description = "Email of the service account used as Cloud Run service identity"
  value       = google_service_account.main_service_account.email
}

output "discord_bot_token_secret_name" {
  description = "Name of the Secret Manager secret for DISCORD_BOT_TOKEN"
  value       = var.discord_bot_token_secret_name
}

output "discord_channel_id_secret_name" {
  description = "Name of the Secret Manager secret for DISCORD_CHANNEL_ID"
  value       = var.discord_channel_id_secret_name
}
