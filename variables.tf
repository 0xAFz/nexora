variable "os_username" {
  description = "openstack username"
  type        = string
}

variable "os_tenant_name" {
  description = "openstack tenant name"
  type        = string
}

variable "os_password" {
  description = "openstack password"
  type        = string
  sensitive   = true
}

variable "os_auth_url" {
  description = "openstack authentication url"
  type        = string
}

variable "os_region_name" {
  description = "openstack region"
  type        = string
}

variable "public_key_path" {
  description = "public key path"
  type        = string
  default     = "~/.ssh/id_rsa.pub"
}

variable "machine_name" {
  description = "instance hostname"
  type        = string
  default     = "nexora"
}

variable "image_name" {
  description = "openstack os image"
  type        = string
}

variable "flavor_name" {
  description = "openstack flavor"
  type        = string
}

variable "network_name" {
  description = "openstack network"
  type        = string
}

variable "security_groups" {
  description = "openstack security groups list"
  type        = list(string)
  default     = ["allow_all"]
}
