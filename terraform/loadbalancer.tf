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
  sku                 = "Standard" # Load Balancer Standard

  frontend_ip_configuration {
    name                 = "public-ip-address"
    public_ip_address_id = azurerm_public_ip.ip_lb.id
  }
}

resource "azurerm_lb_backend_address_pool" "app" {
  name            = "lb-pool-app"
  loadbalancer_id = azurerm_lb.main.id
}

resource "azurerm_lb_probe" "health" {
  loadbalancer_id     = azurerm_lb.main.id
  name                = "health-probe"
  port                = 80
  protocol            = "Http"
  request_path        = "/health" # endpoint
  interval_in_seconds = 5
  number_of_probes    = 2
}

resource "azurerm_lb_rule" "http" {
  loadbalancer_id                = azurerm_lb.main.id
  name                           = "http-rule"
  protocol                       = "Tcp"
  frontend_port                  = 80
  backend_port                   = 80
  frontend_ip_configuration_name = "public-ip-address"
  backend_address_pool_ids       = [azurerm_lb_backend_address_pool.app.id]
  probe_id                       = azurerm_lb_probe.health.id
  disable_outbound_snat          = true
}
