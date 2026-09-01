"""Tests for FieldNamesRule - detects periods in property names."""

from workflow_validator.rules.field_names import FieldNamesRule
from workflow_validator.models.context import ValidationContext
from workflow_validator.models.errors import ErrorSeverity


class TestFieldNamesRule:
    def setup_method(self):
        self.rule = FieldNamesRule()
        self.context = ValidationContext(file_path="test.yaml")

    def test_name(self):
        assert self.rule.name == "Field Names"

    def test_no_actions(self):
        assert self.rule.validate({}, self.context) == []

    def test_clean_property_names_ok(self):
        workflow = {
            "actions": {
                "Step1": {"id": "1", "properties": {"alertId": "abc", "output_files_only": True}}
            }
        }
        assert self.rule.validate(workflow, self.context) == []

    def test_period_in_property_name_warns(self):
        workflow = {
            "actions": {
                "Step1": {"id": "1", "properties": {"host.name": "value"}}
            }
        }
        errors = self.rule.validate(workflow, self.context)
        assert len(errors) == 1
        assert errors[0].severity == ErrorSeverity.WARNING
        assert errors[0].code == "FIELD_NAME_CONTAINS_PERIOD"

    def test_template_variable_with_period_ignored(self):
        """Fields starting with ${ should be skipped (template references)."""
        workflow = {
            "actions": {
                "Step1": {"id": "1", "properties": {"${host.name}": "value"}}
            }
        }
        assert self.rule.validate(workflow, self.context) == []

    def test_no_properties_ignored(self):
        workflow = {"actions": {"Step1": {"id": "1"}}}
        assert self.rule.validate(workflow, self.context) == []
