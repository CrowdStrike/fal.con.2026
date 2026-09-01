"""CsvHeaderFieldsRule - Validates workflow_csv_header_fields in inline query actions.

Inline query actions that export CSV results should include
workflow_csv_header_fields in their properties block. When an output_schema
is also present the field is required for UI field editing; otherwise it is
informational.
"""

from typing import List, Dict
from ..rules.base import ValidationRule
from ..models.context import ValidationContext
from ..models.errors import ValidationError, ErrorSeverity, ErrorCategory
from ..models.location import ValidationLocation


class CsvHeaderFieldsRule(ValidationRule):

    @property
    def name(self) -> str:
        return "CSV Header Fields"

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

            # Identify inline query actions by their characteristic properties
            has_alert_id = 'alertId' in properties
            has_output_files = 'output_files_only' in properties
            has_export_csv = 'workflow_export_event_query_results_to_csv' in properties

            if not (has_alert_id and has_output_files and has_export_csv):
                continue

            if 'workflow_csv_header_fields' in properties:
                continue

            # Determine severity based on output_schema presence
            inline_config = action_data.get('inline_configuration', {})
            has_output_schema = bool(
                isinstance(inline_config, dict) and inline_config.get('output_schema')
            )

            severity = ErrorSeverity.ERROR if has_output_schema else ErrorSeverity.INFO
            schema_context = " with output_schema" if has_output_schema else ""
            fix_context = " - REQUIRED for UI field editing" if has_output_schema else " if you need CSV export"

            errors.append(ValidationError(
                severity=severity,
                category=ErrorCategory.CONFIGURATION,
                code="MISSING_CSV_HEADER_FIELDS",
                message=(
                    f"Inline query action '{action_name}'{schema_context} "
                    f"missing 'workflow_csv_header_fields' property"
                ),
                location=ValidationLocation(
                    file_path=context.file_path,
                    yaml_path=f"actions.{action_name}.properties",
                ),
                fix_suggestion=f"Add 'workflow_csv_header_fields: []' to properties block{fix_context}",
            ))

        return errors
