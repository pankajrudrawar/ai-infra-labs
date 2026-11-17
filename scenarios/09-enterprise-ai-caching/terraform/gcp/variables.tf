variable "project_id" {
  description = "Google Cloud project used only for these labs."
  type        = string
}

variable "prefix" {
  type    = string
  default = "hp-aicache"
}

variable "regions" {
  description = "Region pair. The secondary is only created when enable_cross_region is true."
  type = object({
    primary   = string
    secondary = string
  })
  default = {
    primary   = "us-central1"
    secondary = "us-east4"
  }
}

variable "node_type" {
  description = "Lab: SHARED_CORE_NANO (1.4 GB, no SLA). Production design: HIGHMEM_MEDIUM."
  type        = string
  default     = "SHARED_CORE_NANO"
}

variable "shard_count" {
  description = "Lab: 1. Production design: 3."
  type        = number
  default     = 1
}

variable "replica_count" {
  description = "Replicas per shard in other zones. Lab: 0. Production: 1 or more."
  type        = number
  default     = 0
}

variable "engine_version" {
  type    = string
  default = "VALKEY_8_0"
}

variable "enable_cross_region" {
  description = "Create a read-only secondary instance in regions.secondary that replicates from the primary."
  type        = bool
  default     = false
}

variable "deletion_protection" {
  description = "Keep false for labs so teardown works; true in production."
  type        = bool
  default     = false
}

variable "create_test_vm" {
  type    = bool
  default = true
}

variable "repo_url" {
  type    = string
  default = "https://github.com/pankajrudrawar/ai-infra-labs.git"
}

variable "labels" {
  type = map(string)
  default = {
    project  = "ai-infra-series"
    scenario = "09"
  }
}
