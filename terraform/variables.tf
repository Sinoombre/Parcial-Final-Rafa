variable "location" {
  description = "Region de Azure para CaribeShop"
  type        = string
  default     = "eastus2"
}

variable "resource_group_name" {
  description = "Nombre del grupo de recursos principal"
  type        = string
  default     = "rg-caribeshop"
}

variable "suffix" {
  description = "Suffix for resource names"
  type        = string
  default     = "caribeshop"
}

variable "vm_sku" {
  description = "SKU for the virtual machines"
  type        = string
  default     = "Standard_F1als_v7"
}

variable "min_instances" {
  description = "Minimum number of VM instances in the scale set"
  type        = number
  default     = 2
}

variable "max_instances" {
  description = "Maximum number of VM instances in the scale set"
  type        = number
  default     = 2
}

variable "admin_ssh_public_key" {
  description = "Public SSH key for the admin user"
  type        = string
}

variable "zones" {
  description = "Zones that are available for the SKU"
  type        = list(string)
  default     = ["1", "3"]
}

variable "key_vault_name" {
  description = "Nombre globalmente único para el Key Vault"
  type        = string
  nullable    = false

  validation {
    condition     = can(regex("^[a-zA-Z][a-zA-Z0-9-]{1,22}[a-zA-Z0-9]$", var.key_vault_name)) && !strcontains(var.key_vault_name, "--")
    error_message = "Usa de 3 a 24 caracteres: letras, números o guiones no consecutivos. Inicia con una letra y termina en letra o número."
  }
}

variable "key_vault_operator_ip" {
  description = "IPv4 pública de salida del operador, sin el sufijo /32"
  type        = string
  nullable    = false

  validation {
    condition     = can(cidrnetmask("${var.key_vault_operator_ip}/32"))
    error_message = "Indica una sola dirección IPv4 pública sin máscara CIDR."
  }
}

variable "key_vault_demo_secret_value" {
  description = "Valor de prueba entregado por TF_VAR_key_vault_demo_secret_value, nunca por archivos del repositorio"
  type        = string
  nullable    = false
  sensitive   = true
  ephemeral   = true
}

variable "key_vault_demo_secret_expiration" {
  description = "Fecha futura de expiración del secreto de prueba en UTC, con formato YYYY-MM-DDTHH:MM:SSZ"
  type        = string
  nullable    = false

  validation {
    condition     = can(regex("^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$", var.key_vault_demo_secret_expiration)) && can(formatdate("YYYY", var.key_vault_demo_secret_expiration))
    error_message = "Indica una fecha UTC válida con formato YYYY-MM-DDTHH:MM:SSZ."
  }
}
