locals {
  regions = var.enable_geo_replication ? {
    primary   = { location = var.regions.primary, cidr = "10.90.0.0/16" }
    secondary = { location = var.regions.secondary, cidr = "10.91.0.0/16" }
    } : {
    primary = { location = var.regions.primary, cidr = "10.90.0.0/16" }
  }
  # Joining a geo-replication group later would recreate the database (data loss), so the
  # primary starts as a group of one.
  geo_group = "${var.prefix}-geo"
}

resource "azurerm_resource_group" "lab" {
  name     = "rg-${var.prefix}"
  location = var.regions.primary
  tags     = var.tags
}

# ---------------------------------------------------------------- network, one VNet per region
resource "azurerm_virtual_network" "vnet" {
  for_each            = local.regions
  name                = "vnet-${var.prefix}-${each.key}"
  location            = each.value.location
  resource_group_name = azurerm_resource_group.lab.name
  address_space       = [each.value.cidr]
  tags                = var.tags
}

resource "azurerm_subnet" "app" {
  for_each             = local.regions
  name                 = "snet-app"
  resource_group_name  = azurerm_resource_group.lab.name
  virtual_network_name = azurerm_virtual_network.vnet[each.key].name
  address_prefixes     = [cidrsubnet(each.value.cidr, 8, 1)]
}

resource "azurerm_subnet" "private_endpoints" {
  for_each             = local.regions
  name                 = "snet-private-endpoints"
  resource_group_name  = azurerm_resource_group.lab.name
  virtual_network_name = azurerm_virtual_network.vnet[each.key].name
  address_prefixes     = [cidrsubnet(each.value.cidr, 8, 2)]
}

resource "azurerm_virtual_network_peering" "p2s" {
  count                     = var.enable_geo_replication ? 1 : 0
  name                      = "primary-to-secondary"
  resource_group_name       = azurerm_resource_group.lab.name
  virtual_network_name      = azurerm_virtual_network.vnet["primary"].name
  remote_virtual_network_id = azurerm_virtual_network.vnet["secondary"].id
}

resource "azurerm_virtual_network_peering" "s2p" {
  count                     = var.enable_geo_replication ? 1 : 0
  name                      = "secondary-to-primary"
  resource_group_name       = azurerm_resource_group.lab.name
  virtual_network_name      = azurerm_virtual_network.vnet["secondary"].name
  remote_virtual_network_id = azurerm_virtual_network.vnet["primary"].id
}

# ---------------------------------------------------------------- Azure Managed Redis
resource "azurerm_managed_redis" "cache" {
  for_each                  = local.regions
  name                      = "${var.prefix}-${each.key}"
  resource_group_name       = azurerm_resource_group.lab.name
  location                  = each.value.location
  sku_name                  = var.sku_name
  high_availability_enabled = var.high_availability
  public_network_access     = "Disabled" # reachable only through private endpoints
  tags                      = var.tags

  default_database {
    client_protocol                    = "Encrypted" # TLS only
    access_keys_authentication_enabled = false       # Microsoft Entra ID only, no shared keys
    clustering_policy                  = "EnterpriseCluster"
    eviction_policy                    = "NoEviction" # required with RediSearch; TTLs free memory
    geo_replication_group_name         = local.geo_group

    module {
      name = "RediSearch" # vector search for the semantic LLM cache
    }
  }
}

resource "azurerm_managed_redis_geo_replication" "group" {
  count                    = var.enable_geo_replication ? 1 : 0
  managed_redis_id         = azurerm_managed_redis.cache["primary"].id
  linked_managed_redis_ids = [azurerm_managed_redis.cache["secondary"].id]

  lifecycle {
    precondition {
      condition     = var.high_availability
      error_message = "Keep high_availability = true for geo-replicated caches."
    }
  }
}

# ---------------------------------------------------------------- private endpoints + DNS
resource "azurerm_private_dns_zone" "redis" {
  name                = "privatelink.redis.azure.net"
  resource_group_name = azurerm_resource_group.lab.name
  tags                = var.tags
}

resource "azurerm_private_dns_zone_virtual_network_link" "redis" {
  for_each            = local.regions
  name                = "link-${each.key}"
  private_dns_zone_id = azurerm_private_dns_zone.redis.id
  virtual_network_id  = azurerm_virtual_network.vnet[each.key].id
}

resource "azurerm_private_endpoint" "redis" {
  for_each            = local.regions
  name                = "pe-${var.prefix}-${each.key}"
  location            = each.value.location
  resource_group_name = azurerm_resource_group.lab.name
  subnet_id           = azurerm_subnet.private_endpoints[each.key].id
  tags                = var.tags

  private_service_connection {
    name                           = "psc-${each.key}"
    private_connection_resource_id = azurerm_managed_redis.cache[each.key].id
    subresource_names              = ["redisEnterprise"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "redis"
    private_dns_zone_ids = [azurerm_private_dns_zone.redis.id]
  }
}

# ---------------------------------------------------------------- identity for the app
resource "azurerm_user_assigned_identity" "app" {
  name                = "id-${var.prefix}-app"
  location            = var.regions.primary
  resource_group_name = azurerm_resource_group.lab.name
  tags                = var.tags
}

resource "azurerm_managed_redis_access_policy_assignment" "app" {
  for_each         = local.regions
  managed_redis_id = azurerm_managed_redis.cache[each.key].id
  object_id        = azurerm_user_assigned_identity.app.principal_id
}
