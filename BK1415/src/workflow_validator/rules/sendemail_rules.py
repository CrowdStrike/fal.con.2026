"""SendEmailValidationRule - Validates SendEmail action requirements.

This rule addresses validation of the most common action type based on CrowdStrike research.
Validates required fields (to, subject, msg) and email address format.
"""

import re
from typing import List, Dict
from ..rules.base import ValidationRule
from ..models.context import ValidationContext
from ..models.errors import ValidationError, ErrorSeverity, ErrorCategory
from ..models.location import ValidationLocation


class SendEmailValidationRule(ValidationRule):
    """Validates SendEmail action requirements based on CrowdStrike research.

    Ensures SendEmail actions have:
    - Required fields: to, subject, msg
    - Valid email addresses in 'to' field
    - Non-empty recipients array
    """

    # Simple email regex for basic validation
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

    @property
    def name(self) -> str:
        return "SendEmail Validation"

    @property
    def enabled_by_default(self) -> bool:
        return True

    def validate(self, workflow: Dict, context: ValidationContext) -> List[ValidationError]:
        """Validate SendEmail actions in the workflow.

        Args:
            workflow: The workflow dictionary to validate
            context: Validation context with file path and content

        Returns:
            List of ValidationError objects for SendEmail validation issues
        """
        errors = []

        # Check actions for SendEmail validation
        actions = workflow.get('actions', {})
        for action_name, action_def in actions.items():
            if not isinstance(action_def, dict):
                continue

            # Only validate SendEmail actions
            if self._is_sendemail_action(action_name, action_def):
                errors.extend(self._validate_sendemail_action(action_name, action_def, context))

        return errors

    def _is_sendemail_action(self, action_name: str, action_def: dict) -> bool:
        """Check if this is a SendEmail action that needs validation."""
        # Check explicit class field
        action_class = action_def.get('class', '')
        if 'SendEmail' in action_class:
            return True

        # Check action name pattern
        if 'SendEmail' in action_name:
            return True

        return False

    def _validate_sendemail_action(self, action_name: str, action_def: dict, context: ValidationContext) -> List[ValidationError]:
        """Validate a specific SendEmail action."""
        errors = []
        properties = action_def.get('properties', {})

        # Required fields for SendEmail
        required_fields = ['to', 'subject', 'msg']

        # Check for required fields - informational only, matching monolith
        # behavior which did not enforce to/subject/msg presence.
        for field in required_fields:
            if field not in properties:
                error = ValidationError(
                    severity=ErrorSeverity.INFO,
                    category=ErrorCategory.CONFIGURATION,
                    code="MISSING_SENDEMAIL_FIELD",
                    message=f"SendEmail action '{action_name}' missing field: '{field}'",
                    location=ValidationLocation(
                        file_path=context.file_path,
                        yaml_path=f"actions.{action_name}.properties.{field}"
                    ),
                    fix_suggestion=f"Add '{field}:' field to SendEmail action properties"
                )
                errors.append(error)

        # Validate 'to' field specifically
        if 'to' in properties:
            errors.extend(self._validate_recipients(action_name, properties['to'], context))

        return errors

    def _validate_recipients(self, action_name: str, recipients, context: ValidationContext) -> List[ValidationError]:
        """Validate the recipients field of SendEmail action."""
        errors = []

        # Recipients should be an array
        if not isinstance(recipients, list):
            error = ValidationError(
                severity=ErrorSeverity.CRITICAL,
                category=ErrorCategory.CONFIGURATION,
                code="INVALID_EMAIL_RECIPIENTS",
                message=f"SendEmail action '{action_name}' 'to' field must be an array of email addresses",
                location=ValidationLocation(
                    file_path=context.file_path,
                    yaml_path=f"actions.{action_name}.properties.to"
                ),
                fix_suggestion="Change 'to' field to an array format: ['email@example.com']"
            )
            errors.append(error)
            return errors

        # Check for empty recipients
        if len(recipients) == 0:
            error = ValidationError(
                severity=ErrorSeverity.CRITICAL,
                category=ErrorCategory.CONFIGURATION,
                code="EMPTY_EMAIL_RECIPIENTS",
                message=f"SendEmail action '{action_name}' has empty recipients - causes action node error and puts the workflow into an error-disabled state",
                location=ValidationLocation(
                    file_path=context.file_path,
                    yaml_path=f"actions.{action_name}.properties.to"
                ),
                fix_suggestion="Add at least one email address to the 'to' array"
            )
            errors.append(error)

        # Validate individual email addresses
        for i, email in enumerate(recipients):
            if isinstance(email, str):
                # Skip template variables like ${Variable.Field}
                if email.startswith('${') and email.endswith('}'):
                    continue

                # Validate email format
                if not self.EMAIL_PATTERN.match(email):
                    error = ValidationError(
                        severity=ErrorSeverity.ERROR,
                        category=ErrorCategory.CONFIGURATION,
                        code="INVALID_EMAIL_FORMAT",
                        message=f"SendEmail action '{action_name}' contains invalid email address: '{email}'",
                        location=ValidationLocation(
                            file_path=context.file_path,
                            yaml_path=f"actions.{action_name}.properties.to[{i}]"
                        ),
                        fix_suggestion="Use valid email format: user@domain.com"
                    )
                    errors.append(error)

        return errors