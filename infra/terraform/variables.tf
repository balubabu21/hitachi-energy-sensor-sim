variable "subscription_id" {
  description = "Azure subscription ID to deploy into."
  type        = string
}

variable "project" {
  description = "Short project name used in resource names (lowercase letters/numbers)."
  type        = string
  default     = "hesensor"
  validation {
    condition     = can(regex("^[a-z0-9]{3,12}$", var.project))
    error_message = "project must be 3-12 lowercase letters or digits."
  }
}

variable "environment" {
  description = "Environment name (dev, test, prod)."
  type        = string
  default     = "dev"
}

variable "location" {
  description = "Azure region."
  type        = string
  default     = "uksouth"
}

variable "image_tag" {
  description = "Tag of the backend/frontend images in ACR. Set by scripts/deploy.sh."
  type        = string
  default     = "latest"
}

variable "min_replicas" {
  description = "Minimum replicas per app (0 = scale to zero when idle)."
  type        = number
  default     = 0
}

variable "max_replicas" {
  description = "Maximum replicas per app."
  type        = number
  default     = 3
}

variable "tags" {
  description = "Tags applied to every resource."
  type        = map(string)
  default = {
    workload = "hitachi-energy-sensor-simulator"
    managed  = "terraform"
  }
}
