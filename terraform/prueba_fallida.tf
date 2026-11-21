
resource "azurerm_network_security_group" "prueba_insegura" {
  name                = "nsg-prueba-insegura"
  location            = var.location
  resource_group_name = azurerm_resource_group.main.name

  security_rule {
    name                       = "Allow-SSH-Internet"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "22"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}
