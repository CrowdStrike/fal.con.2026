# Fusion Workflow Validator — Roadmap

## Shipped

### v1.0 (Feb 2026)
Initial release. Basic structural validation of Fusion SOAR workflow YAML — field placement, empty recipients, missing schemas, field names, version constraints.

### v2.0 (Feb 2026)
Complete rewrite. Plugin-based rule architecture, parallel validation, rich CLI output, YAML configuration, precise error locations with YAML path tracking. Shipped with 13 validation rules.

### v2.1 (Mar 2026)
Added CreateCase field limits rule (#14), SOAR payload size rule (#15). Rewrote the pipe counter to correctly skip `|` inside strings, regex literals, and brace blocks. Added truncation guard detection for dynamic CreateCase descriptions.

---

## Current State (v2.1.1, 15 rules, 125 tests)

The validator is strong on **structural/YAML validation** — the things that block import. The biggest gap is **runtime behavior validation**: checking that the workflow will actually do what you expect once imported. "Imports fine, breaks at runtime" failures are currently invisible.

---

## New Validation Rules

Identified via fresh-eyes review of CrowdStrike Falcon docs (Fusion SOAR reference dc4f8c45), foundry-workflows-development skill, foundry-debugging-workflows skill, and personal learnings from OrangeNebula engagements.

### High Priority

#### `next` Graph Integrity
**Impact:** Dangling action references = runtime failure or dead branches.
**What:** Every action's `next:` list should reference actions that actually exist in the workflow. Also check that trigger `next:` points to valid first actions. Detect unreachable actions (nothing points to them).
**Source:** Foundry workflows skill documents `next:` as the flow control mechanism.
**Effort:** Medium — walk actions dict, build adjacency set, compare.

#### Condition Operator Validation
**Impact:** Invalid operators = workflow takes wrong path silently.
**What:** The Fusion docs enumerate exactly 12 condition operators. Validate that condition blocks use recognized operators and that operator/data-type combinations are compatible (e.g., `is greater than` only on ordinal/numeric data).
**Source:** Fusion SOAR docs, conditions reference section.
**Effort:** Medium — need to parse condition blocks, define operator allowlist.

#### Loop Variable Access Warnings
**Impact:** NULL variables inside loop bodies = silent failure.
**What:** Inside `loops:` blocks, bare action references like `${ActionName.field}` return NULL. Must use `data['ActionName.results.#'].field`. Detect bare references in loop contexts and warn.
**Source:** Personal learning `fusion-loop-context.md` — confirmed across Bulk Action Users and Defender Sync projects.
**Effort:** Medium — need to identify loop blocks, scan expressions within them.

### Medium Priority

#### `continue_on_error` on RTR Actions
**Impact:** False sense of error handling safety.
**What:** Flag `continue_on_error: true` on RTR actions (PutAndRunFile, RunScript, etc.) — this setting does NOT work for RTR. Downstream nodes are always skipped on RTR failure regardless.
**Source:** Personal learning `fusion-rtr-error-handling.md` — confirmed on Laroux Auto-Removal project, New Balance CID.
**Effort:** Low — check action class + `continue_on_error` flag.

#### Schedule Trigger Cron Validation
**Impact:** Invalid cron = workflow never fires (no error at import).
**What:** Schedule triggers need a valid cron expression in `schedule.time_cycle`. Validate basic cron syntax (5-field format).
**Source:** Fusion SOAR docs, foundry skill trigger types table.
**Effort:** Low — regex or simple cron parser.

#### The "0" Pagination Gotcha
**Impact:** Infinite loops in pagination workflows.
**What:** Loop conditions checking `WorkflowCustomVariable.next:!null` without also checking `:!'0'` create infinite loops. When a function omits a field, the workflow engine maps it to string `"0"`, not null.
**Source:** Foundry pagination-patterns.md reference.
**Effort:** Low — pattern match on loop conditions.

#### JSON/SARIF Output Mode
**Impact:** CI/CD adoption blocker — pipelines need machine-readable output.
**What:** Add `--format json` and `--format sarif` output modes. SARIF enables IDE integration (VS Code, IntelliJ). JSON enables pipeline parsing.
**Source:** Existing ROADMAP item, reinforced by this review.
**Effort:** Medium — new reporter class, wire up to CLI.

#### Config-Driven Thresholds
**Impact:** Rules hardcode limits that should be tunable per-project.
**What:** InlineQueryPipesRule, InlineQuerySizeRule, CreateCaseFieldLimitsRule all hardcode their thresholds. These should read from `ValidationConfig` so projects can adjust limits in `.validator-config.yaml`.
**Source:** Code review — config system exists but rules don't use it.
**Effort:** Low — pass config to rules, read thresholds from it.

### Lower Priority

#### Variable Reference Validation
**Impact:** References to nonexistent actions = runtime NULL.
**What:** Validate that `${data['ActionName.field']}` references point to actions that exist in the workflow. Complex to do well because variable syntax varies (CEL, FQL, template interpolation).
**Source:** Foundry workflows skill, personal learnings.
**Effort:** High — need comprehensive expression parser.

#### Platform Action ID Validation
**Impact:** Made-up IDs pass validation but fail at deploy.
**What:** Cross-reference action `id` fields against known platform action IDs. The foundry skill lists several verified IDs.
**Source:** Foundry workflows skill, action ID table.
**Effort:** High — needs maintained ID list, version sensitivity.

#### Array Condition Operator Warnings
**Impact:** Narrow but real — affects audit trigger workflows.
**What:** Flag `:~` (text match) or `:*` (wildcard) operators on known array fields. Only `includes` (`:['value']`) works on arrays.
**Source:** Personal learning `fusion-condition-array-handling.md`.
**Effort:** Low — but requires knowledge of which fields are arrays.

#### Condition Wildcard on CommandLine
**Impact:** `matches` with `*` on CommandLine validates but silently doesn't match at runtime when deployed via API.
**Source:** Personal learning `fusion-condition-wildcard-limitations.md`.
**Effort:** Low — flag specific field/operator combinations.

---

## Major Features (branch-worthy)

### Expand Beyond Workflows → "Falcon NG-SIEM Validator"

**Current state:** The validator only handles Fusion SOAR workflow YAML. But the same CQL query pitfalls that break workflows also break dashboards, correlation rules, and saved searches. The plugin architecture already supports this — rules are generic, models are generic, the registry is generic.

**Proposed rename:** `fusion-workflow-validator` → `falcon-ngsiem-validator` (or similar). The tool would validate any NG-SIEM artifact YAML, not just workflows.

**New artifact types:**

#### Dashboard YAML Validation
Dashboard widgets contain CQL queries with the same pitfalls as workflow inline queries, plus dashboard-specific issues:

| Rule | Severity | Description |
|------|----------|-------------|
| `table()` limit required | ERROR | Every `table()` must have `limit=10000`. Default is 200, silently caps output. |
| `sort()` limit required | ERROR | Every `sort()` must have `limit=10000`. Overrides upstream table limit if missing. |
| `groupBy()` limit check | WARNING | `groupBy(limit=N)` is NOT "top N" — flag low limits on chart widgets. Recommend `limit=max`. |
| `render-as: markdown` + empty string | ERROR | If a column uses `render-as: markdown` in `configured-columns`, flag any `case {}` branch that assigns `""` to that column. Empty strings break markdown rendering. |
| Widget `y` gap detection | WARNING | Widgets with `y > 0` in a section where no other widget occupies rows 0 to y-1 create blank space. |
| Missing `configured-columns` for hidden fields | INFO | Fields in `table()` that should be hidden (e.g., join keys like `case_id`, `Vendor.campaignId`) but lack `hidden: true`. |
| `?parameter` inside `join(query={...})` | ERROR | Dashboard parameters are NOT substituted inside sub-query blocks. Flag `?Param` references inside `join({...})` or `defineTable(query={...})`. |

#### Correlation Rule Validation
Correlation rules use CQL inline queries with the same sort/table/groupBy pitfalls. Rules TBD based on correlation rule YAML structure analysis.

#### Saved Search Validation
Saved searches are simpler (just a query string + time range) but benefit from the same CQL checks.

**Implementation approach:**
1. Add artifact type detection (workflow vs dashboard vs correlation rule) — inspect YAML structure (`$schema`, presence of `widgets:` vs `actions:`, etc.)
2. Create a `rules/dashboard/` subdirectory for dashboard-specific rules
3. Existing workflow rules stay in `rules/` unchanged
4. Shared CQL rules (table/sort limits, groupBy) go in `rules/cql/` and apply to all artifact types
5. CLI auto-detects artifact type, or user can specify `--type dashboard|workflow|correlation`

**Source:** PurpleTunnel dashboard audit 2026-04-08 — four deploy cycles to fix missing `limit=10000` on `table()` and `sort()` calls, plus a multi-session debug of `render-as: markdown` breaking due to empty string assignment. All would have been caught by automated validation.

**Effort:** Medium per artifact type. Dashboard rules are highest priority (most rules identified, most painful incidents). The CQL shared rules benefit all artifact types.

### Auto-Fix Engine Expansion
**Current state:** Only handles `INVALID_FIELD_PLACEMENT`. The `auto_fix_yaml` field on `ValidationError` is populated but unused by other rules.
**Target:** Smart YAML modifications for common fixes — field relocation, empty array population, missing field insertion. Backup creation before modifications, preview/dry-run mode.
**Effort:** Large — needs careful YAML manipulation that preserves comments and formatting.

### CLI Overhaul
Click-based CLI with subcommands: `validate`, `fix`, `config`, `rules list`, `rules info <name>`. Interactive config setup. Shell completion.

### Fusion API Integration
Live schema validation against the Fusion SOAR API. Pull action schemas, trigger definitions, and platform action IDs directly from the tenant. Would make platform action ID validation (#10 above) feasible.

---

## Bug Fixes

### `enable_rule` Logic Bug
`get_enabled_rules()` checks both `self._disabled_rules` AND `rule.enabled_by_default`. If you call `enable_rule("X")` on a rule where `enabled_by_default=False`, it still won't appear in enabled rules. The explicit enable should override the default.

### Integration Test Warnings
Two integration tests (`test_full_validation_pipeline`, `test_parallel_processing_integration`) return `bool` instead of using `assert`, generating pytest `PytestReturnNotNoneWarning`.

---

## Ideas (no timeline)

- Docker container for CI environments
- Plugin dependency management (rules already have `dependencies` property, unused)
- Workflow diff tool — compare two versions of a workflow and highlight validation-relevant changes
- VS Code extension using SARIF output
- Foundry CLI integration — `foundry workflows validate` using this tool
