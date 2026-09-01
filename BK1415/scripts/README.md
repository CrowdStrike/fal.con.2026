# Maintainer scripts

Tooling for **maintaining** the validator — not needed to run it. End users
only need `pyyaml` and `workflow_validator.py`.

## `fetch_all_activities.py`

Enumerates every Falcon Fusion SOAR **action (activity)** the authenticated CID
exposes, via FalconPy (`Workflows.search_activities` →
`GET /workflows/combined/activities/v1`), and snapshots them to JSON + a summary.
Its primary job in this repo is to **refresh
`src/workflow_validator/known_action_ids.yaml`** — the allow-list of built-in
action UUIDs the `ActionStructure` rule uses to suppress `MISSING_ACTION_CLASS`.

### Why this exists

`known_action_ids.yaml` was hand-curated ("Add new entries here as new built-in
actions are encountered"). This script replaces the manual step: it pulls the
live catalog, filters to the cross-CID-stable platform core, and appends any
genuinely-new built-in IDs in a dated, reviewable block.

### Setup

```bash
pip install crowdstrike-falconpy        # in addition to the validator's pyyaml
```

Credentials are read from a `.env` (walked up from CWD, same pattern as the
validator's `--server-validate`), or already-exported env vars:

```
FALCON_CLIENT_ID=<client-id>
FALCON_CLIENT_SECRET=<client-secret>
FALCON_BASE_URL=https://api.crowdstrike.com   # or api.us-2.crowdstrike.com, eu-1, etc.
```

Required API scope: **Workflow:read**. The script is **read-only** against the
API (it only enumerates; it never creates or modifies workflows).

### Usage

```bash
# Full catalog snapshot (everything the CID exposes) to ./all_activities.json
python3 scripts/fetch_all_activities.py

# Portable platform-builtin core only (~150 actions, stable across CIDs)
python3 scripts/fetch_all_activities.py --stable-only

# Core + this CID's Foundry Functions / Global Command Engine commands
python3 scripts/fetch_all_activities.py --stable-only --include-foundry

# THE MAIN USE: refresh the validator's known_action_ids.yaml (append-only)
python3 scripts/fetch_all_activities.py \
    --update-known-ids src/workflow_validator/known_action_ids.yaml
```

`--update-known-ids` implies `--stable-only`, parses the existing IDs (including
composite `<base>~<suffix>` roots), and **appends only new IDs** in a dated block
— it never reorders or removes the curated entries above. Re-running is
idempotent (no new IDs → no change). Review the appended block, fix any unnamed
entries, and commit via MR.

### Filtering tiers

| Mode | Result | Use |
|---|---|---|
| *(default)* | Full catalog (thousands; incl. installed plugins, tenant content) | full inventory of a CID |
| `--stable-only` | ~150 platform builtins, ~148 identical across CIDs | portable reference / refresh source |
| `--stable-only --include-foundry` | core + `gce.command` + `faas` | per-CID capability incl. Foundry |

`--stable-only` drops: installed Store plugins (`plugin.*`), tenant
`http_request` connector configs (keeps only the 3 standard HTTP actions),
`custom_storage.*`, `rtr.custom_script`, `on_demand_workflow`,
`logscale.search_result`, `gce`/`faas` (unless `--include-foundry`), and
test/dummy fixtures.

### All flags

| Flag | Effect |
|---|---|
| `--limit N` | Pagination page size (default 500) |
| `--out-dir DIR` | Output directory (default: CWD) |
| `--skip-existing` | No-op if `all_activities.json` already exists |
| `--stable-only` | Portable platform-builtin core only |
| `--include-foundry` | With `--stable-only`, also include gce/faas |
| `--update-known-ids PATH` | Append new stable IDs into a `known_action_ids.yaml` (implies `--stable-only`) |
| `--date YYYY-MM-DD` | Date label for the appended block (default: today) |

### Notes & findings

- **Catalog, not usage.** This lists actions *available* to drop into a
  workflow, not actions *used* in existing workflows. (A CID with 14 workflows
  still exposes thousands of catalog actions.)
- **Count differences are tenant-specific, not cloud-specific.** Across a US-1
  and a US-2 CID, all standard `http_request` IDs are identical; the size
  difference is how built-out each tenant is (installed plugins, saved searches,
  GCE commands, Foundry functions). The `--stable-only` core is ~148 shared.
- **Glossary.** `faas` = Foundry Functions (per-tenant custom code as actions);
  `gce.command` = Global Command Engine (promoted RTR-style commands as actions).
  Both are platform *capabilities* but the individual actions are
  tenant-authored, hence excluded from the portable core by default.
- **US-2 is slow** (~13s/API call); a full pull is ~4 min. Progress prints per
  page.

### `sample-all_activities-stable.json`

A committed sample of the `--stable-only` output (148 actions from a lab CID),
kept at `tests/fixtures/sample-all_activities-stable.json`. It doubles as the
fixture for the offline drift check
(`tests/unit/test_known_action_ids_drift.py`), which fails if
`known_action_ids.yaml` falls behind the snapshot. Regenerate with:

```bash
python3 scripts/fetch_all_activities.py --stable-only --out-dir /tmp
cp /tmp/all_activities.json tests/fixtures/sample-all_activities-stable.json
```
