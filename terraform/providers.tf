terraform {
  required_version = ">= 1.11.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~>5.14.0"
    }
  }
}

provider "azurerm" {
  features {
    key_vault {
      # Azure debe respetar la retención del almacén protegido al destruirlo.
      purge_soft_delete_on_destroy          = false
      purge_soft_deleted_secrets_on_destroy = false
    }
  }

  resource_provider_registrations = "none"
}
