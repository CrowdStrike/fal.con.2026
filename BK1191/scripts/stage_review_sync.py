#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BK-1191 Detection-as-Code Pipeline - Stage Review Sync

Modified from the working Colab notebook to save stage-review queries
to the detections/stage-review/ directory for the DAAC pipeline.
Uses standard library to avoid dependency issues.
"""

import os
import sys
import json
import uuid
import urllib.request
import urllib.parse
from datetime import datetime

# ============================================================
# Configuration
# ============================================================

client_id = "your-client-id"
client_secret = "your-client-secret"
base_url = "https://api.example.com"

print("🚀 BK-1191 Stage-Review Query Sync")
print("=" * 40)

# ============================================================
# Authentication
# ============================================================

print("🔑 Authenticating with Falcon API...")

auth_url = f"{base_url}/oauth2/token"
auth_data = urllib.parse.urlencode({
    'client_id': client_id,
    'client_secret': client_secret
}).encode('utf-8')

auth_headers = {
    'Content-Type': 'application/x-www-form-urlencoded',
    'Accept': 'application/json'
}

try:
    auth_request = urllib.request.Request(auth_url, data=auth_data, headers=auth_headers, method='POST')
    with urllib.request.urlopen(auth_request) as response:
        auth_result = json.loads(response.read().decode())

    if 'access_token' in auth_result:
        access_token = auth_result['access_token']
        print(f"✅ Authenticated successfully | Token: {access_token[:10]}...")
    else:
        print(f"❌ Authentication failed: {auth_result}")
        sys.exit(1)

except Exception as e:
    print(f"❌ Authentication error: {e}")
    sys.exit(1)

def get_headers():
    """Returns headers with current access token"""
    return {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

# ============================================================
# Pull stage-review Queries
# ============================================================

print("\n🔍 Checking for existing saved searches with 'stage-review'...")

existing_saved_queries = {}

# --- Step 1: Query for saved query IDs ---
query_ids_url = f"{base_url}/ngsiem-content/queries/savedqueries/v1?" + urllib.parse.urlencode({
    "search_domain": "all",
    "filter": "name:~'stage-review'",
    "limit": "100"
})

try:
    request = urllib.request.Request(query_ids_url, headers=get_headers(), method='GET')
    with urllib.request.urlopen(request) as response:
        saved_query_ids_response = json.loads(response.read().decode())

    saved_query_ids = saved_query_ids_response.get("resources", [])
    if saved_query_ids:
        print(f"  ✅ Found {len(saved_query_ids)} saved query ID(s) matching 'stage-review'")
        for sq_id in saved_query_ids:
            print(f"    📋 ID: {sq_id}")
    else:
        print("  ℹ️ No saved query IDs containing 'stage-review' found.")
        print("  💡 Create some saved searches in NGSIEM with 'stage-review' in the name to test the pipeline")
        sys.exit(0)

except Exception as e:
    print(f"  ❌ Failed to query saved query IDs: {e}")
    sys.exit(1)

# --- Step 2: Retrieve full saved query details using the IDs ---
if saved_query_ids:
    print("  📥 Fetching details for each saved query ID...")
    for sq_id in saved_query_ids:
        details_url = f"{base_url}/ngsiem-content/entities/savedqueries-template/v1?" + urllib.parse.urlencode({
            "ids": sq_id,
            "search_domain": "all"
        })

        try:
            request = urllib.request.Request(details_url, headers=get_headers(), method='GET')
            with urllib.request.urlopen(request) as response:
                saved_query_details_response = json.loads(response.read().decode())

            resources = saved_query_details_response.get("resources", [])
            if resources:
                sq_detail = resources[0]
                existing_saved_queries[sq_detail["name"]] = sq_detail
                print(f"    📄 Retrieved: {sq_detail['name']}")
            else:
                print(f"    ⚠️ No details found for ID: {sq_id}")

        except Exception as e:
            print(f"    ❌ Failed to retrieve details for ID {sq_id}: {e}")

    print(f"  ✅ Retrieved details for {len(existing_saved_queries)} saved query(s).")

# ============================================================
# Save to Stage-Review Directory
# ============================================================

if existing_saved_queries:
    print(f"\n💾 Saving {len(existing_saved_queries)} stage-review queries to files...")

    # Create directories
    os.makedirs('detections/stage-review/from-ngsiem', exist_ok=True)
    os.makedirs('sync_reports', exist_ok=True)

    processed_queries = []

    for sq_name, sq_detail in existing_saved_queries.items():
        print(f"\n📄 Processing: {sq_name}")

        # Generate safe filename
        safe_name = "".join(c for c in sq_name if c.isalnum() or c in ('-', '_', '.')).lower()

        # Extract query content from YAML template (simplified parsing)
        query_content = "# Query not available"
        if "yaml_template" in sq_detail:
            yaml_template = sq_detail["yaml_template"]
            # Simple search for queryString in YAML (avoiding yaml library dependency)
            if "queryString:" in yaml_template:
                lines = yaml_template.split('\n')
                for i, line in enumerate(lines):
                    if "queryString:" in line:
                        # Try to get the query content (may span multiple lines)
                        query_content = line.split("queryString:")[-1].strip()
                        if query_content.startswith('"') and query_content.endswith('"'):
                            query_content = query_content[1:-1]  # Remove quotes
                        elif query_content.startswith('|-') or query_content.startswith('>-'):
                            # Multi-line YAML string - get following indented lines
                            query_content = ""
                            for j in range(i + 1, len(lines)):
                                if lines[j].startswith('  '):  # Indented line
                                    query_content += lines[j][2:] + '\n'  # Remove 2-space indent
                                else:
                                    break
                        break

        # Save raw JSON data
        json_file = f"detections/stage-review/from-ngsiem/{safe_name}.json"
        with open(json_file, 'w') as f:
            json.dump(sq_detail, f, indent=2)
        print(f"  💾 Saved raw data: {json_file}")

        # Generate detection rule template
        rule_template = {
            'id': str(uuid.uuid4()),
            'created_timestamp': datetime.now().isoformat() + 'Z',
            'modified_timestamp': datetime.now().isoformat() + 'Z',
            'jira_issue': 'DETECT-1191',
            'vendor': sq_name.split('-')[0].lower() if '-' in sq_name else 'unknown',
            'severity': 'medium',
            'state': 'tuning',
            'tlp': 'green',
            'name': sq_name.replace('-stage-review', '').replace('stage-review-', ''),
            'alert_type': 'detection',
            'context': {
                'description': sq_detail.get('description', f"Detection rule from NGSIEM: {sq_name}"),
                'reference_urls': [],
                'notes': f"Original NGSIEM saved query imported from stage-review pipeline",
                'killbook': '',
                'related': []
            },
            'mitre': {
                'tactic': '',
                'technique': ''
            },
            'rule': {
                'tunable': True,
                'schedule': {
                    'ingest_ts': False,
                    'cron': '@every 1h',
                    'lookback': '75m'
                },
                'parser': [sq_name.split('-')[0].lower() if '-' in sq_name else 'unknown'],
                'required_fields': [],
                'logic': query_content,
                'unit_tests': []
            },
            'ngsiem_source': {
                'original_id': sq_detail.get('id'),
                'original_name': sq_name,
                'imported_at': datetime.now().isoformat() + 'Z',
                'api_endpoint': base_url
            }
        }

        # Save YAML rule template (manual formatting)
        yaml_file = f"detections/stage-review/from-ngsiem/{safe_name}.yml"
        with open(yaml_file, 'w') as f:
            f.write(f"# Detection Rule Template (Generated from NGSIEM Stage-Review)\n")
            f.write(f"# Original Query: {sq_name}\n")
            f.write(f"# Generated: {datetime.now().isoformat()}\n\n")

            # Write YAML-like structure manually
            for key, value in rule_template.items():
                if isinstance(value, dict):
                    f.write(f"{key}:\n")
                    for subkey, subvalue in value.items():
                        if isinstance(subvalue, dict):
                            f.write(f"  {subkey}:\n")
                            for subsubkey, subsubvalue in subvalue.items():
                                f.write(f"    {subsubkey}: {json.dumps(subsubvalue) if isinstance(subsubvalue, (list, dict)) else subsubvalue}\n")
                        else:
                            f.write(f"  {subkey}: {json.dumps(subvalue) if isinstance(subvalue, (list, dict)) else subvalue}\n")
                else:
                    f.write(f"{key}: {json.dumps(value) if isinstance(value, (list, dict)) else value}\n")

        print(f"  📝 Generated rule template: {yaml_file}")

        processed_queries.append({
            'name': sq_name,
            'id': sq_detail.get('id'),
            'json_file': json_file,
            'yaml_file': yaml_file,
            'query_content': query_content[:100] + '...' if len(query_content) > 100 else query_content
        })

    # Generate sync report
    sync_report = {
        'timestamp': datetime.now().isoformat(),
        'source': 'NGSIEM stage-review queries',
        'api_endpoint': base_url,
        'total_queries_found': len(existing_saved_queries),
        'processed_count': len(processed_queries),
        'processed_queries': processed_queries,
        'errors': []
    }

    report_file = f"sync_reports/stage_review_sync_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(sync_report, f, indent=2)

    # Display summary
    print(f"\n📊 Stage-Review Sync Complete!")
    print(f"   🎯 Queries found: {len(existing_saved_queries)}")
    print(f"   📁 Files created: {len(processed_queries) * 2}")
    print(f"   📋 Report: {report_file}")

    print(f"\n📂 Files created in detections/stage-review/from-ngsiem/:")
    for query in processed_queries:
        json_name = os.path.basename(query['json_file'])
        yaml_name = os.path.basename(query['yaml_file'])
        print(f"   ├── {json_name}")
        print(f"   ├── {yaml_name}")

    print(f"\n🎯 Next Steps:")
    print(f"   1. Review generated rule templates")
    print(f"   2. Run validation scripts")
    print(f"   3. Move validated rules to detections/stage-validate/")
    print(f"   4. Eventually promote to detections/prod-active/")

else:
    print("  ℹ️ No saved queries containing 'stage-review' found after retrieving details.")
    print("  💡 Create some saved searches in NGSIEM with 'stage-review' in the name to test the pipeline")