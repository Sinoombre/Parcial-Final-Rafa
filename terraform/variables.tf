variable "suffix" {
  description = "Suffix for resource names"
  type        = string
  default    = "caribeshop"
}

variable "location" {
  description = "Azure region for resources"
  type        = string
}

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}