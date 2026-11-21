resource "azurerm_public_ip" "ip_lb" {
  name                = "public-ip-lb-${var.suffix}"
  location            = var.location
  resource_group_name = var.resource_group_name
  allocation_method   = "Static"
  sku                 = "Standard"      # IP pública Standard
  zones               = ["1", "2", "3"] # zonal-redundante
}

resource "azurerm_lb" "main" {
  name                = "lb-${var.suffix}"
  location            = var.location
  resource_group_name = var.resource_group_name
  sku                 = "Standard"      # Load Balancer Standard

  frontend_ip_configuration {
    name                 = "public-ip-address"
    public_ip_address_id = azurerm_public_ip.ip_lb.id
  }
}
