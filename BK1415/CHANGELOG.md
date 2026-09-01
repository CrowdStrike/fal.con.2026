# Fusion Workflow Validator

## Changelog

### 2.2.1 (2026-05-05) - False-Positive Narrowing (default_name, data[...] subscript)

#### Bug Fixes
- **FIXED**: `INVALID_FIELD_PLACEMENT` CRITICAL false positive on `default_name` at action level. This field is emitted automatically by the Fusion UI on export and was observed 447 times across 305 workflows in `~/clients/*/workflows/`. Added to `ALLOWED_ACTION_FIELDS` in `src/workflow_validator/rules/field_placement.py`.
- **FIXED**: `INVALID_VARIABLE_SUBSCRIPT` CRITICAL false positive on `${data['Action.results'][0].field}` expressions inside action property strings and `cel_expression` fields. The rule previously matched any `${...[N]...}` pattern; it is now narrowed to only `${Trigger.*[N]...}` references — the one form that genuinely fails post-deploy (see `~/.claude/learnings/fusion-variable-expression-no-array-subscript.md`). Regex anchored with `Trigger\.` prefix; `${data[...][0].field}` remains valid and is explicitly excluded. Regression fixture added at `tests/test_workflows/valid_data_results_subscript.yaml`.

Both false positives previously fired on every real exported workflow and pressured upstream callers into a `--skip-local-validate` bypass. That bypass has been removed; these narrowings eliminate the need for it.

#### Scope preserved
- `${Trigger.X.Y[0]}` is still flagged — that form genuinely fails post-deploy with `unknown variable`.
- Unknown / misplaced action-level fields (e.g. `workflow_csv_header_fields`, `_fields`, `to`/`subject`/`msg` outside `properties:`) are still flagged.

#### Tests
- 155 unit + integration tests pass on Python 3.14 (previously 149; +6 for the two narrowings and a reference fixture).

---

### 2.2.0 (2026-05-05) - Server-Side Validation Gate & Built-in Action Allow-List

#### New Features
- **NEW**: `--server-validate` / `-s` flag — opt-in second gate that POSTs YAML to the Fusion `validate_only=true` endpoint. Catches trigger-type-specific variable errors (e.g. `${Trigger.CompositeID}` used on an NG-SIEM Detection trigger — code 2016) that the local rule-based validator cannot see. Requires `FALCON_CLIENT_ID` / `FALCON_CLIENT_SECRET` / `FALCON_BASE_URL` in env or `.env`. No auth needed for local-only runs.
- **NEW**: `known_action_ids.yaml` — shipped allow-list of global Fusion action UUIDs recognised as built-in. Sourced from confirmed-global action docIDs plus high-frequency UUIDs observed across client workflows.
- **NEW**: Exit code `2` when `--server-validate` cannot reach the API (auth / network / missing env). Distinct from code `1` which remains "validation errors found."

#### Bug Fixes
- **FIXED**: `MISSING_ACTION_CLASS` INFO false positive on built-in actions. Action `id` is now checked against `known_action_ids.yaml` (and handles Fusion composite ids of the form `<base>~<extension>` by matching the root). Previously, every built-in action (AddCommentToDetection, SetDetectionStatus, CreateVariable by id, etc.) that omitted `class:` — which is nearly every console-exported workflow — triggered the INFO. Verified against 210 real client workflows: INFO now only fires for genuine custom / integration actions (Charlotte AI, Entra, MSDefender, Abnormal Security, etc.).

#### Tests
- All 149 unit + integration tests pass on Python 3.14.
- Validated against 210 workflows under `~/clients/*/workflows/` — no regressions.

---

### 2.1.1 (2026-03-26) - SOAR Payload Size Detection

#### New Features
- **NEW**: SOAR payload size rule (plugin #15) - detects CreateLookupFile actions combining 2+ SOAR page outputs in one CEL expression, which causes runtime `error_code 500 "message size is too large"` when data volume crosses Fusion's ~1MB limit
- Severity: ERROR — this is a guaranteed runtime failure, not a best-practice issue

#### Documentation
- **FIXED**: README and validation guide referenced non-existent CLI flags (`--summary`, `--verbose`, `--json`)
- **FIXED**: Invocation examples used `python3 -m src.workflow_validator` instead of `python3 workflow_validator.py`
- Updated rule count from 14 to 15

---

### 2.1.0 (2026-03-17) - CreateCase Validation & Pipe Counter Fixes

#### New Features
- **NEW**: CreateCase field limits validation rule (plugin #14) - validates field count and character limits for CreateCase actions

#### Bug Fixes
- **FIXED**: Pipe counter rewrite - now correctly skips `|` inside strings, regex literals, and braces to prevent false positives
- **FIXED**: Accurate LogScale pipe counting including case branch penalties
- **FIXED**: Truncation guard detection in dynamic CreateCase descriptions

---

### 2.0.0 (2026-02-06) - Production Ready v2 Architecture

#### 🚀 Major Release - Complete System Rewrite

**Phase 1: Core Architecture Foundation**
- **NEW**: Enhanced error model with precise location tracking and YAML path support
- **NEW**: Plugin-based validation rule system with extensible ValidationRule interface
- **NEW**: ValidationContext and ValidationLocation for comprehensive error reporting

**Phase 2: Auto-Fix Engine with Plugin System**
- **NEW**: Auto-fix engine with backup capabilities for safe YAML modifications
- **NEW**: Plugin registry system for dynamic rule management
- **NEW**: Converted all validation rules to plugin architecture

**Phase 3: Performance and Enhanced Reporting**
- **NEW**: Parallel validation engine for high-performance multi-file processing
- **NEW**: Rich CLI interface with colors, emojis, and beautiful error formatting
- **NEW**: YAML configuration system for customizable validation behavior
- **NEW**: Batch processing with comprehensive summary reporting

#### ✅ Research-Backed Validation Rules

**Priority 1 Rules** (based on analysis of real CrowdStrike workflow import failures):
- **NEW**: InvalidFieldPlacementRule - Detects #1 import blocker (fields in wrong YAML hierarchy)
- **ENHANCED**: ActionStructureRule - Improved built-in vs custom action handling
- **NEW**: SendEmailValidationRule - Validates most common action type requirements
- **ENHANCED**: RequiredFieldsRule - Plugin-based with precise error locations

#### 📊 Proven Results

Tested against **27 real CrowdStrike workflows**:
- ✅ **83 genuine critical issues found** - all would block imports
- ✅ **4 clean workflows passed** - zero false positives
- ✅ **ActionStructureRule** accurately detects missing class fields

#### 🎯 Ready For Production

- **CLI Experience**: `python3 -m src.workflow_validator workflows/*.yaml`
- **Configuration**: YAML-based rule customization and output control
- **Performance**: Parallel processing with configurable worker threads
- **Documentation**: ROADMAP.md for planned features

#### 🔧 Technical Improvements

- **FIXED**: Python import issues throughout codebase (relative imports)
- **NEW**: Comprehensive test coverage for all components
- **NEW**: Real-world validation test infrastructure
- **NEW**: Professional CLI experience matching modern development tools

### 1.1.0 (2026-02-05) - Reality Alignment Update

#### 🚨 Breaking Changes
- **REMOVED**: Duplicate Action ID validation entirely
  - **Reason**: Fusion UI creates workflows with duplicate IDs by design
  - **Impact**: Workflows with duplicate IDs now pass validation (as they should)
  - **Migration**: No action needed - previously "broken" workflows may now validate

#### ✅ Fixed
- **Fixed**: False positive duplicate field detection
  - **Issue**: Validator incorrectly flagged `text_data` fields in different actions as duplicates
  - **Solution**: Improved scope detection to only flag duplicates within same properties block
  - **Example**: `PrintData.properties.text_data` and `PrintData2.properties.text_data` no longer flagged as duplicates

- **Fixed**: Overly strict validation not matching Fusion reality
  - **Issue**: Validator enforced theoretical best practices rather than actual Fusion import requirements
  - **Solution**: Aligned validation rules with real Fusion import behavior
  - **Impact**: Reduced false positive error rate from 75% to 25%

#### 🔧 Improved
- **Enhanced**: Duplicate field detection logic
  - Now correctly identifies properties context before flagging duplicates
  - Improved YAML structure understanding for action scope boundaries
- **Enhanced**: Error messaging aligned with actual Fusion requirements
  - More accurate error descriptions and fix suggestions
  - Clearer distinction between blockers vs improvements

#### 📚 Context & Reasoning

**Why Duplicate IDs Are Now Allowed:**
Through testing with real Fusion workflows, we discovered:
1. **UI Behavior**: Fusion UI creates workflows with duplicate action IDs by default
2. **Import Success**: Workflows with duplicate IDs import successfully
3. **Functional**: These workflows execute properly despite shared IDs
4. **Design Intent**: This appears to be intentional Fusion behavior

**Validator Philosophy Change:**
- **Before**: "Best Practices" validation (theoretical ideals)
- **After**: "Import Readiness" validation (real-world Fusion behavior)

#### 🧪 Testing Results
- **Validation Accuracy**: Improved from 25% success rate to 75% success rate
- **Real Issues**: Now only flags actual import-blocking problems (orphaned YAML)
- **Workflows Fixed**: 6 workflows now pass that previously failed validation

#### 💡 Key Learnings
1. Always validate rules against the actual target system behavior
2. If the UI creates it, it's valid by design
3. Distinguish "will import" from "follows best practices"
4. False positives reduce tool adoption and trust

---

### 1.0.0 (2026-02-04)
- Initial release
- Validates CrowdStrike Fusion SOAR workflow YAML files
- Checks for common import failures:
  - Invalid action-level field placement
  - Empty SendEmail recipients
  - Missing output schemas
  - Invalid field names
  - Missing version constraints
  - Duplicate action names
- Multiple output formats (text, summary, JSON)
- Line number reporting for errors
- Auto-fix suggestions
