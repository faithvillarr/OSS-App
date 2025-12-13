# Service Account for Cloud Run Service Identity
resource "google_service_account" "chat_service_account" {
  account_id   = "${var.service_name}-sa"
  display_name = "Service account for ${var.service_name}"
  description  = "Service account used as Cloud Run service identity for ${var.service_name}"
  project      = var.project_id
}

# Grant necessary permissions to the service account
# Note: Adjust these based on what Google Cloud APIs your service needs to call
resource "google_project_iam_member" "service_account_permissions" {
  for_each = toset(var.service_account_roles)
  project  = var.project_id
  role     = each.value
  member   = "serviceAccount:${google_service_account.chat_service_account.email}"
}

# Cloud Run Service
resource "google_cloud_run_service" "chat_service" {
  name     = var.service_name
  location = var.region
  project  = var.project_id

  template {
    spec {
      # Configure service identity - this is what allows the service to call Google Cloud APIs
      service_account_name = google_service_account.chat_service_account.email

      containers {
        image = var.image

        ports {
          container_port = 8080
        }

        env {
          name  = "TASKS_CLIENT_ID"
          value = var.tasks_client_id
        }

        env {
          name  = "TASKS_CLIENT_SECRET"
          value = var.tasks_client_secret
        }

        env {
          name  = "TASKS_REFRESH_TOKEN"
          value = var.tasks_refresh_token
        }

        env {
          name  = "SESSION_SECRET"
          value = var.session_secret != "" ? var.session_secret : random_id.session_secret.hex
        }

        resources {
          limits = {
            cpu    = var.cpu
            memory = var.memory
          }
        }
      }

      container_concurrency = 80
      timeout_seconds       = 300
    }

    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale" = tostring(var.min_instances)
        "autoscaling.knative.dev/maxScale" = tostring(var.max_instances)
        "run.googleapis.com/execution-environment" = "gen2"
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }
}

# Generate random session secret if not provided
resource "random_id" "session_secret" {
  byte_length = 32
}

# IAM policy for public access (if allow_unauthenticated is true)
resource "google_cloud_run_service_iam_member" "public_access" {
  count    = var.allow_unauthenticated ? 1 : 0
  service  = google_cloud_run_service.chat_service.name
  location = google_cloud_run_service.chat_service.location
  project  = var.project_id
  role     = "roles/run.invoker"
  member    = "allUsers"
}
