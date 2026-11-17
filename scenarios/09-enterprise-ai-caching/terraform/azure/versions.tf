terraform {
  required_version = ">= 1.9"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 5.0" # azurerm_managed_redis* resources; written against 5.14
    }
  }
  # For a team, keep state in an Azure Storage backend instead of on a laptop:
  # backend "azurerm" {}
}

provider "azurerm" {
  features {}
  subscription_id = var.subscription_id
}
