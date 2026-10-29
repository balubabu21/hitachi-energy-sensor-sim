locals {
  name   = "${var.project}-${var.environment}"
  suffix = random_string.suffix.result
  tags   = merge(var.tags, { environment = var.environment })
}

resource "random_string" "suffix" {
  length  = 5
  upper   = false
  special = false
}

resource "azurerm_resource_group" "this" {
  name     = "rg-${local.name}"
  location = var.location
  tags     = local.tags
}

resource "azurerm_log_analytics_workspace" "this" {
  name                = "log-${local.name}-${local.suffix}"
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = local.tags
}

# ---------------------------------------------------------------- Container registry
resource "azurerm_container_registry" "this" {
  name                = "acr${var.project}${var.environment}${local.suffix}"
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name
  sku                 = "Basic"
  admin_enabled       = false
  tags                = local.tags
}

# Identity the container apps use to pull images (no registry passwords)
resource "azurerm_user_assigned_identity" "apps" {
  name                = "id-${local.name}-apps"
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name
  tags                = local.tags
}

resource "azurerm_role_assignment" "acr_pull" {
  scope                = azurerm_container_registry.this.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.apps.principal_id
}

# ---------------------------------------------------------------- Container Apps
resource "azurerm_container_app_environment" "this" {
  name                       = "cae-${local.name}"
  location                   = azurerm_resource_group.this.location
  resource_group_name        = azurerm_resource_group.this.name
  log_analytics_workspace_id = azurerm_log_analytics_workspace.this.id
  tags                       = local.tags
}

resource "azurerm_container_app" "backend" {
  name                         = "ca-${local.name}-api"
  container_app_environment_id = azurerm_container_app_environment.this.id
  resource_group_name          = azurerm_resource_group.this.name
  revision_mode                = "Single"
  workload_profile_name        = "Consumption"
  tags                         = local.tags

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.apps.id]
  }

  registry {
    server   = azurerm_container_registry.this.login_server
    identity = azurerm_user_assigned_identity.apps.id
  }

  # Internal only: reachable from the frontend inside the environment, not from the internet
  ingress {
    external_enabled = false
    target_port      = 8000
    transport        = "http"
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  template {
    min_replicas = var.min_replicas
    max_replicas = var.max_replicas

    container {
      name   = "api"
      image  = "${azurerm_container_registry.this.login_server}/backend:${var.image_tag}"
      cpu    = 0.25
      memory = "0.5Gi"

      env {
        name  = "PORT"
        value = "8000"
      }

      liveness_probe {
        transport = "HTTP"
        port      = 8000
        path      = "/api/health"
      }

      readiness_probe {
        transport = "HTTP"
        port      = 8000
        path      = "/api/health"
      }
    }

    http_scale_rule {
      name                = "http"
      concurrent_requests = "50"
    }
  }

  depends_on = [azurerm_role_assignment.acr_pull]
}

resource "azurerm_container_app" "frontend" {
  name                         = "ca-${local.name}-web"
  container_app_environment_id = azurerm_container_app_environment.this.id
  resource_group_name          = azurerm_resource_group.this.name
  revision_mode                = "Single"
  workload_profile_name        = "Consumption"
  tags                         = local.tags

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.apps.id]
  }

  registry {
    server   = azurerm_container_registry.this.login_server
    identity = azurerm_user_assigned_identity.apps.id
  }

  ingress {
    external_enabled = true
    target_port      = 3000
    transport        = "auto"
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  template {
    min_replicas = var.min_replicas
    max_replicas = var.max_replicas

    container {
      name   = "web"
      image  = "${azurerm_container_registry.this.login_server}/frontend:${var.image_tag}"
      cpu    = 0.5
      memory = "1Gi"

      # Next.js route handler proxies /api/* to the internal backend at runtime
      env {
        name  = "BACKEND_URL"
        value = "https://${azurerm_container_app.backend.ingress[0].fqdn}"
      }
    }

    http_scale_rule {
      name                = "http"
      concurrent_requests = "50"
    }
  }

  depends_on = [azurerm_role_assignment.acr_pull]
}
