"""Tests for LoopIterationUsageRule - warns when a loop ignores its iteration value."""

import yaml

from workflow_validator.rules.loop_iteration_usage import LoopIterationUsageRule
from workflow_validator.models.context import ValidationContext
from workflow_validator.models.errors import ErrorSeverity, ErrorCategory


class TestLoopIterationUsageRule:
    def setup_method(self):
        self.rule = LoopIterationUsageRule()
        self.context = ValidationContext(file_path="test.yaml")

    def test_name(self):
        assert self.rule.name == "Loop Iteration Usage"

    def test_empty_workflow(self):
        assert self.rule.validate({}, self.context) == []

    def test_no_loops(self):
        workflow = {"actions": {"A": {"id": "1", "properties": {"msg": "hi"}}}}
        assert self.rule.validate(workflow, self.context) == []

    def test_positive_loop_missing_iteration_ref(self):
        """Single-loop workflow whose only inner action never references the iteration."""
        yaml_str = """
actions: {}
loops:
  ForEachUserNamesSequentially3Iterations3HourLimit:
    name: For each UserNames
    for:
      input: Trigger.Detection.NGSIEM.UserNames
    actions:
      EscalationEmail:
        id: 07413ef9ba7c47bf5a242799f59902cc
        name: Send email
        properties:
          msg: "An escalation email is sent to the incident owner and the IR team"
          subject: "An escalation email is sent to the incident owner and the IR team"
          to:
            - tbd-recipient@hcl.com
"""
        workflow = yaml.safe_load(yaml_str)
        errors = self.rule.validate(workflow, self.context)

        assert len(errors) == 1
        err = errors[0]
        assert err.severity == ErrorSeverity.WARNING
        assert err.category == ErrorCategory.CONFIGURATION
        assert err.code == "LOOP_ITERATION_NOT_USED"
        assert (
            err.location.yaml_path
            == "loops.ForEachUserNamesSequentially3Iterations3HourLimit"
        )
        assert "ForEachUserNamesSequentially3Iterations3HourLimit" in err.message

    def test_negative_at_least_one_action_references_iteration(self):
        """If ANY loop-internal action references the iteration, no warning."""
        yaml_str = """
actions: {}
loops:
  MyLoop:
    name: MyLoop
    for:
      input: Trigger.Detection.NGSIEM.UserNames
    actions:
      EmailA:
        id: 07413ef9ba7c47bf5a242799f59902cc
        name: Send email
        properties:
          subject: "User: ${data['MyLoop.Iteration']}"
          msg: "Details follow"
          to: [a@example.com]
      EmailB:
        id: 07413ef9ba7c47bf5a242799f59902cc
        name: Send email
        properties:
          subject: "Constant subject"
          msg: "Constant msg"
          to: [b@example.com]
"""
        workflow = yaml.safe_load(yaml_str)
        assert self.rule.validate(workflow, self.context) == []

    def test_yaml_escaped_single_quotes_not_warned(self):
        """Doubled single quotes in YAML collapse on parse to literal singles."""
        yaml_str = """
loops:
  MyLoop:
    name: MyLoop
    for:
      input: Trigger.X
    actions:
      E:
        id: 07413ef9ba7c47bf5a242799f59902cc
        name: E
        properties:
          subject: 'User: ${data[''MyLoop.Iteration'']}'
"""
        workflow = yaml.safe_load(yaml_str)
        # Sanity-check: YAML collapses '' -> '
        assert workflow["loops"]["MyLoop"]["actions"]["E"]["properties"]["subject"] == (
            "User: ${data['MyLoop.Iteration']}"
        )
        assert self.rule.validate(workflow, self.context) == []

    def test_double_quoted_bracket_form(self):
        workflow = {
            "loops": {
                "MyLoop": {
                    "for": {"input": "Trigger.X"},
                    "actions": {
                        "E": {
                            "id": "1",
                            "properties": {
                                "subject": 'hello ${data["MyLoop.Iteration"]}',
                            },
                        }
                    },
                }
            }
        }
        assert self.rule.validate(workflow, self.context) == []

    def test_iteration_in_nested_list_value(self):
        """Iteration ref buried inside a list-valued property is sufficient."""
        workflow = {
            "loops": {
                "MyLoop": {
                    "actions": {
                        "E": {
                            "id": "1",
                            "properties": {
                                "to": ["${data['MyLoop.Iteration']}@example.com"],
                            },
                        }
                    }
                }
            }
        }
        assert self.rule.validate(workflow, self.context) == []

    def test_case_sensitive_iteration_name(self):
        """Lowercase 'iteration' should NOT satisfy the rule."""
        workflow = {
            "loops": {
                "MyLoop": {
                    "actions": {
                        "E": {
                            "id": "1",
                            "properties": {
                                "msg": "${data['MyLoop.iteration']}",  # wrong case
                            },
                        }
                    }
                }
            }
        }
        errors = self.rule.validate(workflow, self.context)
        assert len(errors) == 1
        assert errors[0].code == "LOOP_ITERATION_NOT_USED"

    def test_wrong_loop_name_in_iteration_ref(self):
        """A ref to a different loop's iteration shouldn't count."""
        workflow = {
            "loops": {
                "LoopA": {
                    "actions": {
                        "E": {
                            "id": "1",
                            "properties": {
                                "msg": "${data['LoopB.Iteration']}",
                            },
                        }
                    }
                },
                "LoopB": {
                    "actions": {
                        "E2": {
                            "id": "1",
                            "properties": {
                                "msg": "${data['LoopB.Iteration']}",
                            },
                        }
                    }
                },
            }
        }
        errors = self.rule.validate(workflow, self.context)
        # LoopA doesn't reference its own iteration; LoopB does.
        assert len(errors) == 1
        assert errors[0].location.yaml_path == "loops.LoopA"

    def test_loop_with_no_actions_no_warning(self):
        workflow = {"loops": {"Empty": {"name": "Empty", "actions": {}}}}
        assert self.rule.validate(workflow, self.context) == []

    def test_multiple_loops_multiple_warnings(self):
        workflow = {
            "loops": {
                "A": {
                    "actions": {
                        "X": {"id": "1", "properties": {"msg": "constant"}},
                    }
                },
                "B": {
                    "actions": {
                        "Y": {"id": "1", "properties": {"msg": "also constant"}},
                    }
                },
            }
        }
        errors = self.rule.validate(workflow, self.context)
        assert len(errors) == 2
        assert {e.location.yaml_path for e in errors} == {"loops.A", "loops.B"}
