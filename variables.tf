variable "aws_region" {
  default = "eu-central-1"
  type    = string
}

variable "stage" {
  default = "dev"
  type    = string
}

variable "app_name" {
  default = "auth-service"
  type    = string
}

variable "app_timezone" {
  default = "UTC"
  type    = string
}

variable "cache_service_base_url" {
  type = string
}

variable "debug" {
  default = false
  type    = bool
}

variable "jwt_secret" {
  type = string
}

variable "log_level" {
  default = "INFO"
  type    = string
}

variable "power_tools_service_name" {
  default = "auth-service"
  type    = string
}
