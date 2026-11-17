terraform {
  required_version = ">= 1.9"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 7.0, < 9.0" # google_memorystore_instance; written against 8.11
    }
  }
  # For a team, keep state in a GCS bucket instead of on a laptop:
  # backend "gcs" {}
}

provider "google" {
  project = var.project_id
}
