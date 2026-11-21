
output "resource_group_name" {
  description = "Nombre del grupo de recursos"
  value       = azurerm_resource_group.main.name
}

output "resource_group_location" {
  description = "Region del grupo de recursos"
  value       = azurerm_resource_group.main.location
}
