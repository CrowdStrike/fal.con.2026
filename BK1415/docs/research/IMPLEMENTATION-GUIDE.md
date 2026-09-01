# Validation Rule Implementation Guide

**Based on:** `docs/research/VALIDATION-REQUIREMENTS-RESEARCH.md`
**Architecture:** v2.0 Plugin-Based Validation System
**Status:** 🟢 COMPLETED - Ready for Implementation
**Date:** 2026-02-05 22:35

---

## Quick Reference: Priority 1 Rules

### 1. InvalidFieldPlacementRule (CRITICAL)
**Problem:** `_fields` at action root causes "invalid action found"
**Location:** `src/workflow_validator/rules/field_placement.py`

```python
class InvalidFieldPlacementRule(ValidationRule):
    def validate(self, workflow: Dict, context: ValidationContext) -> List[ValidationError]:
        errors = []

        for action_name, action_def in workflow.get('actions', {}).items():
            # Check for _fields at root level (should be in properties)
            if '_fields' in action_def and '_fields' not in action_def.get('properties', {}):
                errors.append(ValidationError(
                    severity=ErrorSeverity.CRITICAL,
                    category=ErrorCategory.CONFIGURATION,
                    code="INVALID_FIELD_PLACEMENT",
                    message=f"Action '{action_name}' has '_fields' at root level - must be inside 'properties'",
                    location=ValidationLocation(
                        file_path=context.file_path,
                        yaml_path=f"actions.{action_name}._fields"
                    ),
                    fix_suggestion="Move '_fields' inside the 'properties' object"
                ))

        return errors
```

### 2. Enhanced ActionStructureRule
**Problem:** Missing `class` fields for custom actions
**Enhancement:** Handle built-in action exceptions

```python
class ActionStructureRule(ValidationRule):
    BUILTIN_ACTIONS = ['CreateVariable', 'UpdateVariable', 'Decision', 'Wait']

    def _is_builtin_action(self, action_name: str) -> bool:
        return any(builtin in action_name for builtin in self.BUILTIN_ACTIONS)

    def _requires_class_field(self, action_name: str, action_def: dict) -> bool:
        # Built-in actions don't require explicit class field
        if self._is_builtin_action(action_name):
            return False
        return True
```

### 3. SendEmailValidationRule
**Problem:** Missing required fields cause import failures
**Requirements:** `to`, `subject`, `msg` in properties

```python
class SendEmailValidationRule(ValidationRule):
    def validate(self, workflow: Dict, context: ValidationContext) -> List[ValidationError]:
        errors = []

        for action_name, action_def in workflow.get('actions', {}).items():
            if self._is_sendemail_action(action_name, action_def):
                properties = action_def.get('properties', {})
                required_fields = ['to', 'subject', 'msg']

                for field in required_fields:
                    if field not in properties:
                        errors.append(ValidationError(...))

        return errors
```

### 4. ActionPropertiesRule
**Problem:** Missing `properties` object
**Check:** Most actions need properties container

---

## Testing Against Real Workflows

### Test Case 1: MMB v0.8.yaml
**Before Research:** Only detected missing class fields
**After Research:** Should also detect field placement errors

### Test Case 2: Field Placement Errors
```yaml
# Create test workflow with known issues
actions:
  BadAction:
    id: "test"
    _fields: []  # WRONG LOCATION - should trigger INVALID_FIELD_PLACEMENT
    properties:
      to: ["test@example.com"]
```

### Test Case 3: SendEmail Validation
```yaml
actions:
  EmailAction:
    id: "test"
    class: "SendEmail"
    properties:
      # Missing 'to', 'subject', 'msg' - should trigger validation errors
```

---

## Implementation Priority

1. **InvalidFieldPlacementRule** - Addresses #1 import blocker
2. **Enhanced ActionStructureRule** - Better built-in handling
3. **SendEmailValidationRule** - Common action validation
4. **ActionPropertiesRule** - General structure validation

**Estimated Impact:** Should catch majority of real import failures identified in research. Implementation ready for Phase 3 continuation.

---

## Success Validation

Test improved validator against:
- MMB v0.8.yaml (should detect field placement issues)
- Workflows that fail Fusion UI import
- Known good workflows (should pass)

**Target:** >95% accuracy matching Fusion UI import behavior.