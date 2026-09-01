"""DuplicateActionNamesRule - Detects duplicate action display names.

Duplicate action IDs are allowed in Fusion (the UI creates them).
Only duplicate display names are flagged as they cause confusion.
"""

from typing import List, Dict
from ..rules.base import ValidationRule
from ..models.context import ValidationContext
from ..models.errors import ValidationError, ErrorSeverity, ErrorCategory
from ..models.location import ValidationLocation


class DuplicateActionNamesRule(ValidationRule):

    @property
    def name(self) -> str:
        return "Duplicate Action Names"

    def validate(self, workflow: Dict, context: ValidationContext) -> List[ValidationError]:
        errors = []
        actions = workflow.get('actions', {})
        if not isinstance(actions, dict):
            return errors

        name_counts: Dict[str, List[str]] = {}
        for action_key, action_data in actions.items():
            if not isinstance(action_data, dict):
                continue
            display_name = action_data.get('name', action_key)
            name_counts.setdefault(display_name, []).append(action_key)

        for display_name, action_keys in name_counts.items():
            if len(action_keys) > 1:
                errors.append(ValidationError(
                    severity=ErrorSeverity.WARNING,
                    category=ErrorCategory.CONFIGURATION,
                    code="DUPLICATE_ACTION_NAME",
                    message=(
                        f"Multiple actions have the same display name "
                        f"'{display_name}': {', '.join(action_keys)}"
                    ),
                    location=ValidationLocation(
                        file_path=context.file_path,
                        yaml_path="actions",
                    ),
                    fix_suggestion="Ensure each action has a unique name",
                ))

        return errors
