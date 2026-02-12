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

variable "architecture" {
  default = "x86_64"
  type    = string
}

variable "artifacts_bucket" {
  type = string
}

variable "default_timezone" {
  default = "UTC"
  type    = string
}

variable "debug" {
  default = false
  type    = bool
}

variable "jwt_secret_ssm_param_name" {
  type = string
}

variable "lambda_hash" {
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

variable "requirements_layer_hash" {
  type = string
}

variable "tags" {
  type = map(string)
}