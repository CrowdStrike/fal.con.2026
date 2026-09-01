"""Tests for TriggerStructureRule - validates trigger configuration."""

from workflow_validator.rules.trigger_structure import TriggerStructureRule
from workflow_validator.models.context import ValidationContext
from workflow_validator.models.errors import ErrorSeverity


class TestTriggerStructureRule:
    def setup_method(self):
        self.rule = TriggerStructureRule()
        self.context = ValidationContext(file_path="test.yaml")

    def test_name(self):
        assert self.rule.name == "Trigger Structure"

    def test_no_trigger(self):
        """No trigger key at all - nothing to validate (required_fields catches this)."""
        assert self.rule.validate({}, self.context) == []

    def test_event_based_trigger_ok(self):
        workflow = {"trigger": {"type": "Event", "event": {"type": "DetectionSummaryEvent"}}}
        assert self.rule.validate(workflow, self.context) == []

    def test_on_demand_trigger_with_params_ok(self):
        workflow = {"trigger": {"type": "On demand", "parameters": [{"name": "alertId"}]}}
        assert self.rule.validate(workflow, self.context) == []

    def test_on_demand_trigger_without_params_info(self):
        workflow = {"trigger": {"type": "On demand"}}
        errors = self.rule.validate(workflow, self.context)
        assert len(errors) == 1
        assert errors[0].severity == ErrorSeverity.INFO

    def test_empty_trigger_type_warns(self):
        workflow = {"trigger": {"type": ""}}
        errors = self.rule.validate(workflow, self.context)
        assert len(errors) == 1
        assert errors[0].severity == ErrorSeverity.WARNING
        assert "empty" in errors[0].message.lower()

    def test_non_on_demand_type_without_event_errors(self):
        workflow = {"trigger": {"type": "Scheduled"}}
        errors = self.rule.validate(workflow, self.context)
        assert len(errors) == 1
        assert errors[0].severity == ErrorSeverity.ERROR
        assert "event" in errors[0].message.lower()

    def test_trigger_no_type_no_params_info(self):
        """Trigger with no type and no parameters gets informational note."""
        workflow = {"trigger": {}}
        errors = self.rule.validate(workflow, self.context)
        assert len(errors) == 1
        assert errors[0].severity == ErrorSeverity.INFO
