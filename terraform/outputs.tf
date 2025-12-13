output "service_url" {
  description = "URL of the deployed Cloud Run service"
  value       = google_cloud_run_service.chat_service.status[0].url
}

output "service_name" {
  description = "Name of the Cloud Run service"
  value       = google_cloud_run_service.chat_service.name
}

output "service_location" {
  description = "Location of the Cloud Run service"
  value       = google_cloud_run_service.chat_service.location
}

output "service_account_email" {
  description = "Email of the service account used as Cloud Run service identity"
  value       = google_service_account.chat_service_account.email
}
