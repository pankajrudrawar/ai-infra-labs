output "primary_instance" {
  value = google_memorystore_instance.primary.id
}

output "primary_endpoints" {
  description = "Look for the DISCOVERY connection's IP address; clients connect there on port 6379."
  value       = google_memorystore_instance.primary.endpoints
}

output "demo_env" {
  description = "Paste on the test VM (fill in the discovery IP and fetch the CA first; see the README)."
  value       = <<-EOT
    export CACHE_HOST=<discovery-endpoint-ip> CACHE_PORT=6379
    export CACHE_TLS=1 CACHE_CA_FILE=$HOME/server_ca.pem CACHE_CLUSTER=1 CACHE_AUTH=gcp-iam
  EOT
}
