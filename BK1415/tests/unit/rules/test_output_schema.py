"""Tests for OutputSchemaRule - validates inline query output schema completeness."""

from workflow_validator.rules.output_schema import OutputSchemaRule
from workflow_validator.models.context import ValidationContext
from workflow_validator.models.errors import ErrorSeverity


class TestOutputSchemaRule:
    def setup_method(self):
        self.rule = OutputSchemaRule()
        self.context = ValidationContext(file_path="test.yaml")

    def test_name(self):
        assert self.rule.name == "Output Schema"

    def test_no_actions(self):
        assert self.rule.validate({}, self.context) == []

    def test_action_without_inline_config_ignored(self):
        workflow = {"actions": {"Step1": {"id": "123", "properties": {}}}}
        assert self.rule.validate(workflow, self.context) == []

    def test_case_risk_action_with_complete_schema_ok(self):
        workflow = {
            "actions": {
                "CaseRiskAssessment": {
                    "id": "123",
                    "inline_configuration": {
                        "output_schema": {
                            "properties": {
                                "case_description": {},
                                "case_priority": {},
                                "case_title": {},
                                "create_case": {},
                                "risk_breakdown": {},
                                "ioc_verdict": {},
                                "threshold_explanation": {},
                                "total_risk_score": {},
                            }
                        },
                    },
                    "properties": {"workflow_csv_header_fields": []},
                }
            }
        }
        errors = self.rule.validate(workflow, self.context)
        assert len(errors) == 0

    def test_case_risk_action_with_incomplete_schema_warns(self):
        workflow = {
            "actions": {
                "CaseRiskAssessment": {
                    "id": "123",
                    "inline_configuration": {
                        "output_schema": {
                            "properties": {
                                "case_description": {},
                                "case_priority": {},
                            }
                        },
                    },
                    "properties": {"workflow_csv_header_fields": []},
                }
            }
        }
        errors = self.rule.validate(workflow, self.context)
        assert len(errors) == 1
        assert errors[0].severity == ErrorSeverity.WARNING
        assert errors[0].code == "INCOMPLETE_OUTPUT_SCHEMA"
        assert "case_title" in errors[0].message

    def test_output_schema_missing_csv_headers_errors(self):
        """Action with output_schema but no workflow_csv_header_fields."""
        workflow = {
            "actions": {
                "QueryStep": {
                    "id": "123",
                    "inline_configuration": {
                        "output_schema": {"properties": {"field1": {}}},
                    },
                    "properties": {},
                }
            }
        }
        errors = self.rule.validate(workflow, self.context)
        assert len(errors) == 1
        assert errors[0].severity == ErrorSeverity.ERROR
        assert errors[0].code == "MISSING_CSV_HEADER_FIELDS_WITH_SCHEMA"

    def test_non_case_risk_action_skips_schema_completeness(self):
        """Non-case-risk actions should not check for specific schema fields."""
        workflow = {
            "actions": {
                "GenericQuery": {
                    "id": "123",
                    "inline_configuration": {
                        "output_schema": {"properties": {"custom_field": {}}},
                    },
                    "properties": {"workflow_csv_header_fields": []},
                }
            }
        }
        errors = self.rule.validate(workflow, self.context)
        assert len(errors) == 0
