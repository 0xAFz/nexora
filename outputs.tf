output "public_ip" {
  value       = openstack_compute_instance_v2.stargate.access_ip_v4
  description = "The public IP of instance"
}
