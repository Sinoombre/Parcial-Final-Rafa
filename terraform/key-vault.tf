data "azurerm_client_config" "current" {}

resource "azurerm_key_vault" "app" {
  #checkov:skip=CKV2_AZURE_32: S3 usa service endpoint y la IPv4 del operador en vez de Private Link. Se acepta la exposición del endpoint público porque el firewall deniega por defecto, sin excepciones para servicios de Azure, y RBAC controla las lecturas.
  name                       = var.key_vault_name
  location                   = azurerm_resource_group.main.location
  resource_group_name        = azurerm_resource_group.main.name
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  rbac_authorization_enabled = true

  soft_delete_retention_days = 7
  purge_protection_enabled   = true

  # El endpoint público es necesario para la IP del operador; la ACL
  # rechaza las solicitudes que no vengan de una red autorizada.
  public_network_access_enabled = true

  network_acls {
    bypass                     = "None"
    default_action             = "Deny"
    ip_rules                   = ["${var.key_vault_operator_ip}/32"]
    virtual_network_subnet_ids = [azurerm_subnet.app.id]
  }
}

# S4: la identidad del VMSS puede leer secretos de este almacén,
# pero no escribirlos ni administrar el recurso.
resource "azurerm_role_assignment" "vmss_key_vault_secrets_read" {
  scope                = azurerm_key_vault.app.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_linux_virtual_machine_scale_set.app.identity[0].principal_id
  principal_type       = "ServicePrincipal"
}

# Solo quien ejecuta Terraform administra los secretos; la app conserva su rol de lectura.
resource "azurerm_role_assignment" "terraform_key_vault_secrets_officer" {
  scope                = azurerm_key_vault.app.id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = data.azurerm_client_config.current.object_id
}

resource "azurerm_key_vault_secret" "demo" {
  name            = "caribeshop-demo"
  key_vault_id    = azurerm_key_vault.app.id
  content_type    = "text/plain"
  expiration_date = var.key_vault_demo_secret_expiration

  value_wo         = var.key_vault_demo_secret_value
  value_wo_version = 1 # Incrementar al rotar el valor.

  depends_on = [azurerm_role_assignment.terraform_key_vault_secrets_officer]
}
