"""Tests for MixedPrintFormatsRule - detects old fields + new custom_json conflicts."""

from workflow_validator.rules.mixed_print_formats import MixedPrintFormatsRule
from workflow_validator.models.context import ValidationContext
from workflow_validator.models.errors import ErrorSeverity


class TestMixedPrintFormatsRule:
    def setup_method(self):
        self.rule = MixedPrintFormatsRule()
        self.context = ValidationContext(file_path="test.yaml")

    def test_name(self):
        assert self.rule.name == "Mixed Print Formats"

    def test_no_actions(self):
        assert self.rule.validate({}, self.context) == []

    def test_fields_only_ok(self):
        workflow = {
            "actions": {
                "Print1": {"id": "1", "properties": {"fields": [{"key": "val"}]}}
            }
        }
        assert self.rule.validate(workflow, self.context) == []

    def test_custom_json_only_ok(self):
        workflow = {
            "actions": {
                "Print1": {"id": "1", "properties": {"custom_json": "{}"}}
            }
        }
        assert self.rule.validate(workflow, self.context) == []

    def test_fields_and_custom_json_errors(self):
        workflow = {
            "actions": {
                "Print1": {
                    "id": "1",
                    "properties": {
                        "fields": [{"key": "val"}],
                        "custom_json": "{}",
                    },
                }
            }
        }
        errors = self.rule.validate(workflow, self.context)
        assert len(errors) == 1
        assert errors[0].severity == ErrorSeverity.ERROR
        assert errors[0].code == "MIXED_PRINT_FORMATS"

    def test_no_properties_ignored(self):
        workflow = {"actions": {"Step1": {"id": "1"}}}
        assert self.rule.validate(workflow, self.context) == []
