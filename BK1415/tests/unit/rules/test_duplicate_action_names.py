"""Tests for DuplicateActionNamesRule - detects duplicate display names across actions."""

from workflow_validator.rules.duplicate_action_names import DuplicateActionNamesRule
from workflow_validator.models.context import ValidationContext
from workflow_validator.models.errors import ErrorSeverity


class TestDuplicateActionNamesRule:
    def setup_method(self):
        self.rule = DuplicateActionNamesRule()
        self.context = ValidationContext(file_path="test.yaml")

    def test_name(self):
        assert self.rule.name == "Duplicate Action Names"

    def test_no_actions(self):
        assert self.rule.validate({}, self.context) == []

    def test_unique_names_ok(self):
        workflow = {
            "actions": {
                "Step1": {"id": "1", "name": "Extract Data"},
                "Step2": {"id": "2", "name": "Send Email"},
            }
        }
        assert self.rule.validate(workflow, self.context) == []

    def test_duplicate_display_names_warns(self):
        workflow = {
            "actions": {
                "Step1": {"id": "1", "name": "Process Alert"},
                "Step2": {"id": "2", "name": "Process Alert"},
            }
        }
        errors = self.rule.validate(workflow, self.context)
        assert len(errors) == 1
        assert errors[0].severity == ErrorSeverity.WARNING
        assert errors[0].code == "DUPLICATE_ACTION_NAME"
        assert "Process Alert" in errors[0].message

    def test_duplicate_ids_allowed(self):
        """Duplicate action IDs are allowed in Fusion - only display names flagged."""
        workflow = {
            "actions": {
                "Step1": {"id": "same-id", "name": "First"},
                "Step2": {"id": "same-id", "name": "Second"},
            }
        }
        assert self.rule.validate(workflow, self.context) == []

    def test_fallback_to_action_key_when_no_name(self):
        """When 'name' field is absent, action key is used as display name."""
        workflow = {
            "actions": {
                "Step1": {"id": "1"},
                "Step2": {"id": "2"},
            }
        }
        # Different keys, no name field - should be fine
        assert self.rule.validate(workflow, self.context) == []
