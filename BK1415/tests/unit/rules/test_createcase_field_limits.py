"""Tests for CreateCaseFieldLimitsRule - validates Fusion Cases API field length limits."""

from workflow_validator.rules.createcase_field_limits import CreateCaseFieldLimitsRule
from workflow_validator.models.context import ValidationContext
from workflow_validator.models.errors import ErrorSeverity


class TestCreateCaseFieldLimitsRule:
    def setup_method(self):
        self.rule = CreateCaseFieldLimitsRule()
        self.context = ValidationContext(file_path="test.yaml")

    def test_name(self):
        assert self.rule.name == "CreateCase Field Limits"

    def test_no_actions(self):
        errors = self.rule.validate({}, self.context)
        assert errors == []

    def test_non_createcase_action_ignored(self):
        workflow = {
            "actions": {
                "SendEmail": {
                    "id": "abc",
                    "name": "Send notification email",
                    "properties": {"description": "x" * 3000},
                }
            }
        }
        errors = self.rule.validate(workflow, self.context)
        assert errors == []

    def test_static_description_under_soft_limit(self):
        workflow = {
            "actions": {
                "CreateANewCase": {
                    "id": "123",
                    "name": "Create a new Case",
                    "properties": {"description": "Short description"},
                }
            }
        }
        errors = self.rule.validate(workflow, self.context)
        assert errors == []

    def test_static_description_over_hard_limit_errors(self):
        workflow = {
            "actions": {
                "CreateANewCase": {
                    "id": "123",
                    "name": "Create a new Case",
                    "properties": {"description": "x" * 2051},
                }
            }
        }
        errors = self.rule.validate(workflow, self.context)
        assert len(errors) == 1
        assert errors[0].severity == ErrorSeverity.ERROR
        assert errors[0].code == "CREATECASE_DESCRIPTION_OVER_LIMIT"
        assert "2,051" in errors[0].message

    def test_static_description_near_limit_warns(self):
        workflow = {
            "actions": {
                "CreateANewCase": {
                    "id": "123",
                    "name": "Create a new Case",
                    "properties": {"description": "x" * 1850},
                }
            }
        }
        errors = self.rule.validate(workflow, self.context)
        assert len(errors) == 1
        assert errors[0].severity == ErrorSeverity.WARNING
        assert errors[0].code == "CREATECASE_DESCRIPTION_NEAR_LIMIT"

    def test_static_description_at_exactly_hard_limit_no_error(self):
        workflow = {
            "actions": {
                "CreateANewCase": {
                    "id": "123",
                    "name": "Create a new Case",
                    "properties": {"description": "x" * 2000},
                }
            }
        }
        errors = self.rule.validate(workflow, self.context)
        # 2000 is over the soft limit (1800) but not over the hard limit
        assert len(errors) == 1
        assert errors[0].severity == ErrorSeverity.WARNING
        assert errors[0].code == "CREATECASE_DESCRIPTION_NEAR_LIMIT"

    def test_dynamic_expression_unguarded_warns(self):
        workflow = {
            "actions": {
                "CreateANewCase": {
                    "id": "123",
                    "name": "Create a new Case",
                    "properties": {
                        "description": "${data['CalculateRiskScore.results'][0]['case_description']}"
                    },
                }
            }
        }
        errors = self.rule.validate(workflow, self.context)
        assert len(errors) == 1
        assert errors[0].severity == ErrorSeverity.WARNING
        assert errors[0].code == "CREATECASE_DESCRIPTION_DYNAMIC"
        assert "no recognized length guard" in errors[0].message.lower()

    def test_dynamic_expression_with_substring_guard_info(self):
        """JUEL .size()/.substring() guard should downgrade to INFO."""
        workflow = {
            "actions": {
                "CreateANewCase": {
                    "id": "123",
                    "name": "Create a new Case",
                    "properties": {
                        "description": (
                            "${data['CRA.results'][0].case_description.size() > 1900 "
                            "? data['CRA.results'][0].case_description.substring(0, 1900) "
                            "+ '\\n[TRUNCATED]' "
                            ": data['CRA.results'][0].case_description}"
                        )
                    },
                }
            }
        }
        errors = self.rule.validate(workflow, self.context)
        assert len(errors) == 1
        assert errors[0].severity == ErrorSeverity.INFO
        assert errors[0].code == "CREATECASE_DESCRIPTION_GUARDED"

    def test_dynamic_expression_with_python_slice_guard_info(self):
        """Python-style [:N] guard should downgrade to INFO."""
        workflow = {
            "actions": {
                "CreateANewCase": {
                    "id": "123",
                    "name": "Create a new Case",
                    "properties": {
                        "description": "${data['score']['desc'][:1900]}"
                    },
                }
            }
        }
        errors = self.rule.validate(workflow, self.context)
        assert len(errors) == 1
        assert errors[0].severity == ErrorSeverity.INFO
        assert errors[0].code == "CREATECASE_DESCRIPTION_GUARDED"

    def test_dynamic_expression_with_length_check_guard_info(self):
        """A .length() > N check should count as a guard."""
        workflow = {
            "actions": {
                "CreateANewCase": {
                    "id": "123",
                    "name": "Create a new Case",
                    "properties": {
                        "description": "${desc.length() > 1800 ? short : desc}"
                    },
                }
            }
        }
        errors = self.rule.validate(workflow, self.context)
        assert len(errors) == 1
        assert errors[0].severity == ErrorSeverity.INFO
        assert errors[0].code == "CREATECASE_DESCRIPTION_GUARDED"

    def test_dynamic_expression_with_truncate_function_guard_info(self):
        """A truncate() call should count as a guard."""
        workflow = {
            "actions": {
                "CreateANewCase": {
                    "id": "123",
                    "name": "Create a new Case",
                    "properties": {
                        "description": "${truncate(data['desc'], 1900)}"
                    },
                }
            }
        }
        errors = self.rule.validate(workflow, self.context)
        assert len(errors) == 1
        assert errors[0].severity == ErrorSeverity.INFO
        assert errors[0].code == "CREATECASE_DESCRIPTION_GUARDED"

    def test_no_description_field_skipped(self):
        workflow = {
            "actions": {
                "CreateANewCase": {
                    "id": "123",
                    "name": "Create a new Case",
                    "properties": {"status": "new"},
                }
            }
        }
        errors = self.rule.validate(workflow, self.context)
        assert errors == []

    def test_detection_by_class_field(self):
        """Action with explicit CreateCaseV1 class should be detected."""
        workflow = {
            "actions": {
                "MyCustomAction": {
                    "id": "123",
                    "class": "CreateCaseV1",
                    "name": "Open incident ticket",
                    "properties": {"description": "x" * 2100},
                }
            }
        }
        errors = self.rule.validate(workflow, self.context)
        assert len(errors) == 1
        assert errors[0].severity == ErrorSeverity.ERROR
        assert errors[0].code == "CREATECASE_DESCRIPTION_OVER_LIMIT"

    def test_detection_by_action_name_only(self):
        """Action with no class but matching name should be detected."""
        workflow = {
            "actions": {
                "step_7": {
                    "id": "456",
                    "name": "Create a new Case",
                    "properties": {
                        "description": "${data['score']['desc']}"
                    },
                }
            }
        }
        errors = self.rule.validate(workflow, self.context)
        assert len(errors) == 1
        assert errors[0].code == "CREATECASE_DESCRIPTION_DYNAMIC"

    def test_location_yaml_path(self):
        workflow = {
            "actions": {
                "CreateANewCase": {
                    "id": "123",
                    "name": "Create a new Case",
                    "properties": {"description": "x" * 2100},
                }
            }
        }
        errors = self.rule.validate(workflow, self.context)
        assert errors[0].location.yaml_path == "actions.CreateANewCase.properties.description"

    def test_no_properties_skipped(self):
        workflow = {
            "actions": {
                "CreateANewCase": {
                    "id": "123",
                    "name": "Create a new Case",
                }
            }
        }
        errors = self.rule.validate(workflow, self.context)
        assert errors == []
