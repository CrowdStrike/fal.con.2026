"""Tests for InvalidFieldPlacementRule - validates field placement in YAML hierarchy."""

import pytest
from workflow_validator.rules.field_placement import InvalidFieldPlacementRule
from workflow_validator.models.context import ValidationContext
from workflow_validator.models.errors import ErrorSeverity, ErrorCategory


class TestInvalidFieldPlacementRule:

    def test_fields_at_action_root_invalid(self):
        """Test that _fields at action root level is flagged as invalid."""
        rule = InvalidFieldPlacementRule()
        context = ValidationContext(file_path="test.yaml")

        # Workflow with _fields at wrong location (action root instead of properties)
        workflow = {
            "name": "Test Workflow",
            "trigger": {},
            "actions": {
                "SendEmail": {
                    "id": "test-id",
                    "_fields": ["${Trigger.Field1}"],  # WRONG LOCATION - should be in properties
                    "properties": {
                        "to": ["user@example.com"]
                    }
                }
            }
        }

        errors = rule.validate(workflow, context)

        assert len(errors) == 1
        error = errors[0]
        assert error.code == "INVALID_FIELD_PLACEMENT"
        assert error.severity == ErrorSeverity.CRITICAL
        assert error.category == ErrorCategory.CONFIGURATION
        assert "SendEmail" in error.message
        assert "_fields" in error.message
        assert "properties" in error.message
        assert error.location.yaml_path == "actions.SendEmail._fields"
        assert "properties" in error.fix_suggestion

    def test_fields_in_properties_valid(self):
        """Test that _fields inside properties is valid."""
        rule = InvalidFieldPlacementRule()
        context = ValidationContext(file_path="test.yaml")

        # Workflow with _fields in correct location (inside properties)
        workflow = {
            "name": "Test Workflow",
            "trigger": {},
            "actions": {
                "SendEmail": {
                    "id": "test-id",
                    "properties": {
                        "to": ["user@example.com"],
                        "_fields": ["${Trigger.Field1}"]  # CORRECT LOCATION
                    }
                }
            }
        }

        errors = rule.validate(workflow, context)

        assert len(errors) == 0

    def test_no_fields_attribute_valid(self):
        """Test that actions without _fields are valid."""
        rule = InvalidFieldPlacementRule()
        context = ValidationContext(file_path="test.yaml")

        workflow = {
            "name": "Test Workflow",
            "trigger": {},
            "actions": {
                "SendEmail": {
                    "id": "test-id",
                    "properties": {
                        "to": ["user@example.com"]
                    }
                }
            }
        }

        errors = rule.validate(workflow, context)

        assert len(errors) == 0

    def test_multiple_actions_with_field_placement_errors(self):
        """Test validation of multiple actions with field placement errors."""
        rule = InvalidFieldPlacementRule()
        context = ValidationContext(file_path="test.yaml")

        workflow = {
            "name": "Test Workflow",
            "trigger": {},
            "actions": {
                "SendEmail1": {
                    "id": "test-id-1",
                    "_fields": ["${Field1}"],  # WRONG LOCATION
                    "properties": {
                        "to": ["user1@example.com"]
                    }
                },
                "SendEmail2": {
                    "id": "test-id-2",
                    "properties": {
                        "to": ["user2@example.com"],
                        "_fields": ["${Field2}"]  # CORRECT LOCATION
                    }
                },
                "SendEmail3": {
                    "id": "test-id-3",
                    "_fields": ["${Field3}"],  # WRONG LOCATION
                    "properties": {
                        "to": ["user3@example.com"]
                    }
                }
            }
        }

        errors = rule.validate(workflow, context)

        # Should find 2 errors (SendEmail1 and SendEmail3)
        assert len(errors) == 2
        error_actions = [error.location.yaml_path for error in errors]
        assert "actions.SendEmail1._fields" in error_actions
        assert "actions.SendEmail3._fields" in error_actions

        # SendEmail2 should not have errors since _fields is in correct location
        assert "actions.SendEmail2._fields" not in error_actions

    def test_allowed_action_level_fields_ok(self):
        """Fields in the allowed set (id, name, properties, etc.) should not trigger errors."""
        rule = InvalidFieldPlacementRule()
        context = ValidationContext(file_path="test.yaml")

        workflow = {
            "actions": {
                "Step1": {
                    "id": "123",
                    "name": "My Step",
                    "properties": {"key": "val"},
                    "version_constraint": "~1",
                    "next": ["Step2"],
                    "continue_on_error": True,
                    "condition": "x == 1",
                    "class": "SomeAction",
                    "inline_configuration": {},
                    "loop": {},
                    "description": "test",
                    "end": True,
                    "else": ["StepX"],
                }
            }
        }
        errors = rule.validate(workflow, context)
        assert len(errors) == 0

    def test_unknown_action_level_field_errors(self):
        """Fields NOT in the allowed set should be flagged."""
        rule = InvalidFieldPlacementRule()
        context = ValidationContext(file_path="test.yaml")

        workflow = {
            "actions": {
                "Step1": {
                    "id": "123",
                    "properties": {},
                    "workflow_csv_header_fields": [],  # Should be inside properties
                }
            }
        }
        errors = rule.validate(workflow, context)
        assert len(errors) == 1
        assert errors[0].code == "INVALID_FIELD_PLACEMENT"
        assert "workflow_csv_header_fields" in errors[0].message

    def test_x_extension_fields_allowed(self):
        """Custom extension fields starting with 'x-' should be allowed."""
        rule = InvalidFieldPlacementRule()
        context = ValidationContext(file_path="test.yaml")

        workflow = {
            "actions": {
                "Step1": {
                    "id": "123",
                    "properties": {},
                    "x-custom-field": "value",
                }
            }
        }
        errors = rule.validate(workflow, context)
        assert len(errors) == 0

    def test_default_name_action_level_allowed(self):
        """`default_name` is emitted at action level by Fusion UI exports.

        Regression: previously this rule flagged it as a CRITICAL field-placement
        violation, which fired on ~every exported workflow. Scanning
        ~/clients/*/workflows/ shows `default_name` appears 447 times across 305
        workflows at action level and is never a real problem.
        """
        rule = InvalidFieldPlacementRule()
        context = ValidationContext(file_path="test.yaml")

        workflow = {
            "actions": {
                "MyStep": {
                    "id": "abc-123",
                    "name": "My Step",
                    "default_name": "My Step",
                    "properties": {"key": "val"},
                }
            }
        }
        errors = rule.validate(workflow, context)
        assert errors == [], (
            f"default_name at action level should be allowed but got: "
            f"{[e.message for e in errors]}"
        )