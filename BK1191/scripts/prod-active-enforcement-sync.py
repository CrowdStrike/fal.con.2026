#!/usr/bin/env python3
"""
Production Active Enforcement & Sync (No external dependencies)
Enforces prod-active branch as authority for NGSIEM correlation rules.
Syncs rules, validates, and maintains prod-archive for deprecated rules.
"""

import sys
import json
import os
import urllib.request
import urllib.parse
from pathlib import Path
from datetime import datetime, timezone

# Configuration
PROD_ACTIVE_DIR = Path("/tmp/daac-ngsiem-testing/detections/prod-active")
PROD_ARCHIVE_DIR = Path("/tmp/daac-ngsiem-testing/detections/prod-archive")
BASE_URL = os.getenv("BASE_URL", "https://api.example.com")


def get_access_token(client_id, client_secret):
    """Get OAuth2 access token from API."""
    print("[INIT] Authenticating with API...")

    url = f"{BASE_URL}/oauth2/token"
    payload = urllib.parse.urlencode({
        "client_id": client_id,
        "client_secret": client_secret
    }).encode('utf-8')

    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    try:
        req = urllib.request.Request(url, data=payload, headers=headers)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            token = data.get("access_token")
            if token:
                print("[INIT] ✓ Connected to API\n")
                return token
            else:
                print(f"[ERROR] No access token in response: {data}")
                sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Authentication failed: {e}")
        sys.exit(1)


def query_active_rules(access_token):
    """Query all active rules from NGSIEM."""
    print("[SYNC] Querying NGSIEM for active rules...")

    url = f"{BASE_URL}/correlation-rules/combined/rules/v2?filter=status%3A%22active%22&limit=5000"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    try:
        req = urllib.request.Request(url, headers=headers, method='GET')
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            rules = data.get("resources", [])
            print(f"[SYNC] Found {len(rules)} active rules in NGSIEM\n")
            return rules
    except Exception as e:
        print(f"[ERROR] Failed to query NGSIEM: {e}")
        sys.exit(1)


def get_rules_by_name(ngsiem_rules):
    """Index NGSIEM rules by name."""
    rules_by_name = {}
    for rule in ngsiem_rules:
        rule_name = rule.get("name", "unknown")
        rules_by_name[rule_name] = rule

    print(f"[SYNC] Indexed {len(rules_by_name)} rules by name from NGSIEM")
    return rules_by_name


def get_prod_active_rules():
    """Read all rules from prod-active directory."""
    prod_rules = {}

    if not PROD_ACTIVE_DIR.exists():
        print(f"[ERROR] prod-active directory not found: {PROD_ACTIVE_DIR}")
        return prod_rules

    for rule_dir in PROD_ACTIVE_DIR.iterdir():
        if rule_dir.is_dir() and (rule_dir / f"{rule_dir.name}.json").exists():
            json_file = rule_dir / f"{rule_dir.name}.json"
            try:
                with open(json_file, 'r') as f:
                    rule_data = json.load(f)
                    rule_name = rule_dir.name
                    prod_rules[rule_name] = rule_data
            except Exception as e:
                print(f"[WARN] Error reading {json_file}: {e}")

    print(f"[SYNC] Found {len(prod_rules)} rules in prod-active\n")
    return prod_rules


def push_missing_rules(access_token, prod_rules, ngsiem_rules):
    """Push rules from prod-active that are missing from NGSIEM."""
    missing_rules = []

    for rule_name, rule_data in prod_rules.items():
        if rule_name not in ngsiem_rules:
            missing_rules.append((rule_name, rule_data))

    if not missing_rules:
        print("[SYNC] ✓ All prod-active rules present in NGSIEM\n")
        return

    print(f"[PUSH] Pushing {len(missing_rules)} missing rules to NGSIEM...\n")

    url = f"{BASE_URL}/correlation-rules/entities/rules/v1"

    for rule_name, rule_data in missing_rules:
        try:
            if "resources" in rule_data and len(rule_data["resources"]) > 0:
                rule = rule_data["resources"][0].copy()
                rule["status"] = "active"

                print(f"[PUSH]   → {rule_name}")

                payload = json.dumps({"resources": [rule]}).encode('utf-8')
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                }

                req = urllib.request.Request(url, data=payload, headers=headers, method='POST')
                with urllib.request.urlopen(req) as response:
                    print(f"[PUSH]   ✓ Successfully pushed {rule_name}")
        except Exception as e:
            print(f"[PUSH]   ✗ Error pushing {rule_name}: {e}")

    print()


def find_mismatched_rules(prod_rules, ngsiem_rules):
    """Find rules that exist in NGSIEM but don't match prod-active."""
    mismatched = []

    for rule_name, ngsiem_rule in ngsiem_rules.items():
        if rule_name not in prod_rules:
            mismatched.append((rule_name, ngsiem_rule))

    return mismatched


def deactivate_and_archive(access_token, mismatched_rules):
    """Deactivate mismatched rules in NGSIEM and archive them to prod-archive."""
    if not mismatched_rules:
        print("[SYNC] ✓ No mismatched rules found\n")
        return

    print(f"[ARCHIVE] Processing {len(mismatched_rules)} mismatched rules...\n")

    url = f"{BASE_URL}/correlation-rules/entities/rules/v1"
    archived_count = 0

    for rule_name, rule_data in mismatched_rules:
        try:
            rule_data["status"] = "inactive"
            print(f"[ARCHIVE]  → {rule_name}")

            # Try to deactivate in NGSIEM
            deactivated = False
            try:
                payload = json.dumps({"resources": [rule_data]}).encode('utf-8')
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                }

                req = urllib.request.Request(url, data=payload, headers=headers, method='POST')
                with urllib.request.urlopen(req) as response:
                    print(f"[ARCHIVE]  ✓ Deactivated in NGSIEM")
                    deactivated = True
            except urllib.error.HTTPError as http_err:
                if http_err.code == 401:
                    print(f"[ARCHIVE]  ⚠ NGSIEM deactivation blocked (401 Unauthorized - insufficient permissions)")
                else:
                    print(f"[ARCHIVE]  ⚠ NGSIEM deactivation failed ({http_err.code})")

            # Always archive locally, regardless of NGSIEM deactivation status
            archive_dir = PROD_ARCHIVE_DIR / rule_name
            archive_dir.mkdir(parents=True, exist_ok=True)

            json_file = archive_dir / f"{rule_name}.json"
            with open(json_file, 'w') as f:
                json.dump({"resources": [rule_data]}, f, indent=2)

            archived_count += 1
            print(f"[ARCHIVE]  ✓ Archived {rule_name} to prod-archive")

        except Exception as e:
            print(f"[ARCHIVE]  ✗ Error processing {rule_name}: {e}")

    print(f"\n[ARCHIVE] Successfully archived {archived_count}/{len(mismatched_rules)} rules to prod-archive\n")


def main():
    """Main sync orchestration."""
    print("\n" + "=" * 80)
    print("PRODUCTION ACTIVE ENFORCEMENT & SYNC")
    print("=" * 80)
    print(f"Execution time: {datetime.now(timezone.utc).isoformat()}\n")

    # Get credentials
    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")

    if not client_id or not client_secret:
        print("[ERROR] CLIENT_ID and CLIENT_SECRET environment variables required")
        sys.exit(1)

    # Get access token
    access_token = get_access_token(client_id, client_secret)

    # Phase 1: Query NGSIEM
    ngsiem_rules_list = query_active_rules(access_token)
    ngsiem_rules = get_rules_by_name(ngsiem_rules_list)

    # Phase 2: Read prod-active
    prod_rules = get_prod_active_rules()

    # Phase 3: Push missing rules
    push_missing_rules(access_token, prod_rules, ngsiem_rules)

    # Phase 4: Find mismatched
    mismatched = find_mismatched_rules(prod_rules, ngsiem_rules)
    print(f"[SYNC] Found {len(mismatched)} rules in NGSIEM not in prod-active\n")

    # Phase 5: Deactivate and archive
    deactivate_and_archive(access_token, mismatched)

    print("=" * 80)
    print("SYNC COMPLETE")
    print("=" * 80 + "\n")
    sys.exit(0)


if __name__ == "__main__":
    main()
