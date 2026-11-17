# Optional: a small VM to run the demo app inside the VPC. No external IP: connect with
# the console's SSH button (through Identity-Aware Proxy). Cloud NAT gives it internet for pip.

resource "google_compute_firewall" "iap_ssh" {
  count         = var.create_test_vm ? 1 : 0
  name          = "${var.prefix}-allow-iap-ssh"
  network       = google_compute_network.vpc.id
  source_ranges = ["35.235.240.0/20"] # Google's IAP range
  target_tags   = ["${var.prefix}-vm"]
  allow {
    protocol = "tcp"
    ports    = ["22"]
  }
}

resource "google_compute_router" "nat" {
  count   = var.create_test_vm ? 1 : 0
  name    = "${var.prefix}-router"
  region  = var.regions.primary
  network = google_compute_network.vpc.id
}

resource "google_compute_router_nat" "nat" {
  count                              = var.create_test_vm ? 1 : 0
  name                               = "${var.prefix}-nat"
  router                             = google_compute_router.nat[0].name
  region                             = var.regions.primary
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"
}

resource "google_compute_instance" "vm" {
  count        = var.create_test_vm ? 1 : 0
  name         = "${var.prefix}-vm"
  zone         = "${var.regions.primary}-a"
  machine_type = "e2-medium"
  tags         = ["${var.prefix}-vm"]
  labels       = var.labels

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-12"
    }
  }

  network_interface {
    subnetwork = google_compute_subnetwork.app["primary"].id
  }

  service_account {
    email  = google_service_account.app.email
    scopes = ["cloud-platform"]
  }

  shielded_instance_config {
    enable_secure_boot = true
  }

  metadata_startup_script = <<-EOT
    apt-get update && apt-get install -y python3-venv git redis-tools
    [ -d /opt/ai-infra-labs ] || git clone ${var.repo_url} /opt/ai-infra-labs
    python3 -m venv /opt/venv
    /opt/venv/bin/pip install -r /opt/ai-infra-labs/scenarios/09-enterprise-ai-caching/app/requirements.txt
    chmod -R a+rwX /opt/ai-infra-labs /opt/venv
  EOT

  depends_on = [google_compute_router_nat.nat]
}
