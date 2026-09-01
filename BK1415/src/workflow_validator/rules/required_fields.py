from typing import List, Dict
from ..rules.base import ValidationRule
from ..models.context import ValidationContext
from ..models.errors import ValidationError, ErrorSeverity, ErrorCategory
from ..models.location import ValidationLocation

class RequiredFieldsRule(ValidationRule):
    @property
    def name(self) -> str:
        return "Required Fields"

    def validate(self, workflow: Dict, context: ValidationContext) -> List[ValidationError]:
        errors = []
        required = ['name', 'trigger', 'actions']

        for field in required:
            if field not in workflow:
                location = ValidationLocation(
                    file_path=context.file_path,
                    yaml_path=f"root.{field}"
                )
                errors.append(ValidationError(
                    severity=ErrorSeverity.CRITICAL,
                    category=ErrorCategory.SCHEMA,
                    code="MISSING_REQUIRED_FIELD",
                    message=f"Workflow missing required field: '{field}'",
                    location=location,
                    fix_suggestion=f"Add '{field}:' to the workflow root"
                ))

        return errors