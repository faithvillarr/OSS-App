# Secret Manager secrets for Discord credentials
resource "google_secret_manager_secret" "discord_bot_token" {
  count     = var.create_secrets ? 1 : 0
  secret_id = var.discord_bot_token_secret_name
  project   = var.project_id

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "discord_bot_token" {
  count       = var.create_secrets ? 1 : 0
  secret      = google_secret_manager_secret.discord_bot_token[0].id
  secret_data = var.discord_bot_token
}

resource "google_secret_manager_secret" "discord_channel_id" {
  count     = var.create_secrets ? 1 : 0
  secret_id = var.discord_channel_id_secret_name
  project   = var.project_id

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "discord_channel_id" {
  count       = var.create_secrets ? 1 : 0
  secret      = google_secret_manager_secret.discord_channel_id[0].id
  secret_data = var.discord_channel_id
}

# Service Account for Cloud Run Service Identity
resource "google_service_account" "main_service_account" {
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
  member   = "serviceAccount:${google_service_account.main_service_account.email}"
}

# Grant Secret Manager access to service account for Discord secrets
resource "google_secret_manager_secret_iam_member" "discord_bot_token_accessor" {
  secret_id = var.discord_bot_token_secret_name
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.main_service_account.email}"
  project   = var.project_id
}

resource "google_secret_manager_secret_iam_member" "discord_channel_id_accessor" {
  secret_id = var.discord_channel_id_secret_name
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.main_service_account.email}"
  project   = var.project_id
}

# Cloud Run Service
resource "google_cloud_run_service" "main_service" {
  name     = var.service_name
  location = var.region
  project  = var.project_id

  template {
    spec {
      # Configure service identity - this is what allows the service to call Google Cloud APIs
      service_account_name = google_service_account.main_service_account.email

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

        env {
          name  = "OPENAI_API_KEY"
          value = var.openai_api_key
        }

        # Discord credentials from Secret Manager
        env {
          name = "DISCORD_BOT_TOKEN"
          value_from {
            secret_key_ref {
              name = var.discord_bot_token_secret_name
              key  = "latest"
            }
          }
        }

        env {
          name = "DISCORD_CHANNEL_ID"
          value_from {
            secret_key_ref {
              name = var.discord_channel_id_secret_name
              key  = "latest"
            }
          }
        }

        resources {
          limits = {
            cpu    = var.cpu
            memory = var.memory
          }
        }
      }

      container_concurrency = 1
      timeout_seconds       = 60
    }

    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale" = tostring(var.min_instances)
        "autoscaling.knative.dev/maxScale" = tostring(var.max_instances)
        "run.googleapis.com/execution-environment" = "gen1"
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
  service  = google_cloud_run_service.main_service.name
  location = google_cloud_run_service.main_service.location
  project  = var.project_id
  role     = "roles/run.invoker"
  member    = "allUsers"
}
