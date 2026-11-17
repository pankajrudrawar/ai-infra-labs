# Optional: a small VM to run the demo app inside the VNet. No public IP: you connect
# through Bastion Developer (free) in the portal, and it reaches the internet through NAT.

resource "azurerm_public_ip" "nat" {
  count               = var.create_test_vm ? 1 : 0
  name                = "pip-${var.prefix}-nat"
  location            = var.regions.primary
  resource_group_name = azurerm_resource_group.lab.name
  allocation_method   = "Static"
  sku                 = "Standard"
  tags                = var.tags
}

resource "azurerm_nat_gateway" "nat" {
  count               = var.create_test_vm ? 1 : 0
  name                = "nat-${var.prefix}"
  location            = var.regions.primary
  resource_group_name = azurerm_resource_group.lab.name
  tags                = var.tags
}

resource "azurerm_nat_gateway_public_ip_association" "nat" {
  count                = var.create_test_vm ? 1 : 0
  nat_gateway_id       = azurerm_nat_gateway.nat[0].id
  public_ip_address_id = azurerm_public_ip.nat[0].id
}

resource "azurerm_subnet_nat_gateway_association" "app" {
  count          = var.create_test_vm ? 1 : 0
  subnet_id      = azurerm_subnet.app["primary"].id
  nat_gateway_id = azurerm_nat_gateway.nat[0].id
}

resource "azurerm_network_interface" "vm" {
  count               = var.create_test_vm ? 1 : 0
  name                = "nic-${var.prefix}-vm"
  location            = var.regions.primary
  resource_group_name = azurerm_resource_group.lab.name
  tags                = var.tags

  ip_configuration {
    name                          = "internal"
    subnet_id                     = azurerm_subnet.app["primary"].id
    private_ip_address_allocation = "Dynamic"
  }
}

resource "azurerm_linux_virtual_machine" "vm" {
  count                 = var.create_test_vm ? 1 : 0
  name                  = "vm-${var.prefix}"
  location              = var.regions.primary
  resource_group_name   = azurerm_resource_group.lab.name
  size                  = "Standard_B2s"
  admin_username        = "azureuser"
  network_interface_ids = [azurerm_network_interface.vm[0].id]
  tags                  = var.tags

  admin_ssh_key {
    username   = "azureuser"
    public_key = var.ssh_public_key
  }

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.app.id]
  }

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Standard_LRS"
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "ubuntu-24_04-lts"
    sku       = "server"
    version   = "latest"
  }

  custom_data = base64encode(<<-CLOUDINIT
    #cloud-config
    package_update: true
    packages: [python3-venv, git, redis-tools]
    runcmd:
      - git clone ${var.repo_url} /opt/ai-infra-labs
      - python3 -m venv /opt/venv
      - /opt/venv/bin/pip install -r /opt/ai-infra-labs/scenarios/09-enterprise-ai-caching/app/requirements.txt
      - chown -R azureuser /opt/ai-infra-labs /opt/venv
    CLOUDINIT
  )

  lifecycle {
    precondition {
      condition     = length(var.ssh_public_key) > 0
      error_message = "Set ssh_public_key, or set create_test_vm = false."
    }
  }
}

resource "azurerm_bastion_host" "dev" {
  count               = var.create_test_vm ? 1 : 0
  name                = "bas-${var.prefix}"
  location            = var.regions.primary
  resource_group_name = azurerm_resource_group.lab.name
  sku                 = "Developer"
  virtual_network_id  = azurerm_virtual_network.vnet["primary"].id
  tags                = var.tags
}
