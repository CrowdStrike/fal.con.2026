"""TriggerStructureRule - Validates trigger configuration.

Checks trigger type, event field presence, and parameter completeness
for on-demand vs event-based triggers.
"""

from typing import List, Dict
from ..rules.base import ValidationRule
from ..models.context import ValidationContext
from ..models.errors import ValidationError, ErrorSeverity, ErrorCategory
from ..models.location import ValidationLocation


class TriggerStructureRule(ValidationRule):

    @property
    def name(self) -> str:
        return "Trigger Structure"

    def validate(self, workflow: Dict, context: ValidationContext) -> List[ValidationError]:
        errors = []

        if 'trigger' not in workflow:
            return errors

        trigger = workflow['trigger']
        if not isinstance(trigger, dict):
            return errors

        trigger_type = trigger.get('type', '').lower()

        if 'event' in trigger:
            # Event-based trigger — valid
            return errors

        if trigger_type and 'on demand' in trigger_type:
            if 'parameters' not in trigger:
                errors.append(ValidationError(
                    severity=ErrorSeverity.INFO,
                    category=ErrorCategory.CONFIGURATION,
                    code="ON_DEMAND_MISSING_PARAMS",
                    message="On-demand trigger without parameters (may be intentional)",
                    location=ValidationLocation(file_path=context.file_path, yaml_path="trigger"),
                ))
            return errors

        if 'type' in trigger and not trigger_type:
            errors.append(ValidationError(
                severity=ErrorSeverity.WARNING,
                category=ErrorCategory.CONFIGURATION,
                code="EMPTY_TRIGGER_TYPE",
                message="Trigger has 'type' field but value is empty",
                location=ValidationLocation(file_path=context.file_path, yaml_path="trigger"),
                fix_suggestion="Set 'type: On demand' for on-demand triggers or add 'event:' field",
            ))
            return errors

        if 'type' in trigger and 'event' not in trigger and 'on demand' not in trigger_type:
            errors.append(ValidationError(
                severity=ErrorSeverity.ERROR,
                category=ErrorCategory.CONFIGURATION,
                code="MISSING_TRIGGER_EVENT",
                message=f"Trigger with type '{trigger.get('type')}' missing 'event' field",
                location=ValidationLocation(file_path=context.file_path, yaml_path="trigger"),
                fix_suggestion="Add 'event:' field to trigger or change type to 'On demand'",
            ))
            return errors

        # No clear trigger type identified
        if 'parameters' not in trigger:
            errors.append(ValidationError(
                severity=ErrorSeverity.INFO,
                category=ErrorCategory.CONFIGURATION,
                code="UNCLEAR_TRIGGER_TYPE",
                message="Trigger type not clearly identified - add 'type: On demand' for clarity",
                location=ValidationLocation(file_path=context.file_path, yaml_path="trigger"),
            ))

        return errors
