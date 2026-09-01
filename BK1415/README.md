# Fusion SOAR Workflow Validator v2.2

Validates CrowdStrike Fusion SOAR workflow YAML files before import. Catches structural issues that cause silent import failures or break UI editing — the kinds of problems you only find out about after clicking "Import" and getting a cryptic error.

Two gates:
- **Local rule-based** (default) — fast, offline, no auth. 17 rules derived from real client import failures and runtime incidents.
- **Server-side** (opt-in via `--server-validate`) — calls the Fusion `validate_only=true` endpoint. Catches trigger-type-specific variable errors (e.g. `${Trigger.CompositeID}` used on an NG-SIEM Detection trigger) that only the server can see.

## Quick Start

```bash
# Local lint (offline)
python3 workflow_validator.py workflow.yaml

# Batch
python3 workflow_validator.py workflows/*.yaml

# Custom config
python3 workflow_validator.py --config .validator-config.yaml workflows/*.yaml

# Local lint + server-side validate_only=true (requires FALCON_* env)
python3 workflow_validator.py workflow.yaml --server-validate
```

## What It Checks

15 validation rules, all derived from real-world import failures and runtime incidents across client engagements:

- **Field placement** — the most common import blocker. Fields placed at the action level instead of inside `properties:` will fail silently or error on import.
- **Action structure** — custom actions missing required `class` fields.
- **SOAR payload size** — CreateLookupFile actions combining multiple SOAR page outputs in one CEL expression, risking Fusion's ~1MB message size limit at runtime.
- **SendEmail recipients** — SendEmail actions with empty `to: []` arrays cause an action node error and put the workflow into an error-disabled state. This is a common issue because the Fusion UI strips email addresses on export by default.
- **Output schemas** — inline query actions without `workflow_csv_header_fields` lose UI editability.
- **CreateCase limits** — field count and character length validation for case creation actions.
- **Pipe complexity** — flags LogScale queries that exceed safe pipe counts (accounting for case branches, strings, and regex).
- **Version constraints**, **duplicate fields**, **orphaned YAML**, and more.

Full rule list and configuration options are in [workflow-validation-guide.md](workflow-validation-guide.md).

## Installation

Requires Python 3.7+ and PyYAML.

```bash
git clone https://github.com/CrowdStrike/fal.con.2026.git
cd BK1415
cd fusion-workflow-validator
pip install pyyaml
```

## Usage

```bash
# Single file
python3 workflow_validator.py path/to/workflow.yaml

# Batch
python3 workflow_validator.py workflows/*.yaml

# With custom config
python3 workflow_validator.py --config .validator-config.yaml workflows/*.yaml

# With server-side validate_only=true gate
python3 workflow_validator.py workflow.yaml --server-validate
```

### Server-Side Validation (`--server-validate` / `-s`)

Calls `POST {FALCON_BASE_URL}/workflows/entities/definitions/v1?validate_only=true` after the local gate passes. Catches things the local validator cannot see:

- Trigger-type-specific variable references — e.g. `${Trigger.CompositeID}` is valid for EPP triggers but **not** for NG-SIEM Detection (use `${Trigger.Detection.DetectionID}`). Server returns code `2016`.
- Dangling trigger with no downstream action (code `2019`).
- Other schema-level issues the server discovers during parse.

Requires these env vars (loaded from `.env` walking up from CWD, or already-exported):

```
FALCON_CLIENT_ID=<your-client-id>
FALCON_CLIENT_SECRET=<your-client-secret>
FALCON_BASE_URL=https://api.crowdstrike.com
```

No network calls happen unless the flag is passed. Missing env only errors when you actually use `--server-validate`.

## Exit Codes

- **0** — no errors, safe to import
- **1** — validation errors found (local or server)
- **2** — script error, auth / network failure, or invalid usage

## Common Issues

### Invalid Action-Level Fields

Fields like `workflow_csv_header_fields` placed outside `properties:` will block import:

```yaml
# Wrong — import will fail
Step1ExtractMetadata:
    properties:
        alertId: ${data['Trigger.Detection.DetectionID']}
    workflow_csv_header_fields: []  # outside properties
    version_constraint: ~1

# Correct
Step1ExtractMetadata:
    properties:
        alertId: ${data['Trigger.Detection.DetectionID']}
        workflow_csv_header_fields: []  # inside properties
    version_constraint: ~1
```

### Empty SendEmail Recipients

Empty `to: []` arrays cause the workflow to fail at runtime with an action node error. The Fusion UI strips email addresses on export unless you explicitly check the option to retain them:

```yaml
# Wrong
SendEmail:
    properties:
        to: []

# Correct
SendEmail:
    properties:
        to:
            - someone@example.com
```

### Missing Output Schema

Without `workflow_csv_header_fields`, inline query actions can't be edited in the Fusion UI after import:

```yaml
# Will import, but you can't edit it in the UI afterward
Step1ExtractMetadata:
    properties:
        alertId: ${data['Trigger.Detection.DetectionID']}

# Add the field to keep UI editing working
Step1ExtractMetadata:
    properties:
        alertId: ${data['Trigger.Detection.DetectionID']}
        workflow_csv_header_fields: []
```

## CI/CD Integration

### GitLab CI

```yaml
validate-workflows:
  stage: test
  script:
    - pip install pyyaml
    - python3 workflow_validator.py workflows/*.yaml
  only:
    - merge_requests
```

### Pre-commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

for file in $(git diff --cached --name-only | grep '\.yaml$'); do
    if [[ $file == workflows/* ]]; then
        python3 workflow_validator.py "$file"
        if [ $? -ne 0 ]; then
            echo "Workflow validation failed for $file"
            exit 1
        fi
    fi
done
```

## Configuration

YAML-based config for enabling/disabling rules, adjusting thresholds, and controlling output format. See `.validator-config.yaml` for options.

## Maintainer Tooling

`scripts/fetch_all_activities.py` refreshes `src/workflow_validator/known_action_ids.yaml` (the built-in action allow-list) from a live CID via FalconPy. Append-only and idempotent. See [scripts/README.md](scripts/README.md). Not needed to run the validator.

## Author

Nathan Church (nathan.church@crowdstrike.com)

## Version

2.2.0 (May 2026)
