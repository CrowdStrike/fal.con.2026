"""Tests for InvalidVariableSubscriptRule - detects ${...[N]...} integer subscripts."""

import yaml
from pathlib import Path

from workflow_validator.rules.invalid_variable_subscript import (
    InvalidVariableSubscriptRule,
)
from workflow_validator.models.context import ValidationContext
from workflow_validator.models.errors import ErrorSeverity, ErrorCategory

FIXTURE_DIR = Path(__file__).resolve().parent.parent.parent / "test_workflows"


class TestInvalidVariableSubscriptRule:
    def setup_method(self):
        self.rule = InvalidVariableSubscriptRule()
        self.context = ValidationContext(file_path="test.yaml")

    def test_name(self):
        assert self.rule.name == "Invalid Variable Subscript"

    def test_empty_workflow(self):
        assert self.rule.validate({}, self.context) == []

    def test_positive_full_fixture_produces_four_errors(self):
        """Real-world pre-fix state of HCLTech BackUps v3 workflow."""
        yaml_str = """
name: Example Workflow
trigger:
  event: Investigatable/NGSIEM
  type: Signal
actions:
  TopEmail:
    id: 07413ef9ba7c47bf5a242799f59902cc
    name: Send email
    properties:
      msg: "A detection fired on ${Trigger.Detection.NGSIEM.DestinationHosts[0]}"
      subject: "Alert for ${Trigger.Detection.NGSIEM.SourceHosts[0]}"
      to:
        - tbd-recipient@hcl.com
loops:
  MyLoop:
    name: MyLoop
    for:
      input: Trigger.Detection.NGSIEM.UserNames
    actions:
      LoopEmail:
        id: 07413ef9ba7c47bf5a242799f59902cc
        name: Loop email
        properties:
          msg: "User ${data['MyLoop.Iteration']} on host ${Trigger.Detection.NGSIEM.DestinationHosts[0]}"
          subject: "Hit ${Trigger.Detection.NGSIEM.DestinationHosts[0]}"
          to:
            - tbd-recipient@hcl.com
"""
        workflow = yaml.safe_load(yaml_str)
        errors = self.rule.validate(workflow, self.context)

        assert len(errors) == 4, f"Expected 4 errors, got {len(errors)}: {[e.message for e in errors]}"
        for err in errors:
            assert err.severity == ErrorSeverity.CRITICAL
            assert err.category == ErrorCategory.CONFIGURATION
            assert err.code == "INVALID_VARIABLE_SUBSCRIPT"
            assert err.fix_suggestion is not None

        paths = sorted(e.location.yaml_path for e in errors)
        assert paths == sorted([
            "actions.TopEmail.properties.msg",
            "actions.TopEmail.properties.subject",
            "loops.MyLoop.actions.LoopEmail.properties.msg",
            "loops.MyLoop.actions.LoopEmail.properties.subject",
        ])

    def test_negative_no_subscripts(self):
        yaml_str = """
actions:
  TopEmail:
    id: 07413ef9ba7c47bf5a242799f59902cc
    name: Send email
    properties:
      msg: "Detections on ${Trigger.Detection.NGSIEM.DestinationHosts}"
      subject: "Alert: ${Trigger.Detection.Name}"
      to:
        - security@example.com
"""
        workflow = yaml.safe_load(yaml_str)
        assert self.rule.validate(workflow, self.context) == []

    def test_data_bracket_string_key_not_matched(self):
        """${data['MyLoop.Iteration']} is a string-key bracket, not integer subscript."""
        workflow = {
            "actions": {
                "A": {
                    "id": "1",
                    "properties": {
                        "msg": "User ${data['MyLoop.Iteration']}",
                        "subject": "Also ${data[\"X.Iteration\"]}",
                    },
                }
            }
        }
        assert self.rule.validate(workflow, self.context) == []

    def test_subscript_in_condition_expression(self):
        workflow = {
            "conditions": {
                "C1": {
                    "expression": "${Trigger.X.Hosts[0]} == 'foo'",
                }
            }
        }
        errors = self.rule.validate(workflow, self.context)
        assert len(errors) == 1
        assert errors[0].location.yaml_path == "conditions.C1.expression"

    def test_subscript_in_cel_expression(self):
        workflow = {
            "conditions": {
                "C1": {
                    "cel_expression": "has(x) && ${Trigger.X.Arr[5]}",
                }
            }
        }
        errors = self.rule.validate(workflow, self.context)
        assert len(errors) == 1
        assert errors[0].location.yaml_path == "conditions.C1.cel_expression"

    def test_subscript_in_loop_condition(self):
        workflow = {
            "loops": {
                "L": {
                    "conditions": {
                        "LC": {
                            "expression": "${Trigger.X.Y[2]}",
                        }
                    }
                }
            }
        }
        errors = self.rule.validate(workflow, self.context)
        assert len(errors) == 1
        assert errors[0].location.yaml_path == "loops.L.conditions.LC.expression"

    def test_subscript_in_list_element(self):
        """Subscripts inside list items (e.g. `to:` recipients) should be caught."""
        workflow = {
            "actions": {
                "A": {
                    "id": "1",
                    "properties": {
                        "to": ["${Trigger.X.Emails[0]}", "ok@example.com"],
                    },
                }
            }
        }
        errors = self.rule.validate(workflow, self.context)
        assert len(errors) == 1
        assert errors[0].location.yaml_path == "actions.A.properties.to[0]"

    def test_multi_digit_subscript(self):
        """Multi-digit integer subscript on a Trigger.* path is still flagged."""
        workflow = {
            "actions": {
                "A": {
                    "id": "1",
                    "properties": {"msg": "${Trigger.X.Y[12]}"},
                }
            }
        }
        errors = self.rule.validate(workflow, self.context)
        assert len(errors) == 1

    def test_non_trigger_prefix_not_flagged(self):
        """${foo[12]} (no Trigger. prefix) is not flagged - the rule is
        narrowly scoped to Trigger.* references only.
        """
        workflow = {
            "actions": {
                "A": {
                    "id": "1",
                    "properties": {"msg": "${foo[12]}"},
                }
            }
        }
        errors = self.rule.validate(workflow, self.context)
        assert errors == []

    def test_data_results_subscript_not_flagged(self):
        """${data['Action.results'][0].field} is a production-valid pattern used
        in string-interpolation contexts (comments, tags, email bodies). It must
        NOT be flagged by this rule.
        """
        workflow = {
            "actions": {
                "A": {
                    "id": "1",
                    "properties": {
                        "comment": "Count was ${data['CountQuery.results'][0].hourly_count} events",
                        "subject": "First host: ${data['Query.results'][0].host_name}",
                    },
                }
            }
        }
        errors = self.rule.validate(workflow, self.context)
        assert errors == [], (
            f"Expected 0 errors but got: {[e.message for e in errors]}"
        )

    def test_data_results_subscript_in_cel_expression_not_flagged(self):
        """In cel_expression fields, data['X.results'][0].field is also valid."""
        workflow = {
            "conditions": {
                "C1": {
                    "cel_expression": "data['Query.results'][0].count > 10",
                }
            }
        }
        errors = self.rule.validate(workflow, self.context)
        assert errors == []

    def test_multiple_subscripts_in_same_string(self):
        """Two Trigger.* subscripts in the same string → two errors."""
        workflow = {
            "actions": {
                "A": {
                    "id": "1",
                    "properties": {
                        "msg": "${Trigger.a[0]} and ${Trigger.b[1]}",
                    },
                }
            }
        }
        errors = self.rule.validate(workflow, self.context)
        assert len(errors) == 2

    def test_mixed_trigger_and_data_subscripts(self):
        """In a string with both a Trigger.* subscript and a data[...] subscript,
        only the Trigger.* one is flagged.
        """
        workflow = {
            "actions": {
                "A": {
                    "id": "1",
                    "properties": {
                        "msg": (
                            "Host ${Trigger.X.Hosts[0]} "
                            "had ${data['Q.results'][0].count} events"
                        ),
                    },
                }
            }
        }
        errors = self.rule.validate(workflow, self.context)
        assert len(errors) == 1
        assert "Trigger.X.Hosts[0]" in errors[0].message

    def test_no_loops_no_actions_ok(self):
        assert self.rule.validate({"name": "empty"}, self.context) == []

    def test_valid_data_results_subscript_fixture_passes(self):
        """Regression fixture: the test_workflows/ fixture that exercises the
        production-valid ${data['X.results'][0].field} pattern must produce zero
        INVALID_VARIABLE_SUBSCRIPT errors.
        """
        fixture = FIXTURE_DIR / "valid_data_results_subscript.yaml"
        assert fixture.exists(), f"Fixture missing: {fixture}"
        with fixture.open() as f:
            workflow = yaml.safe_load(f)
        errors = self.rule.validate(workflow, self.context)
        assert errors == [], (
            "INVALID_VARIABLE_SUBSCRIPT flagged the valid data[...] pattern: "
            f"{[e.message for e in errors]}"
        )
