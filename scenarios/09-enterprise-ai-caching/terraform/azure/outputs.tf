output "cache_hostnames" {
  description = "Private DNS names of the caches (port 10000, TLS)."
  value       = { for k, c in azurerm_managed_redis.cache : k => c.hostname }
}

output "app_identity_client_id" {
  description = "Client ID of the managed identity the app signs in with."
  value       = azurerm_user_assigned_identity.app.client_id
}

output "demo_env" {
  description = "Paste on the test VM before running the demo."
  value       = <<-EOT
    export CACHE_HOST=${azurerm_managed_redis.cache["primary"].hostname}
    export CACHE_PORT=10000 CACHE_TLS=1 CACHE_CLUSTER=0 CACHE_AUTH=entra
    export AZURE_CLIENT_ID=${azurerm_user_assigned_identity.app.client_id}
  EOT
}
