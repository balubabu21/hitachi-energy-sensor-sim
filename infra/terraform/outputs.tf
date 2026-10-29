output "frontend_url" {
  description = "Public URL of the web app."
  value       = "https://${azurerm_container_app.frontend.ingress[0].fqdn}"
}

output "backend_internal_url" {
  description = "Internal URL of the API (only reachable inside the Container Apps environment)."
  value       = "https://${azurerm_container_app.backend.ingress[0].fqdn}"
}

output "acr_name" {
  value = azurerm_container_registry.this.name
}

output "acr_login_server" {
  value = azurerm_container_registry.this.login_server
}

output "resource_group" {
  value = azurerm_resource_group.this.name
}
