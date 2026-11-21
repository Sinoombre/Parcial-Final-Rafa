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
