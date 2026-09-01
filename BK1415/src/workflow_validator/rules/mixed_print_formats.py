"""MixedPrintFormatsRule - Detects old fields array + new custom_json conflicts.

Print actions should use either the legacy 'fields' array format or the newer
'custom_json' format, but not both simultaneously.
"""

from typing import List, Dict
from ..rules.base import ValidationRule
from ..models.context import ValidationContext
from ..models.errors import ValidationError, ErrorSeverity, ErrorCategory
from ..models.location import ValidationLocation


class MixedPrintFormatsRule(ValidationRule):

    @property
    def name(self) -> str:
        return "Mixed Print Formats"

    def validate(self, workflow: Dict, context: ValidationContext) -> List[ValidationError]:
        errors = []
        actions = workflow.get('actions', {})
        if not isinstance(actions, dict):
            return errors

        for action_name, action_data in actions.items():
            if not isinstance(action_data, dict):
                continue

            properties = action_data.get('properties', {})
            if not isinstance(properties, dict):
                continue

            has_fields = 'fields' in properties
            has_custom_json = 'custom_json' in properties

            if has_fields and has_custom_json:
                errors.append(ValidationError(
                    severity=ErrorSeverity.ERROR,
                    category=ErrorCategory.CONFIGURATION,
                    code="MIXED_PRINT_FORMATS",
                    message=(
                        f"Action '{action_name}' has both 'fields' (old format) "
                        f"and 'custom_json' (new format)"
                    ),
                    location=ValidationLocation(
                        file_path=context.file_path,
                        yaml_path=f"actions.{action_name}.properties",
                    ),
                    fix_suggestion="Remove either 'fields:' or 'custom_json:' - don't use both formats",
                ))

        return errors
