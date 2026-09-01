"""OutputSchemaRule - Validates inline query output schema completeness.

Checks that case risk assessment actions have all required output_schema fields
and that actions with output_schema also have workflow_csv_header_fields.
"""

from typing import List, Dict
from ..rules.base import ValidationRule
from ..models.context import ValidationContext
from ..models.errors import ValidationError, ErrorSeverity, ErrorCategory
from ..models.location import ValidationLocation

CASE_RISK_REQUIRED_FIELDS = [
    'case_description', 'case_priority', 'case_title', 'create_case',
    'risk_breakdown', 'ioc_verdict', 'threshold_explanation', 'total_risk_score',
]


class OutputSchemaRule(ValidationRule):

    @property
    def name(self) -> str:
        return "Output Schema"

    def validate(self, workflow: Dict, context: ValidationContext) -> List[ValidationError]:
        errors = []
        actions = workflow.get('actions', {})
        if not isinstance(actions, dict):
            return errors

        for action_name, action_data in actions.items():
            if not isinstance(action_data, dict):
                continue

            inline_config = action_data.get('inline_configuration', {})
            if not isinstance(inline_config, dict) or not inline_config:
                continue

            output_schema = inline_config.get('output_schema', {})
            if not output_schema:
                continue

            properties = action_data.get('properties', {})
            if not isinstance(properties, dict):
                properties = {}

            # Check case risk assessment actions for schema completeness
            is_case_risk = (
                'CaseRisk' in action_name
                or 'create_case_risk_level' in properties
            )

            if is_case_risk:
                schema_properties = output_schema.get('properties', {})
                missing = [f for f in CASE_RISK_REQUIRED_FIELDS if f not in schema_properties]
                if missing:
                    errors.append(ValidationError(
                        severity=ErrorSeverity.WARNING,
                        category=ErrorCategory.CONFIGURATION,
                        code="INCOMPLETE_OUTPUT_SCHEMA",
                        message=(
                            f"Case risk assessment action '{action_name}' has incomplete "
                            f"output_schema missing: {', '.join(missing)}"
                        ),
                        location=ValidationLocation(
                            file_path=context.file_path,
                            yaml_path=f"actions.{action_name}.inline_configuration.output_schema",
                        ),
                        fix_suggestion=(
                            f"Add complete output_schema with all required fields: "
                            f"{', '.join(missing)}. This enables field editing in the NG-SIEM UI."
                        ),
                    ))

            # Check for workflow_csv_header_fields alongside output_schema
            if 'workflow_csv_header_fields' not in properties:
                errors.append(ValidationError(
                    severity=ErrorSeverity.ERROR,
                    category=ErrorCategory.CONFIGURATION,
                    code="MISSING_CSV_HEADER_FIELDS_WITH_SCHEMA",
                    message=(
                        f"Inline query action '{action_name}' with output_schema missing "
                        f"required 'workflow_csv_header_fields' property"
                    ),
                    location=ValidationLocation(
                        file_path=context.file_path,
                        yaml_path=f"actions.{action_name}.properties",
                    ),
                    fix_suggestion="Add 'workflow_csv_header_fields: []' to properties block - required for UI field editing",
                ))

        return errors
