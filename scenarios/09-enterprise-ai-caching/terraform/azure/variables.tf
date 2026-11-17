variable "subscription_id" {
  description = "Azure subscription used only for these labs."
  type        = string
}

variable "prefix" {
  description = "Short lowercase name prefix; the cache DNS name must be globally unique."
  type        = string
  default     = "hp-aicache"
}

variable "regions" {
  description = "Region pair. The secondary is only created when enable_geo_replication is true."
  type = object({
    primary   = string
    secondary = string
  })
  default = {
    primary   = "eastus2"
    secondary = "westus3"
  }
}

variable "sku_name" {
  description = "Lab: Balanced_B3 (3 GB, smallest SKU that supports geo-replication). Production design: Balanced_B20."
  type        = string
  default     = "Balanced_B3"
}

variable "high_availability" {
  description = "Replica in a second zone. Needed for the SLA and for geo-replication; changing it recreates the cache."
  type        = bool
  default     = true
}

variable "enable_geo_replication" {
  description = "Create a second cache in regions.secondary and link both into an active-active group. The primary is always created as a one-member geo group, so turning this on later does not recreate it."
  type        = bool
  default     = false
}

variable "create_test_vm" {
  description = "Small Ubuntu VM (no public IP) plus free Bastion Developer, used to run the demo app."
  type        = bool
  default     = true
}

variable "ssh_public_key" {
  description = "Your SSH public key for the test VM (paste the contents of ~/.ssh/id_ed25519.pub)."
  type        = string
  default     = ""
}

variable "repo_url" {
  description = "Repository cloned onto the test VM."
  type        = string
  default     = "https://github.com/pankajrudrawar/ai-infra-labs.git"
}

variable "tags" {
  type = map(string)
  default = {
    project  = "ai-infra-series"
    scenario = "09"
  }
}
