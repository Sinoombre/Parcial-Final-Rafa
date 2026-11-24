# E5 - Observabilidad: Log Analytics, grupo de acciones con correo y alertas.
# Archivo nuevo: se agrega junto a los demas .tf de la carpeta terraform/.
# Depende de azurerm_log_analytics_workspace.main (key-vault-diagnostics.tf).

# El workspace de Log Analytics ya existe en key-vault-diagnostics.tf
# (azurerm_log_analytics_workspace.main); aqui solo se reutiliza.

resource "azurerm_monitor_action_group" "email" {
  name                = "ag-${var.suffix}"
  resource_group_name = var.resource_group_name
  short_name          = "caribeshop" # maximo 12 caracteres

  email_receiver {
    name                    = "equipo-caribeshop"
    email_address           = var.alert_email
    use_common_alert_schema = true
  }
}

# E5 - Alerta principal: la sonda de salud del balanceador baja de 100 %.
# "DipAvailability" es la metrica que el portal muestra como "Health Probe Status".
resource "azurerm_monitor_metric_alert" "health_probe" {
  name                = "alert-health-probe-${var.suffix}"
  resource_group_name = var.resource_group_name
  scopes              = [azurerm_lb.main.id]
  description         = "Alguna instancia del VMSS no responde a la sonda /health (Health Probe Status < 100 %)."
  severity            = 2
  frequency           = "PT1M"
  window_size         = "PT5M"
  auto_mitigate       = true

  criteria {
    metric_namespace = "Microsoft.Network/loadBalancers"
    metric_name      = "DipAvailability"
    aggregation      = "Average"
    operator         = "LessThan"
    threshold        = 100
  }

  action {
    action_group_id = azurerm_monitor_action_group.email.id
  }
}

# Alerta adicional: CPU sostenida del VMSS (complementa el autoscale).
resource "azurerm_monitor_metric_alert" "cpu_alta" {
  name                = "alert-cpu-alta-${var.suffix}"
  resource_group_name = var.resource_group_name
  scopes              = [azurerm_linux_virtual_machine_scale_set.app.id]
  description         = "CPU promedio del VMSS por encima de 80 % durante 10 minutos."
  severity            = 3
  frequency           = "PT5M"
  window_size         = "PT15M"

  criteria {
    metric_namespace = "Microsoft.Compute/virtualMachineScaleSets"
    metric_name      = "Percentage CPU"
    aggregation      = "Average"
    operator         = "GreaterThan"
    threshold        = 80
  }

  action {
    action_group_id = azurerm_monitor_action_group.email.id
  }
}

# Evidencia de E3: historial de evaluaciones y acciones del autoscale en Log Analytics.
resource "azurerm_monitor_diagnostic_setting" "autoscale" {
  name                       = "diag-autoscale"
  target_resource_id         = azurerm_monitor_autoscale_setting.app.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id

  enabled_log {
    category = "AutoscaleEvaluations"
  }

  enabled_log {
    category = "AutoscaleScaleActions"
  }
}

# Metricas del balanceador (sonda de salud) en Log Analytics.
resource "azurerm_monitor_diagnostic_setting" "lb" {
  name                       = "diag-lb"
  target_resource_id         = azurerm_lb.main.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id

  enabled_metric {
    category = "AllMetrics"
  }
}
