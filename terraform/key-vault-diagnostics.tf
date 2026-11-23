resource "azurerm_log_analytics_workspace" "main" {
  name                = "law-${var.suffix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
}

# S6: Key Vault envía AuditEvent a la tabla AzureDiagnostics del workspace.
resource "azurerm_monitor_diagnostic_setting" "key_vault" {
  name                       = "key-vault-audit"
  target_resource_id         = azurerm_key_vault.app.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id

  enabled_log {
    category = "AuditEvent"
  }
}
