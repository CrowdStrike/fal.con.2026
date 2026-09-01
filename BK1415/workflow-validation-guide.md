# Fusion Workflow Validation Guide

Reference for all validation rules in the Fusion SOAR Workflow Validator. Each rule targets a specific class of import failure or runtime issue observed in real CrowdStrike Fusion deployments.

## Two Gates: Local vs. Server-Side

The validator has two independent gates, and they catch different classes of problem. Use both in combination for demo / client-deploy contexts.

| Gate | Flag | Needs auth? | What it catches | What it misses |
|------|------|-------------|-----------------|----------------|
| **Local rule-based** | (default) | No | Field placement, SendEmail recipients, CSV header issues, pipe limits, payload size, duplicate names, invalid variable subscripts, orphaned YAML, etc. (17 rules, all derived from real client import failures) | Trigger-type-specific variable references — e.g. `${Trigger.CompositeID}` on an NG-SIEM Detection trigger. Schema-level issues the server discovers at parse time. |
| **Server-side `validate_only=true`** | `--server-validate` / `-s` | Yes (FALCON_CLIENT_ID / SECRET / BASE_URL) | Trigger-scoped variable namespaces, dangling triggers (code 2019), unknown variable references (code 2016), other server-parse errors | Project-specific conventions, runtime-volume issues (payload size), maintainability concerns. |

**Recommended workflow:**

```bash
# 1. Fast local lint during development
python3 workflow_validator.py my-workflow.yaml

# 2. Before deploy, run the full combined gate
python3 workflow_validator.py my-workflow.yaml --server-validate
```

Exit `0` only when both gates pass. Exit `1` if either reports errors. Exit `2` if the server gate cannot run (missing env, 401, network).

## Validation Rules

### FIELD_PLACEMENT (Critical)

The single most common import blocker. Fields placed at the action level instead of inside `properties:` will cause import failures.

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

Allowed action-level fields: `id`, `name`, `class`, `properties`, `version_constraint`, `output_schema`, `next`, `display`, `execution_cid`.

### REQUIRED_FIELDS (Critical)

Every workflow must have three root-level fields: `name`, `trigger`, `actions`. Missing any of these blocks import entirely.

### SENDEMAIL_RULES (Critical / Error)

Validates SendEmail actions have non-empty `to`, `subject`, and `msg` fields. Empty recipient arrays (`to: []`) cause an action node error and put the workflow into an error-disabled state. This is commonly seen because the Fusion UI strips email addresses on export by default.

Also validates email address format.

### ACTION_STRUCTURE (Critical / Info)

Checks that every action has an `id` field and that custom actions (non-built-in) include a `class` field.

An action is treated as **built-in** (no `class:` needed, INFO note suppressed) when its `id` matches an entry in `src/workflow_validator/known_action_ids.yaml`. That file ships with the validator and lists confirmed-global Fusion action UUIDs (Add comment to detection, Set detection status, Create variable, Update variable, Send Email, CreateCase, Append row to lookup file, etc.) plus the most common high-frequency UUIDs observed across client workflows. Composite ids of the form `<base>~<extension>` match on the base.

Custom / third-party integration actions (Charlotte AI, Entra, MSDefender, Abnormal Security, custom probes, etc.) are not in the allow-list and will still emit the INFO note, which is the correct behavior — those really do benefit from an explicit `class:` field.

Add new UUIDs to `known_action_ids.yaml` as new built-in actions are encountered.

### CREATECASE_FIELD_LIMITS (Error / Warning)

Validates CreateCase description fields against the Fusion Cases API constraint of 2,000 characters. Flags:
- Static strings over the limit
- Dynamic expressions without truncation guards (e.g., `format()` calls building descriptions from variable data)

Soft limit at 1,800 chars (90%) gives a buffer for dynamic content.

### INLINE_QUERY_PIPES (Error / Warning)

Counts top-level pipes in inline NG-SIEM queries against the LogScale API limit of 100. The counter skips `|` inside quoted strings, regex literals, and brace blocks to avoid false positives. Case branches incur additional penalties.

- Hard limit: 100 pipes
- Soft limit: 95 pipes (warning)

### INLINE_QUERY_SIZE (Error / Warning)

Checks inline query character count. Queries approaching ~26,000 characters hit a hard limit that causes Fusion 500 errors.

- Hard limit: 26,000 chars
- Soft limit: 25,000 chars (warning)

### MIXED_PRINT_FORMATS (Error)

Detects actions that mix the legacy `fields` array format with the newer `custom_json` format. Using both simultaneously causes unpredictable output.

### CSV_HEADER_FIELDS (Error / Info)

Inline query actions with an `output_schema` must also include `workflow_csv_header_fields` inside `properties`. Without it, query results may not flow correctly downstream.

### OUTPUT_SCHEMA (Warning / Error)

Validates that case risk assessment actions have a complete `output_schema` with all 8 required fields. Also checks that `workflow_csv_header_fields` is present alongside `output_schema`.

### TRIGGER_STRUCTURE (Error / Warning / Info)

Validates trigger configuration: event field presence for event-based triggers, parameter completeness, and type consistency.

### FIELD_NAMES (Warning)

Flags periods in property names (e.g., `remote.ip`). These cause import failures — use underscores or camelCase instead (`remote_ip`).

### DUPLICATE_ACTION_NAMES (Warning)

Flags duplicate action display names. Note: duplicate action *IDs* are allowed (Fusion creates these by design), but duplicate *names* make workflows harder to maintain.

### ORPHANED_YAML_FRAGMENTS (Warning)

Detects stray `- ${...}` list items that don't belong to any recognized list property. Usually indicates a copy/paste error or broken YAML structure.

### SOAR_PAYLOAD_SIZE (Error)

Detects CreateLookupFile actions that combine 2+ SOAR action outputs in one CEL expression. SOAR actions return full API response objects (often 10-40KB per item) and do NOT support `$select` to reduce payload size. With 50+ items per page, combined payloads routinely exceed Fusion's ~1MB message size limit, causing runtime `error_code 500 "message size is too large"`.

This is an ERROR (not WARNING) because it's a guaranteed runtime failure waiting for sufficient data volume — the workflow validates and deploys fine, but fails silently when actual data exceeds the limit.

```yaml
# Wrong — combines two SOAR pages in one CEL expression
CreateAlertLookupFile:
    class: CreateLookupFile
    properties:
        lookup_file_content_text: >-
            ${data["ListAlerts.API_Integration.SomeAPI.body.value"].map(...)
            + data["ListAlertsPage2.API_Integration.SomeAPI.body.value"].map(...)}

# Correct — one CreateLookupFile per SOAR page
CreateAlertLookupFileP1:
    class: CreateLookupFile
    properties:
        lookup_file_content_text: >-
            ${data["ListAlerts.API_Integration.SomeAPI.body.value"].map(...)}

CreateAlertLookupFileP2:
    class: CreateLookupFile
    properties:
        lookup_file_content_text: >-
            ${data["ListAlertsPage2.API_Integration.SomeAPI.body.value"].map(...)}
```

Route interleaved: `SOAR(page1) → CreateLookupFile_P1 → SOAR(page2) → CreateLookupFile_P2`. Update the downstream `Inline.QueryEvent` to accept multiple lookup file inputs and add a separate `case{}` branch per file.

## Configuration

Rules can be enabled/disabled and thresholds adjusted via `.validator-config.yaml`:

```yaml
rules:
  FIELD_PLACEMENT:
    enabled: true
  INLINE_QUERY_PIPES:
    enabled: true
    # soft_limit: 95
    # hard_limit: 100
  INLINE_QUERY_SIZE:
    enabled: true
    # soft_limit: 25000
    # hard_limit: 26000
```

## Usage

```bash
# Validate a single workflow (local only)
python3 workflow_validator.py workflow.yaml

# Batch validation
python3 workflow_validator.py workflows/*.yaml

# With custom config
python3 workflow_validator.py --config .validator-config.yaml workflows/*.yaml

# Local + server-side validate_only=true (requires FALCON_* env)
python3 workflow_validator.py workflow.yaml --server-validate
```

## Exit Codes

- **0** — no errors, safe to import
- **1** — validation errors found (local or server)
- **2** — script error, auth / network failure, or invalid usage

## Common Error Reference

| Error | Cause | Fix |
|-------|-------|-----|
| Invalid field placement | Unknown field outside `properties:` | Move into `properties:` block. Note: `default_name` is emitted by the Fusion UI on export and is allowed at action level (not flagged).
| Invalid variable subscript | `${Trigger.X.Y[N]}` integer subscript | Reference the whole array (`${Trigger.X.Y}`, renders comma-separated) or extract a single value via a `CreateVariable` action. `${data['Action.results'][N].field}` is a separate, valid pattern in property strings and `cel_expression` fields — not flagged.
| Empty SendEmail recipients | `to: []` from UI export | Add recipient addresses |
| Missing output schema fields | Incomplete case risk schema | Add all 8 required fields |
| Query results unavailable | Field name mismatch across query/schema/combine | Make names match exactly |
| Period in field name | `remote.ip` in schema | Use `remote_ip` instead |
| Missing version constraint | No `version_constraint` on action | Add `version_constraint: ~1` |
| Query too long | Inline query near 26k chars | Break into sub-queries or simplify |
| Too many pipes | Over 100 pipes in query | Reduce pipe stages or restructure |
| CreateCase description too long | Over 2,000 chars | Add truncation guard or shorten |
| SOAR multi-page lookup | 2+ SOAR outputs in one CreateLookupFile | Split into one CreateLookupFile per SOAR page |
