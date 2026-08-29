#!/usr/bin/env python3
"""
BK-1191 Saved Search to Detection Rule Converter
Converts saved search JSON exports into YAML detection rule templates
ready for review.
"""

import os
import sys
import json
import uuid
import re
from datetime import datetime
from glob import glob

print("🔄 BK-1191 Saved Search to Detection Rule Converter")
print("=" * 55)

# Create stage-review/up-for-review directory for converted rules
os.makedirs('detections/stage-review/up-for-review', exist_ok=True)
os.makedirs('conversion_reports', exist_ok=True)

def extract_mitre_info(notes_text):
    """Extract MITRE ATT&CK information from notes"""
    tactic = ""
    technique = ""

    # Look for MITRE patterns in notes (various formats)
    if "TA0" in notes_text:
        tactic_match = re.search(r'TA0\d{3}', notes_text)
        if tactic_match:
            tactic = tactic_match.group()

    if "T1" in notes_text:
        technique_match = re.search(r'T1\d{3}(?:\.\d{3})?', notes_text)
        if technique_match:
            technique = technique_match.group()

    # Also look for MITRE ATT&CK patterns with descriptions
    mitre_pattern = r'MITRE ATT&CK:\s*(TA\d{4})[^/]*(?:/[^/]*)*\s*(T\d{4}(?:\.\d{3})?)'
    mitre_match = re.search(mitre_pattern, notes_text)
    if mitre_match:
        tactic = mitre_match.group(1)
        technique = mitre_match.group(2)

    return tactic, technique

def extract_severity(notes_text):
    """Extract severity from notes, default to medium"""
    notes_lower = notes_text.lower()

    if any(word in notes_lower for word in ['critical', 'severe']):
        return 'critical'
    elif any(word in notes_lower for word in ['high']):
        return 'high'
    elif any(word in notes_lower for word in ['medium', 'moderate']):
        return 'medium'
    elif any(word in notes_lower for word in ['low']):
        return 'low'
    elif any(word in notes_lower for word in ['info', 'informational']):
        return 'informational'
    else:
        return 'medium'  # Default

def extract_vendor_from_name(name):
    """Extract vendor from rule name"""
    name_lower = name.lower()

    # Remove stage-review prefix for analysis
    clean_name = name.replace('stage-review-', '').lower()

    # Common vendor patterns
    if 'okta' in clean_name:
        return 'okta'
    elif 'palo alto' in clean_name or 'paloalto' in clean_name:
        return 'palo-alto'
    elif 'microsoft' in clean_name or 'azure' in clean_name or 'office365' in clean_name:
        return 'microsoft'
    elif 'aws' in clean_name:
        return 'aws'
    elif 'crowdstrike' in clean_name or 'falcon' in clean_name:
        return 'crowdstrike'
    elif 'meisgn' in clean_name:
        return 'meisgn'
    else:
        # Try to get first word as vendor
        first_word = clean_name.split('-')[0] if '-' in clean_name else clean_name.split()[0]
        return first_word if first_word else 'unknown'

def generate_rule_name(original_name):
    """Generate proper rule name in VENDOR-PRODUCT-INTENT format"""
    # Remove stage-review prefix
    clean_name = original_name.replace('stage-review-', '').replace('stage-review ', '')

    # Convert to uppercase and replace spaces with hyphens
    rule_name = clean_name.upper().replace(' ', '-').replace('--', '-')

    return rule_name

def extract_description(notes_text, rule_name):
    """Extract or generate description from notes"""
    lines = notes_text.split('\n')

    # Look for description in notes
    for line in lines:
        if 'description:' in line.lower():
            desc = line.split(':', 1)[1].strip()
            if desc:
                return desc

    # Look for detection logic explanation
    for line in lines:
        if 'detection logic' in line.lower() or 'this rule' in line.lower():
            # Take next few lines as description
            desc = line.strip().replace('//', '').strip()
            if desc and len(desc) > 20:
                return desc

    # Generate default description
    return f"This rule identifies suspicious activity patterns based on {rule_name.lower().replace('-', ' ')}"

def extract_parser_tags(query_string):
    """Extract parser tags from query logic"""
    parsers = []

    # Look for vendor/module patterns
    if '#Vendor' in query_string:
        vendor_match = re.search(r'#Vendor\s*=\s*["\']?([^"\'\s]+)["\']?', query_string)
        if vendor_match:
            parsers.append(vendor_match.group(1))

    if '#event.module' in query_string:
        module_match = re.search(r'#event\.module\s*=\s*["\']?([^"\'\s]+)["\']?', query_string)
        if module_match:
            parsers.append(module_match.group(1))

    if '#type' in query_string:
        type_match = re.search(r'#type\s*=\s*["\']?([^"\'\s]+)["\']?', query_string)
        if type_match:
            parsers.append(type_match.group(1))

    return list(set(parsers)) if parsers else ['unknown']

def extract_required_fields(query_string):
    """Extract required fields from query logic"""
    fields = []

    # Look for field patterns that are required
    field_patterns = [
        r'user\.name',
        r'user\.id',
        r'source\.ip',
        r'client\.ip',
        r'event\.action',
        r'event\.outcome',
        r'@timestamp'
    ]

    for pattern in field_patterns:
        if re.search(pattern, query_string):
            fields.append(pattern.replace(r'\.', '.'))

    return fields

def convert_saved_search_to_rule(json_file_path):
    """Convert a single saved search JSON to YAML detection rule"""

    print(f"\n🔄 Converting: {os.path.basename(json_file_path)}")

    # Read JSON file
    with open(json_file_path, 'r') as f:
        saved_search = json.load(f)

    # Extract data from saved search
    original_name = saved_search.get('name', 'Unknown Rule')
    yaml_template = saved_search.get('yaml_template', '')
    search_id = saved_search.get('id', 'unknown')

    # Parse the yaml_template to extract queryString and notes
    query_string = ""
    notes = ""

    if 'queryString:' in yaml_template:
        # Extract everything after 'queryString: |-'
        start_marker = 'queryString: |-'
        if start_marker in yaml_template:
            # Get the part after the start marker
            after_marker = yaml_template.split(start_marker, 1)[1]

            # Split into lines and get indented content
            lines = after_marker.split('\n')
            query_lines = []

            for line in lines:
                # Skip empty lines at the start
                if not query_lines and line.strip() == '':
                    continue

                # If line starts with 2+ spaces, it's part of the query
                if line.startswith('  '):
                    query_lines.append(line[2:])  # Remove 2-space indent
                elif line.strip() == '':  # Empty line within query
                    query_lines.append('')
                elif query_lines:  # Non-indented line after we started - end of query
                    break

            query_string = '\n'.join(query_lines).rstrip()

        # Extract notes from query comments (Section 6)
        if '// SECTION 6: Rule Notes' in query_string:
            notes_section = query_string.split('// SECTION 6: Rule Notes')[-1]
            notes = notes_section.strip()

    # Generate rule components
    vendor = extract_vendor_from_name(original_name)
    rule_name = generate_rule_name(original_name)
    severity = extract_severity(notes)
    tactic, technique = extract_mitre_info(notes)
    description = extract_description(notes, rule_name)
    parser_tags = extract_parser_tags(query_string)
    required_fields = extract_required_fields(query_string)

    # Build YAML detection rule
    detection_rule = {
        'id': str(uuid.uuid4()),
        'created_timestamp': datetime.now().isoformat() + 'Z',
        'modified_timestamp': datetime.now().isoformat() + 'Z',
        'vendor': vendor,
        'severity': severity,
        'state': 'tuning',
        'name': rule_name,
        'alert_type': 'detection',
        'context': {
            'description': description,
            'reference_urls': [],
            'notes': f"Converted from NGSIEM saved search: {original_name}",
            'related': []
        },
        'mitre': {
            'tactic': tactic,
            'technique': technique
        },
        'rule': {
            'tunable': True,
            'schedule': {
                'ingest_ts': False,
                'cron': '@every 1h',
                'lookback': '75m'
            },
            'parser': parser_tags,
            'required_fields': required_fields,
            'logic': query_string,
            'unit_tests': []
        },
        'conversion_metadata': {
            'original_saved_search_id': search_id,
            'original_name': original_name,
            'converted_at': datetime.now().isoformat() + 'Z',
            'conversion_script': 'saved_search_to_rule_converter.py'
        }
    }

    # Generate output filename
    safe_rule_name = "".join(c for c in rule_name.lower() if c.isalnum() or c in ('-', '_'))
    output_file = f"detections/stage-review/up-for-review/{safe_rule_name}.yml"

    # Write YAML file (manual formatting to avoid dependency)
    with open(output_file, 'w') as f:
        f.write(f"# Detection Rule Template (Converted from NGSIEM Saved Search)\n")
        f.write(f"# Original: {original_name}\n")
        f.write(f"# Converted: {datetime.now().isoformat()}\n\n")

        # Write main fields
        f.write(f'id: "{detection_rule["id"]}"\n')
        f.write(f'created_timestamp: "{detection_rule["created_timestamp"]}"\n')
        f.write(f'modified_timestamp: "{detection_rule["modified_timestamp"]}"\n')
        f.write(f'vendor: "{detection_rule["vendor"]}"\n')
        f.write(f'severity: {detection_rule["severity"]}\n')
        f.write(f'state: {detection_rule["state"]}\n')
        f.write(f'name: {detection_rule["name"]}\n')
        f.write(f'alert_type: {detection_rule["alert_type"]}\n\n')

        # Context section
        f.write('context:\n')
        f.write(f'  description: "{detection_rule["context"]["description"]}"\n')
        f.write(f'  reference_urls: {json.dumps(detection_rule["context"]["reference_urls"])}\n')
        f.write(f'  notes: "{detection_rule["context"]["notes"]}"\n')
        f.write(f'  related: {json.dumps(detection_rule["context"]["related"])}\n\n')

        # MITRE section
        f.write('mitre:\n')
        f.write(f'  tactic: "{detection_rule["mitre"]["tactic"]}"\n')
        f.write(f'  technique: "{detection_rule["mitre"]["technique"]}"\n\n')

        # Rule section
        f.write('rule:\n')
        f.write(f'  tunable: {str(detection_rule["rule"]["tunable"]).lower()}\n')
        f.write('  schedule:\n')
        f.write(f'    ingest_ts: {str(detection_rule["rule"]["schedule"]["ingest_ts"]).lower()}\n')
        f.write(f'    cron: "{detection_rule["rule"]["schedule"]["cron"]}"\n')
        f.write(f'    lookback: {detection_rule["rule"]["schedule"]["lookback"]}\n')
        f.write(f'  parser: {json.dumps(detection_rule["rule"]["parser"])}\n')
        f.write(f'  required_fields: {json.dumps(detection_rule["rule"]["required_fields"])}\n')
        f.write('  logic: |-\n')

        # Write query logic with proper indentation
        for line in detection_rule["rule"]["logic"].split('\n'):
            f.write(f'    {line}\n')

        f.write(f'  unit_tests: {json.dumps(detection_rule["rule"]["unit_tests"])}\n\n')

        # Conversion metadata
        f.write('conversion_metadata:\n')
        f.write(f'  original_saved_search_id: "{detection_rule["conversion_metadata"]["original_saved_search_id"]}"\n')
        f.write(f'  original_name: "{detection_rule["conversion_metadata"]["original_name"]}"\n')
        f.write(f'  converted_at: "{detection_rule["conversion_metadata"]["converted_at"]}"\n')
        f.write(f'  conversion_script: "{detection_rule["conversion_metadata"]["conversion_script"]}"\n')

    print(f"  ✅ Generated: {output_file}")
    print(f"     📝 Rule Name: {rule_name}")
    print(f"     🏷️  Vendor: {vendor}")
    print(f"     ⚠️  Severity: {severity}")
    print(f"     🎯 MITRE: {tactic}/{technique}" if tactic or technique else "     🎯 MITRE: Not specified")

    return {
        'original_file': json_file_path,
        'output_file': output_file,
        'rule_name': rule_name,
        'vendor': vendor,
        'severity': severity,
        'mitre_tactic': tactic,
        'mitre_technique': technique
    }

# Main conversion process
print("🔍 Finding saved search JSON files...")
json_files = glob('detections/stage-review/from-ngsiem/*.json')

if not json_files:
    print("❌ No JSON files found in detections/stage-review/from-ngsiem/")
    sys.exit(1)

print(f"📋 Found {len(json_files)} saved search files to convert")

converted_rules = []

for json_file in json_files:
    try:
        result = convert_saved_search_to_rule(json_file)
        converted_rules.append(result)
    except Exception as e:
        print(f"  ❌ Error converting {json_file}: {e}")
        converted_rules.append({
            'original_file': json_file,
            'output_file': 'FAILED',
            'error': str(e)
        })

# Generate conversion report
conversion_report = {
    'timestamp': datetime.now().isoformat(),
    'total_files_processed': len(json_files),
    'successful_conversions': len([r for r in converted_rules if 'error' not in r]),
    'failed_conversions': len([r for r in converted_rules if 'error' in r]),
    'converted_rules': converted_rules
}

report_file = f"conversion_reports/saved_search_conversion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(report_file, 'w') as f:
    json.dump(conversion_report, f, indent=2)

# Display summary
print(f"\n📊 Conversion Complete!")
print(f"   📁 Files processed: {len(json_files)}")
print(f"   ✅ Successful conversions: {conversion_report['successful_conversions']}")
print(f"   ❌ Failed conversions: {conversion_report['failed_conversions']}")
print(f"   📋 Report: {report_file}")

print(f"\n📂 Detection rules ready for review:")
for rule in converted_rules:
    if 'error' not in rule:
        output_name = os.path.basename(rule['output_file'])
        print(f"   ├── {output_name}")

print(f"\n🎯 Next Steps:")
print(f"   1. Review rules in detections/stage-review/up-for-review/")
print(f"   2. Validate logic and tune parameters")
print(f"   3. Add unit tests")
print(f"   4. Move validated rules to detections/stage-validate/")

print(f"\n✨ All detection rules organized in stage-review/up-for-review/ folder!")