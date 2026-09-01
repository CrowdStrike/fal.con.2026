"""InvalidFieldPlacementRule - Validates field placement in YAML hierarchy.

This rule addresses the #1 import blocker: fields in wrong YAML hierarchy.
Uses an allowlist of valid action-level fields; anything not in the allowlist
is flagged as misplaced (typically belongs inside 'properties').
"""

from typing import List, Dict
from ..rules.base import ValidationRule
from ..models.context import ValidationContext
from ..models.errors import ValidationError, ErrorSeverity, ErrorCategory
from ..models.location import ValidationLocation

# Fields legitimately allowed at the action level (not inside properties).
# Derived from scanning ~/clients/*/workflows/ (305 files, 4468 actions) and
# cross-referencing with the UI-exported YAML shape. `default_name` in particular
# shows up 447 times and is emitted automatically by the Fusion UI on export.
ALLOWED_ACTION_FIELDS = {
    'id', 'name', 'default_name', 'next', 'properties', 'version_constraint',
    'continue_on_error', 'condition', 'else', 'class',
    'inline_configuration', 'loop', 'description', 'end',
}

# Common misplaced fields with specific guidance
COMMON_MISPLACED_FIELDS = {
    'workflow_csv_header_fields': "Should be inside 'properties:' block",
    'workflow_export_event_query_results_to_csv': "Should be inside 'properties:' block",
    'output_files_only': "Should be inside 'properties:' block",
    'alertId': "Should be inside 'properties:' block",
    '_fields': "Should be inside 'properties:' block",
    'to': "Should be inside 'properties:' block (for SendEmail actions)",
    'subject': "Should be inside 'properties:' block (for SendEmail actions)",
    'msg': "Should be inside 'properties:' block (for SendEmail actions)",
}


class InvalidFieldPlacementRule(ValidationRule):
    """Detects fields in wrong YAML hierarchy - the #1 import blocker.

    Uses an inverted-logic allowlist: only known action-level fields are
    permitted; everything else is flagged as likely misplaced.
    """

    @property
    def name(self) -> str:
        return "Invalid Field Placement"

    @property
    def enabled_by_default(self) -> bool:
        return True

    def validate(self, workflow: Dict, context: ValidationContext) -> List[ValidationError]:
        errors = []
        actions = workflow.get('actions', {})

        for action_name, action_def in actions.items():
            if not isinstance(action_def, dict):
                continue

            for field_name in action_def:
                # Allow custom extension fields
                if field_name.startswith('x-'):
                    continue

                if field_name in ALLOWED_ACTION_FIELDS:
                    continue

                fix_guidance = COMMON_MISPLACED_FIELDS.get(
                    field_name,
                    f"Unknown field '{field_name}' at action level - check CrowdStrike documentation",
                )

                errors.append(ValidationError(
                    severity=ErrorSeverity.CRITICAL,
                    category=ErrorCategory.CONFIGURATION,
                    code="INVALID_FIELD_PLACEMENT",
                    message=(
                        f"Action '{action_name}' has '{field_name}' at action level - "
                        f"{fix_guidance.lower()}"
                    ),
                    location=ValidationLocation(
                        file_path=context.file_path,
                        yaml_path=f"actions.{action_name}.{field_name}",
                    ),
                    fix_suggestion=fix_guidance,
                ))

        return errors
