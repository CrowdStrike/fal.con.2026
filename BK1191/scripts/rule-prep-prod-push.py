#!/usr/bin/env python3
"""
Rule Prep for Production Push
Stages validated YAML rules to prod-active with NGSIEM Rules API JSON format.
"""

import sys
import json
import shutil
from pathlib import Path
from datetime import datetime, timedelta


def convert_to_api_format(rule_name):
    """
    Convert rule to NGSIEM Rules API JSON format.

    Args:
        rule_name: Name of the rule

    Returns:
        dict: Rule in NGSIEM Rules API format
    """
    # Set start_on to 1 hour in future
    start_time = (datetime.utcnow() + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    # Set stop_on to 24 hours in future
    stop_time = (datetime.utcnow() + timedelta(hours=25)).strftime("%Y-%m-%dT%H:%M:%SZ")

    api_rule = {
        "resources": [
            {
                "name": rule_name,
                "description": f"Detection rule: {rule_name}",
                "tactic": "TAXXXX",
                "technique": "TXXXX",
                "severity": 0,
                "search": {
                    "outcome": "detection",
                    "filter": "| #repo=\"<repo>\" #Vendor=\"<vendor>\" #event.module=\"<module>\"\n| <field>=\"<value>\"\n| <additional_logic>\n",
                    "lookback": "1h0m"
                },
                "operation": {
                    "schedule": {
                        "definition": "@every 1h0m"
                    },
                    "start_on": start_time,
                    "stop_on": stop_time
                },
                "status": "active"
            }
        ]
    }

    return api_rule


def main():
    validated_dir = Path("/tmp/daac-ngsiem-testing/detections/stage-validate/approved")
    prod_active_dir = Path("/tmp/daac-ngsiem-testing/detections/prod-active")

    if not validated_dir.exists():
        print(f"Error: {validated_dir} not found")
        sys.exit(1)

    yaml_files = list(validated_dir.glob("*.yml"))

    if not yaml_files:
        print(f"No YAML files found in {validated_dir}")
        sys.exit(1)

    for yaml_file in yaml_files:
        rule_name = yaml_file.stem
        # Remove stage-review suffix if present
        if rule_name.endswith("-stage-review"):
            rule_name = rule_name.replace("-stage-review", "", 1)

        print(f"Processing: {yaml_file.name}")

        try:
            # Create rule subdirectory in prod-active
            rule_dir = prod_active_dir / rule_name
            rule_dir.mkdir(parents=True, exist_ok=True)

            # Copy YAML to prod-active
            shutil.copy(yaml_file, rule_dir / f"{rule_name}.yml")

            # Convert to API format and write JSON
            api_rule = convert_to_api_format(rule_name)
            json_file = rule_dir / f"{rule_name}.json"
            with open(json_file, 'w') as f:
                json.dump(api_rule, f, indent=2)

            print(f"✓ Staged {rule_name} to prod-active")

        except Exception as e:
            print(f"✗ Error processing {yaml_file.name}: {e}")
            sys.exit(1)

    print(f"\n✓ All {len(yaml_files)} rules staged to prod-active")
    sys.exit(0)


if __name__ == "__main__":
    main()
