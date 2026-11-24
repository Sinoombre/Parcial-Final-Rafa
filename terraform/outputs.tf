output "resource_group_name" {
  description = "Nombre del grupo de recursos"
  value       = azurerm_resource_group.main.name
}

output "resource_group_location" {
  description = "Region del grupo de recursos"
  value       = azurerm_resource_group.main.location
}

output "lb_public_ip" {
  description = "IP Pública de Load Balancer"
  value       = azurerm_public_ip.ip_lb.ip_address
}

output "vmss_name" {
  description = "Nombre de VMSS"
  value       = azurerm_linux_virtual_machine_scale_set.app.name
}

output "vmss_principal_id" {
  description = "ID principal de Linux Virtual Machine Scale Set"
  value       = azurerm_linux_virtual_machine_scale_set.app.identity[0].principal_id
}

output "subnet_app_id" {
  description = "ID de la subnet de la aplicación web"
  value       = azurerm_subnet.app.id
}

output "log_analytics_workspace_name" {
  description = "Nombre del workspace donde se consulta la auditoría de Key Vault"
  value       = azurerm_log_analytics_workspace.main.name
}

output "log_analytics_workspace_guid" {
  description = "Workspace ID (GUID) para consultas KQL desde la CLI"
  value       = azurerm_log_analytics_workspace.main.workspace_id
}

output "autoscale_name" {
  description = "Nombre del autoscale setting"
  value       = azurerm_monitor_autoscale_setting.app.name
}

output "lb_name" {
  description = "Nombre del Load Balancer"
  value       = azurerm_lb.main.name
}
