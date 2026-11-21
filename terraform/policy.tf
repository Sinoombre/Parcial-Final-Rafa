# S5 - Azure Policy con efecto Deny
# Restringe las regiones permitidas para los recursos
# del grupo de recursos principal de CaribeShop.

resource "azurerm_resource_group_policy_assignment" "allowed_locations" {
  name         = "caribeshop-allowed-locations"
  display_name = "CaribeShop - Regiones permitidas"
  description  = "Restringe el despliegue a la region autorizada."

  resource_group_id = azurerm_resource_group.main.id

  policy_definition_id = "/providers/Microsoft.Authorization/policyDefinitions/e56962a6-4747-49cd-b67b-bf8b01975c4c"

  parameters = jsonencode({
    listOfAllowedLocations = {
      value = [var.location]
    }
  })
}
