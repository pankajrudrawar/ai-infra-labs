locals {
  regions = var.enable_cross_region ? {
    primary   = { region = var.regions.primary, cidr = "10.80.0.0/20" }
    secondary = { region = var.regions.secondary, cidr = "10.81.0.0/20" }
    } : {
    primary = { region = var.regions.primary, cidr = "10.80.0.0/20" }
  }
}

resource "google_project_service" "apis" {
  for_each = toset([
    "compute.googleapis.com",
    "memorystore.googleapis.com",
    "networkconnectivity.googleapis.com",
    "serviceconsumermanagement.googleapis.com",
    "iap.googleapis.com",
  ])
  service            = each.value
  disable_on_destroy = false
}

# ---------------------------------------------------------------- network: one global VPC
resource "google_compute_network" "vpc" {
  name                    = "${var.prefix}-vpc"
  auto_create_subnetworks = false
  depends_on              = [google_project_service.apis]
}

resource "google_compute_subnetwork" "app" {
  for_each                 = local.regions
  name                     = "${var.prefix}-${each.key}"
  region                   = each.value.region
  network                  = google_compute_network.vpc.id
  ip_cidr_range            = each.value.cidr
  private_ip_google_access = true
}

# Lets Memorystore create Private Service Connect endpoints in our subnet automatically.
resource "google_network_connectivity_service_connection_policy" "memorystore" {
  for_each      = local.regions
  name          = "${var.prefix}-memorystore-${each.key}"
  location      = each.value.region
  service_class = "gcp-memorystore"
  network       = google_compute_network.vpc.id
  psc_config {
    subnetworks = [google_compute_subnetwork.app[each.key].id]
  }
}

# ---------------------------------------------------------------- Memorystore for Valkey
resource "google_memorystore_instance" "primary" {
  instance_id                 = "${var.prefix}-primary"
  location                    = var.regions.primary
  mode                        = "CLUSTER"
  shard_count                 = var.shard_count
  replica_count               = var.replica_count
  node_type                   = var.node_type
  engine_version              = var.engine_version
  authorization_mode          = "IAM_AUTH"              # no passwords; service accounts sign in
  transit_encryption_mode     = "SERVER_AUTHENTICATION" # TLS
  deletion_protection_enabled = var.deletion_protection
  labels                      = var.labels

  engine_configs = {
    maxmemory-policy = "volatile-lru" # every cache key has a TTL; evict least recently used
  }

  zone_distribution_config {
    mode = "MULTI_ZONE"
  }

  desired_auto_created_endpoints {
    network    = google_compute_network.vpc.id
    project_id = var.project_id
  }

  depends_on = [google_network_connectivity_service_connection_policy.memorystore]
}

resource "google_memorystore_instance" "secondary" {
  count                       = var.enable_cross_region ? 1 : 0
  instance_id                 = "${var.prefix}-secondary"
  location                    = var.regions.secondary
  mode                        = "CLUSTER"
  shard_count                 = var.shard_count # must match the primary
  replica_count               = var.replica_count
  node_type                   = var.node_type
  engine_version              = var.engine_version
  authorization_mode          = "IAM_AUTH"
  transit_encryption_mode     = "SERVER_AUTHENTICATION"
  deletion_protection_enabled = var.deletion_protection
  labels                      = var.labels

  engine_configs = {
    maxmemory-policy = "volatile-lru"
  }

  zone_distribution_config {
    mode = "MULTI_ZONE"
  }

  desired_auto_created_endpoints {
    network    = google_compute_network.vpc.id
    project_id = var.project_id
  }

  cross_instance_replication_config {
    instance_role = "SECONDARY"
    primary_instance {
      instance = google_memorystore_instance.primary.id
    }
  }

  depends_on = [google_network_connectivity_service_connection_policy.memorystore]
}

# ---------------------------------------------------------------- identity for the app
resource "google_service_account" "app" {
  account_id   = "${var.prefix}-app"
  display_name = "AI cache demo app"
}

# Project-wide for the lab project. In a shared production project, add an IAM condition on
# resource.name (projects/PROJECT/locations/REGION/instances/NAME) to scope it to one instance.
resource "google_project_iam_member" "app_db_connect" {
  project = var.project_id
  role    = "roles/memorystore.dbConnectionUser"
  member  = "serviceAccount:${google_service_account.app.email}"
}

# Lets the VM download the instance's CA certificate.
resource "google_project_iam_member" "app_viewer" {
  project = var.project_id
  role    = "roles/memorystore.viewer"
  member  = "serviceAccount:${google_service_account.app.email}"
}
