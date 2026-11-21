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
  default     = "Standard_B2s"
}

variable "min_instances" {
  description = "Minimum number of VM instances in the scale set"
  type        = number
  default     = 2
}

variable "max_instances" {
  description = "Maximum number of VM instances in the scale set"
  type        = number
  default     = 5
}

variable "admin_ssh_public_key" {
  description = "Public SSH key for the admin user"
  type        = string
}