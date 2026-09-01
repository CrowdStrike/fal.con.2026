# CrowdStrike Fusion SOAR Workflow Validation Requirements Research

**Date:** 2026-02-05
**Status:** 🟢 COMPLETED
**Research Scope:** Comprehensive analysis of CrowdStrike knowledge sources for workflow validation requirements
**Research Method:** Systematic search across Jira, Confluence, Slack, Falcon Docs, and API documentation
**Primary Focus:** Action structure requirements and real import failure patterns
**Completion:** 2026-02-05 22:35

---

## Executive Summary

This research identified **specific validation requirements** that prevent workflow import failures in CrowdStrike Fusion SOAR. The findings explain why workflows pass basic schema validation but fail with "invalid action found" errors in the Fusion UI.

**Key Discovery:** Field placement errors and missing action structure requirements are the primary causes of import failures, not generic schema violations.

---

## 1. Critical Import Blockers

### 1.1 Action Structure Requirements

**Source:** Fusion SOAR Workflow APIs documentation (`/workflows/entities/definitions/import/v1`)

#### Required Action Schema
```yaml
actions:
  action_name:
    id: "07413exxxxxxxxxxxxxxxxxxxx9902cc"  # REQUIRED: UUID string
    class: "ActionClassName"                  # REQUIRED: For custom actions only
    properties:                               # REQUIRED: For most actions
      # Action-specific fields here
    next: ["next_action"]                     # OPTIONAL: Flow control
```

#### Action Type Classification
- **Custom Actions**: Require explicit `class` field (e.g., `Inline.QueryEvent`, `SendEmail`)
- **Built-in Actions**: May not need `class` field (`CreateVariable`, `UpdateVariable`, `Decision`, `Wait`)

### 1.2 Field Placement Rules (Critical)

**The #1 Import Blocker:** Fields in wrong YAML hierarchy

#### Prohibited Placements
- `_fields` **CANNOT** be at action root level - must be inside `properties`
- `next` belongs in flow control, not inside `properties`
- Action-specific fields must be inside `properties` object

#### Correct Field Hierarchy
```yaml
actions:
  my_action:
    id: "required-uuid"
    class: "RequiredForCustomActions"
    properties:                        # Required container
      _fields: []                      # ✅ MUST be inside properties
      action_specific_field: "value"   # ✅ Action config goes here
    next: ["flow_control"]             # ✅ Flow control at action level
```

### 1.3 Import Compatibility Requirements

**Source:** API import specifications

- **Workflow name uniqueness** within target CID
- **No third-party plugins** without availability validation
- **CID-specific subscriptions** must be available
- **Cross-CID event queries** are prohibited

---

## 2. Action-Specific Validation Requirements

### 2.1 SendEmail Action Requirements

**Source:** Documentation examples and API specs

#### Required Structure
```yaml
send_email:
  id: "07413exxxxxxxxxxxxxxxxxxxx9902cc"
  class: "SendEmail"                    # Required for custom actions
  properties:                           # Required container
    _fields: ["${Trigger.Field1}"]      # Optional metadata
    msg: "Email message content"        # REQUIRED
    subject: "Email subject"            # REQUIRED
    to: ["email@example.com"]           # REQUIRED: Array of valid emails
```

#### Validation Rules
- `to` field must be array of valid email addresses
- Recipients must have accounts in target CID
- `subject` and `msg` are required strings
- `_fields` is optional metadata array

### 2.2 Event Search Actions

**Source:** Query action documentation

#### Required Structure
```yaml
get_events:
  id: "06b30bxxxxxxxxxxxxxxxxxxxx965f11"
  class: "Inline.QueryEvent"
  properties:
    device_id: "${Trigger.SensorID}"          # REQUIRED: Search criteria
    latest: "${Workflow.Execution.Time}"      # REQUIRED: Time boundary
    search_timeframe_minutes: 60              # REQUIRED: Search window
```

#### Validation Rules
- Search criteria required (`device_id` or equivalent)
- Time boundaries required (`latest`, timeframe)
- Event queries must be valid in target CID

### 2.3 Built-in Action Exceptions

**Source:** Workflow template documentation

Built-in actions have simplified requirements:
- `CreateVariable`, `UpdateVariable`, `Decision`, `Wait`
- May not require explicit `class` field
- Simplified `properties` structure
- Focus on flow control vs. external integrations

---

## 3. Real-World Import Failure Patterns

### 3.1 Common UI Error Messages → Root Causes

| UI Error | Root Cause | Validation Rule Needed |
|----------|------------|------------------------|
| "invalid action found" | Missing `class` field | `ActionStructureRule` |
| "invalid action found" | `_fields` in wrong location | `InvalidFieldPlacementRule` |
| "Unable to import workflow" | Missing required properties | `ActionPropertiesRule` |
| "Recipients validation failed" | Invalid email addresses | `SendEmailValidationRule` |
| "Dependency not available" | Missing plugins/subscriptions | `DependencyValidationRule` |

### 3.2 Field Placement Error Examples

**❌ Wrong (causes import failure):**
```yaml
actions:
  MyAction:
    id: "uuid"
    class: "SendEmail"
    _fields: []              # WRONG LOCATION - causes "invalid action found"
    properties:
      to: ["user@domain.com"]
```

**✅ Correct:**
```yaml
actions:
  MyAction:
    id: "uuid"
    class: "SendEmail"
    properties:
      _fields: []            # CORRECT LOCATION
      to: ["user@domain.com"]
```

---

## 4. Validation Rule Implementation Roadmap

### 4.1 Priority 1: Critical Import Blockers

#### Rule 1: InvalidFieldPlacementRule
```python
class InvalidFieldPlacementRule(ValidationRule):
    """Detect fields in wrong YAML hierarchy - #1 import blocker"""

    def validate(self, workflow, context):
        # Check for _fields at action root (should be in properties)
        # Check for properties fields at wrong levels
        # Check for next field inside properties
```

#### Rule 2: Enhanced ActionStructureRule
```python
class ActionStructureRule(ValidationRule):
    """Validate action structure with built-in exceptions"""

    BUILTIN_ACTIONS = ['CreateVariable', 'UpdateVariable', 'Decision', 'Wait']

    def validate(self, workflow, context):
        # Check required id field
        # Check class field for custom actions (not built-ins)
        # Validate properties object existence
```

#### Rule 3: SendEmailValidationRule
```python
class SendEmailValidationRule(ValidationRule):
    """Validate SendEmail action requirements"""

    def validate(self, workflow, context):
        # Validate to/subject/msg required fields
        # Check email address format
        # Validate _fields placement if present
```

#### Rule 4: ActionPropertiesRule
```python
class ActionPropertiesRule(ValidationRule):
    """Ensure required properties object exists"""

    def validate(self, workflow, context):
        # Check properties object exists for non-control-flow actions
        # Validate properties is object type, not array/string
```

### 4.2 Priority 2: Enhanced Validation

- **DependencyValidationRule**: Check plugin/subscription availability
- **EventQueryValidationRule**: Validate search criteria and time boundaries
- **ControlFlowValidationRule**: Validate next/decision logic
- **NameUniquenessRule**: Check workflow name conflicts

### 4.3 Priority 3: Advanced Features

- **CID CompatibilityRule**: Cross-CID validation
- **PerformanceValidationRule**: Query optimization checks
- **SecurityValidationRule**: Sensitive data exposure checks

---

## 5. Error Severity Classification

### Critical (Import Blockers)
- Missing required fields (`id`, `class`, `properties`)
- Invalid field placement (`_fields` location)
- Action structure violations
- Dependency unavailability

### Warning (Best Practice)
- Deprecated field usage
- Suboptimal configurations
- Performance concerns
- Style violations

### Info (Recommendations)
- Documentation improvements
- Optimization opportunities
- Enhancement suggestions

---

## 6. Validation Rule Categories by Impact

### Schema Validation (Critical)
```python
CRITICAL_VALIDATIONS = {
    "MISSING_ACTION_ID": "Action missing required 'id' field",
    "MISSING_ACTION_CLASS": "Custom action missing 'class' field",
    "INVALID_FIELD_PLACEMENT": "_fields must be inside properties, not root",
    "MISSING_PROPERTIES": "Action missing required 'properties' object",
}
```

### Action-Specific Validation (Critical)
```python
ACTION_SPECIFIC_VALIDATIONS = {
    "INVALID_EMAIL_RECIPIENTS": "SendEmail 'to' field must be array of valid emails",
    "MISSING_SENDEMAIL_REQUIRED": "SendEmail missing required fields: to/subject/msg",
    "INVALID_QUERY_CRITERIA": "Event search missing required search criteria",
}
```

### Dependency Validation (Critical)
```python
DEPENDENCY_VALIDATIONS = {
    "MISSING_PLUGIN": "Required plugin not available in target CID",
    "MISSING_SUBSCRIPTION": "Required subscription not available in target CID",
    "CROSS_CID_QUERY": "Event query references different CID",
}
```

---

## 7. Implementation Success Metrics

### Validation Accuracy Targets
- **Import Success Rate**: >95% for workflows passing validation
- **False Positive Rate**: <5% (workflows failing validation but importing successfully)
- **Error Precision**: Exact YAML path location for all errors
- **Fix Success Rate**: >80% of auto-fix suggestions resolve import failures

### Coverage Requirements
- **Action Types**: Support for all common action types (SendEmail, QueryEvent, Variables, etc.)
- **Field Validation**: Complete coverage of field placement rules
- **Error Messages**: Actionable fix suggestions for all critical errors

---

## 8. Future Research Priorities

### Knowledge Gap Areas
1. **Custom Action Requirements**: More action-specific validation rules
2. **Advanced Field Types**: Complex property validation (objects, arrays)
3. **Version Compatibility**: Validation rules across Fusion versions
4. **Performance Patterns**: Query optimization requirements

### Research Sources for Expansion
1. **Support Tickets**: Analysis of real customer import failures
2. **Engineering Feedback**: Direct input from Fusion development team
3. **User Community**: Common issues from workflow builders
4. **Version Updates**: New validation requirements in platform updates

---

## 9. Conclusion

This research provides a **systematic foundation** for building validation rules that catch **real import failures** rather than generic schema violations. The key insight is that **field placement errors and action structure requirements** are the primary causes of import failures, not basic YAML syntax issues.

The modular v2 validation architecture is perfectly positioned to implement these findings incrementally, starting with the highest-impact rules that prevent the most common import failures.

**Next Steps:**
1. Implement Priority 1 validation rules
2. Test against real workflows that fail import
3. Measure validation accuracy and refine rules
4. Expand to Priority 2 and 3 rules based on usage data

---

**Research Completed:** 2026-02-05 22:35
**Implementation Ready:** Priority 1 rules (4 critical validation rules identified)
**Architecture:** Compatible with v2.0 plugin-based validation system
**Impact:** Addresses #1 import blocker (field placement errors) and action structure requirements
**Next Phase:** Implementation guide created - ready for Phase 3 continuation

---

## Appendix A: Inline Query Limit Evidence (Added 2026-02-13)

Research into the source of the inline query size and pipe count limits used by the validator.

### A.1 Pipe/Subquery Limit: 100 (LogScale-enforced)

**Status:** Confirmed via LogScale API error response

LogScale enforces a hard limit of 100 pipes/subqueries per query. When exceeded, the API returns:

```
HTTP 400 Bad Request
Too many pipes/subqueries in query. count=101. max=100
```

**Evidence:**
- **Jira:** [OWL-7321](https://jira.cs.sys/browse/OWL-7321) - "Autogen LogScale enrichments: Too many pipes/subqueries in query"
  - OverWatch Labs hit this limit in Feb 2026 when autogenerated enrichment queries grew to 101 pipes
  - The error originates from LogScale's `/api/v1/repositories/{repo}/query` endpoint
  - Assigned to Day Barr, status: In Progress as of 2026-02-12
- **Error source:** LogScale server-side enforcement, not Fusion

**Counting method in validator:** Each line starting with `|` (after stripping whitespace) counts as one pipe. This matches LogScale's own counting (`count=101` in the error matched the actual pipe-prefixed lines).

### A.2 Character Size Limit: ~26,000 (Fusion inline execution, empirically determined)

**Status:** Empirically determined; no official documentation found

The validator uses a hard limit of 26,000 characters for inline query size based on empirical testing:
- Queries of ~26,300 characters execute successfully
- Queries of ~26,400+ characters cause HTTP 500 errors in Fusion inline execution

**Evidence:**
- Code comment in `workflow_validator.py` (original author's testing notes)
- No Jira tickets, Confluence pages, or official Fusion/LogScale documentation found that specify this limit
- The Foundry Platform Limits & Constraints Guide ([Confluence page 689686278](https://wiki.cs.sys/spaces/~jcarrasco/pages/689686278)) documents many Foundry limits but does not mention inline query character limits
- The limit appears to be in the Fusion workflow execution layer (HTTP 500), not in LogScale itself (which returns HTTP 400 for its own limits)

**Search methodology (2026-02-13):**
- Confluence: Searched "Fusion inline query pipe limit", "LogScale query limits constraints maximum", "Humio LogScale pipe operations maximum 100" - no relevant results
- Jira: Searched `text ~ "too many pipes" OR text ~ "pipe limit"` - found OWL-7321 confirming pipe limit; no tickets documenting the character limit
- No official LogScale or Fusion documentation found specifying the ~26K character limit

### A.3 Recommendations

1. The pipe limit of 100 is well-supported and should remain at `QUERY_PIPE_HARD_LIMIT = 100`
2. The character limit should be re-validated periodically since it is based on empirical testing and may change with Fusion platform updates
3. If LogScale or Fusion publish official limit documentation, update both the code comments and this research document