"""Tests for CsvHeaderFieldsRule - validates workflow_csv_header_fields in inline query actions."""

from workflow_validator.rules.csv_header_fields import CsvHeaderFieldsRule
from workflow_validator.models.context import ValidationContext
from workflow_validator.models.errors import ErrorSeverity


class TestCsvHeaderFieldsRule:
    def setup_method(self):
        self.rule = CsvHeaderFieldsRule()
        self.context = ValidationContext(file_path="test.yaml")

    def test_name(self):
        assert self.rule.name == "CSV Header Fields"

    def test_no_actions(self):
        assert self.rule.validate({}, self.context) == []

    def test_inline_query_with_csv_headers_ok(self):
        """Inline query action with workflow_csv_header_fields present - no error."""
        workflow = {
            "actions": {
                "Step1": {
                    "id": "123",
                    "properties": {
                        "alertId": "abc",
                        "output_files_only": True,
                        "workflow_export_event_query_results_to_csv": True,
                        "workflow_csv_header_fields": [],
                    },
                }
            }
        }
        errors = self.rule.validate(workflow, self.context)
        assert len(errors) == 0

    def test_inline_query_missing_csv_headers_with_output_schema_errors(self):
        """Inline query with output_schema but no csv_headers is ERROR."""
        workflow = {
            "actions": {
                "Step1": {
                    "id": "123",
                    "inline_configuration": {
                        "output_schema": {"properties": {}},
                    },
                    "properties": {
                        "alertId": "abc",
                        "output_files_only": True,
                        "workflow_export_event_query_results_to_csv": True,
                    },
                }
            }
        }
        errors = self.rule.validate(workflow, self.context)
        assert len(errors) == 1
        assert errors[0].severity == ErrorSeverity.ERROR
        assert errors[0].code == "MISSING_CSV_HEADER_FIELDS"

    def test_inline_query_missing_csv_headers_without_output_schema_info(self):
        """Inline query without output_schema and no csv_headers is INFO."""
        workflow = {
            "actions": {
                "Step1": {
                    "id": "123",
                    "properties": {
                        "alertId": "abc",
                        "output_files_only": True,
                        "workflow_export_event_query_results_to_csv": True,
                    },
                }
            }
        }
        errors = self.rule.validate(workflow, self.context)
        assert len(errors) == 1
        assert errors[0].severity == ErrorSeverity.INFO
        assert errors[0].code == "MISSING_CSV_HEADER_FIELDS"

    def test_non_inline_query_action_ignored(self):
        """Actions that aren't inline queries should be skipped."""
        workflow = {
            "actions": {
                "Step1": {
                    "id": "123",
                    "properties": {
                        "to": ["user@example.com"],
                    },
                }
            }
        }
        errors = self.rule.validate(workflow, self.context)
        assert len(errors) == 0
