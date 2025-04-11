import os
import sys
import json
import argparse
from datetime import datetime
from cloudflare import Cloudflare, APIError
from cloudflare.types.dns import Record, RecordDeleteResponse

def get_env(key):
    value = os.environ.get(key)
    if value is None or value.strip() == "":
        print(f"Error: Environment variable {key} cannot be empty.", file=sys.stderr)
        sys.exit(1)
    return value

def load_config():
    return {
        "CLOUDFLARE_EMAIL": get_env("CLOUDFLARE_EMAIL"),
        "CLOUDFLARE_API_KEY": get_env("CLOUDFLARE_API_KEY"),
        "ZONE_ID": get_env("ZONE_ID"),
    }

def get_all_dns_records(cf: Cloudflare, zone_id: str) -> list[Record]:
    try:
        records_iterator = cf.dns.records.list(zone_id=zone_id)
        records_list = list(records_iterator)
        return records_list
    except APIError as e:
        print(f"Error fetching DNS records: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred while fetching DNS records: {e}", file=sys.stderr)
        sys.exit(1)


def find_dns_record(name: str, record_type: str, records: list[Record]) -> Record | None:
    for record in records:
        if record.name == name and record.type == record_type:
            return record
    return None

def create_dns_record(cf: Cloudflare, zone_id: str, record_type: str, name: str, content: str, proxied: bool):
    print(f"Attempting to create {record_type} record for {name} -> {content} (Proxied: {proxied})...")
    try:
        created_record = cf.dns.records.create(
            zone_id=zone_id,
            type=record_type,
            name=name,
            content=content,
            proxied=proxied,
        )
        print(f"Successfully created record (ID: {created_record.id}).")
        return created_record
    except APIError as e:
        print(f"Error creating DNS record: {e}", file=sys.stderr)
        if "already exists" in str(e):
            print("Hint: A record with this name and type might already exist.")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred while creating DNS record: {e}", file=sys.stderr)
        sys.exit(1)

def update_dns_record(cf: Cloudflare, zone_id: str, dns_record_id: str, record_type: str, name: str, content: str, proxied: bool):
    print(f"Attempting to update record {name} (ID: {dns_record_id}) -> {content} (Proxied: {proxied})...")
    try:
        updated_record = cf.dns.records.update(
            dns_record_id=dns_record_id,
            zone_id=zone_id,
            type=record_type,
            name=name,
            content=content,
            proxied=proxied,
        )
        print("Successfully updated record.")
        return updated_record
    except APIError as e:
        print(f"Error updating DNS record: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred while updating DNS record: {e}", file=sys.stderr)
        sys.exit(1)

def delete_dns_record(cf: Cloudflare, zone_id: str, dns_record_id: str, record_name: str):
    print(f"Attempting to delete record {record_name} (ID: {dns_record_id})...")
    try:
        delete_result: RecordDeleteResponse = cf.dns.records.delete(
            dns_record_id=dns_record_id,
            zone_id=zone_id
        )
        # The delete response object directly contains the id
        if delete_result and delete_result.id == dns_record_id:
            print(f"Successfully deleted record {record_name}.")
            return True
        else:
            # This case might indicate an unexpected API response format
            print(f"Warning: Delete operation completed but response format was unexpected for {record_name}. Please verify.", file=sys.stderr)
            return False
    except APIError as e:
        print(f"Error deleting DNS record: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred while deleting DNS record: {e}", file=sys.stderr)
        sys.exit(1)


def handle_add_or_update(cf: Cloudflare, zone_id: str, args: argparse.Namespace):
    record_name = args.record_name
    ip_address = args.ip_address
    proxied = args.proxy
    record_type = "A"

    print(f"Fetching existing records for zone {zone_id}...")
    all_records = get_all_dns_records(cf, zone_id)

    print(f"Searching for existing {record_type} record named '{record_name}'...")
    existing_record = find_dns_record(record_name, record_type, all_records)

    if existing_record:
        print(f"Found existing record (ID: {existing_record.id}, IP: {existing_record.content}, Proxied: {existing_record.proxied}).")
        if existing_record.content == ip_address and existing_record.proxied == proxied:
            print("Record already exists with the correct IP and proxy status. No changes needed.")
        else:
            update_dns_record(cf, zone_id, existing_record.id, record_type, record_name, ip_address, proxied)
    else:
        print(f"No existing {record_type} record found for '{record_name}'. Creating new record...")
        create_dns_record(cf, zone_id, record_type, record_name, ip_address, proxied)

def handle_remove(cf: Cloudflare, zone_id: str, args: argparse.Namespace):
    record_name = args.record_name
    record_type = "A"

    print(f"Fetching existing records for zone {zone_id}...")
    all_records = get_all_dns_records(cf, zone_id)

    print(f"Searching for existing {record_type} record named '{record_name}'...")
    existing_record = find_dns_record(record_name, record_type, all_records)

    if existing_record:
        print(f"Found record to delete (ID: {existing_record.id}).")
        delete_dns_record(cf, zone_id, existing_record.id, record_name)
    else:
        print(f"Error: No {record_type} record found with the name '{record_name}'. Nothing to delete.", file=sys.stderr)
        sys.exit(1)

def handle_list(cf: Cloudflare, zone_id: str, args: argparse.Namespace):
    print(f"Fetching existing records for zone {zone_id}...")
    all_records = get_all_dns_records(cf, zone_id)

    if not all_records:
        print("No DNS records found for this zone.")
        return

    output_records = []
    for record in all_records:
        output_records.append({
            "id": record.id,
            "type": record.type,
            "name": record.name,
            "content": record.content,
            "proxied": record.proxied,
            "ttl": record.ttl,
            "created_on": record.created_on.isoformat() if record.created_on else None,
            "modified_on": record.modified_on.isoformat() if record.modified_on else None,
        })

    print(json.dumps(output_records, indent=2))


def main():
    config = load_config()

    try:
        cf = Cloudflare(
            api_email=config["CLOUDFLARE_EMAIL"],
            api_key=config["CLOUDFLARE_API_KEY"],
        )
    except Exception as e:
        print(f"Error initializing Cloudflare client: {e}", file=sys.stderr)
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Manage Cloudflare DNS records.")
    subparsers = parser.add_subparsers(dest="action", required=True, help="Action to perform")

    parser_add = subparsers.add_parser("add", help="Add or update an A record.")
    parser_add.add_argument("record_name", help="The full DNS record name (e.g., sub.domain.tld)")
    parser_add.add_argument("ip_address", help="The IP address for the A record.")
    parser_add.add_argument("--proxy", action="store_true", help="Enable Cloudflare proxy (orange cloud). Defaults to False.")
    parser_add.set_defaults(func=handle_add_or_update)

    parser_rm = subparsers.add_parser("rm", help="Remove an A record.")
    parser_rm.add_argument("record_name", help="The full DNS record name to remove (e.g., sub.domain.tld)")
    parser_rm.set_defaults(func=handle_remove)

    parser_list = subparsers.add_parser("list", help="List all DNS records for the zone.")
    parser_list.set_defaults(func=handle_list)

    args = parser.parse_args()
    args.func(cf, config["ZONE_ID"], args)


if __name__ == "__main__":
    main()
