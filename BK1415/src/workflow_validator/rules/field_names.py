"""FieldNamesRule - Detects periods in property names.

LogScale schemas and Fusion properties should use underscores or camelCase,
not periods, in field names.
"""

from typing import List, Dict
from ..rules.base import ValidationRule
from ..models.context import ValidationContext
from ..models.errors import ValidationError, ErrorSeverity, ErrorCategory
from ..models.location import ValidationLocation


class FieldNamesRule(ValidationRule):

    @property
    def name(self) -> str:
        return "Field Names"

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

            for prop_key in properties:
                if '.' in prop_key and not prop_key.startswith('${'):
                    errors.append(ValidationError(
                        severity=ErrorSeverity.WARNING,
                        category=ErrorCategory.CONFIGURATION,
                        code="FIELD_NAME_CONTAINS_PERIOD",
                        message=f"Property '{prop_key}' in action '{action_name}' contains period",
                        location=ValidationLocation(
                            file_path=context.file_path,
                            yaml_path=f"actions.{action_name}.properties.{prop_key}",
                        ),
                        fix_suggestion="Use underscores or camelCase instead of periods in field names",
                    ))

        return errors
