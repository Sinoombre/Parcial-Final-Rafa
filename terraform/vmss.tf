resource "azurerm_linux_virtual_machine_scale_set" "app" {
  name                = "vmss-${var.suffix}"
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = var.vm_sku
  instances           = var.min_instances
  zones               = var.zones
  zone_balance        = true
  health_probe_id     = azurerm_lb_probe.health.id
  upgrade_mode        = "Rolling" # Actualización de instancias de VMSS por lotes, no todas a la vez, obligatorio para health_probe_id

  admin_username                  = "azureadminuser"
  disable_password_authentication = true

  admin_ssh_key {
    username   = "azureadminuser"
    public_key = var.admin_ssh_public_key
  }

  custom_data = base64encode(templatefile("${path.module}/cloud-init.yaml", {
    app_b64               = filebase64("${path.module}/../app/app.py")
    key_vault_uri         = azurerm_key_vault.app.vault_uri
    key_vault_secret_name = azurerm_key_vault_secret.demo.name
  }))

  extension_operations_enabled = true

  identity {
    type = "SystemAssigned" # Para que se pueda realizar S3 y S4
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "ubuntu-24_04-lts"
    sku       = "server"
    version   = "latest"
  }

  os_disk {
    storage_account_type = "StandardSSD_LRS"
    caching              = "ReadWrite"
  }

  encryption_at_host_enabled = true

  network_interface {
    name    = "nic"
    primary = true

    ip_configuration { # sin public_ip_address
      name                                   = "internal"
      primary                                = true
      subnet_id                              = azurerm_subnet.app.id
      load_balancer_backend_address_pool_ids = [azurerm_lb_backend_address_pool.app.id]
    }
  }

  rolling_upgrade_policy {
    # 50 porque solo hay 2 máquinas
    max_batch_instance_percent              = 50
    max_unhealthy_instance_percent          = 50
    max_unhealthy_upgraded_instance_percent = 50
    pause_time_between_batches              = "PT2M" # Tiempo de espera de 2min para empezar con una nueva batch
  }

  automatic_instance_repair {
    enabled      = true
    grace_period = "PT10M" # Tiempo de 10min
  }

  # La regla debe existir antes de que el VMSS use la sonda
  depends_on = [azurerm_lb_rule.http]

  lifecycle {
    ignore_changes = [instances] # E3
  }
}
