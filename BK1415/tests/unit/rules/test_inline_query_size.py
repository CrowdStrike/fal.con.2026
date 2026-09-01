"""Tests for InlineQuerySizeRule - validates inline LogScale query character limits."""

from workflow_validator.rules.inline_query_size import InlineQuerySizeRule
from workflow_validator.models.context import ValidationContext
from workflow_validator.models.errors import ErrorSeverity


class TestInlineQuerySizeRule:
    def setup_method(self):
        self.rule = InlineQuerySizeRule()
        self.context = ValidationContext(file_path="test.yaml")

    def test_name(self):
        assert self.rule.name == "Inline Query Size"

    def test_no_actions(self):
        errors = self.rule.validate({}, self.context)
        assert errors == []

    def test_no_inline_config(self):
        workflow = {"actions": {"Step1": {"id": "123", "properties": {}}}}
        errors = self.rule.validate(workflow, self.context)
        assert errors == []

    def test_query_under_soft_limit(self):
        workflow = {
            "actions": {
                "Step1": {
                    "id": "123",
                    "inline_configuration": {
                        "config": {"search_query": "x" * 1000}
                    },
                }
            }
        }
        errors = self.rule.validate(workflow, self.context)
        assert len(errors) == 0

    def test_query_at_soft_limit_warns(self):
        workflow = {
            "actions": {
                "Step1": {
                    "id": "123",
                    "inline_configuration": {
                        "config": {"search_query": "x" * 25000}
                    },
                }
            }
        }
        errors = self.rule.validate(workflow, self.context)
        assert len(errors) == 1
        assert errors[0].severity == ErrorSeverity.WARNING
        assert errors[0].code == "INLINE_QUERY_SIZE_WARNING"
        assert "25,000" in errors[0].message

    def test_query_at_hard_limit_errors(self):
        workflow = {
            "actions": {
                "Step1": {
                    "id": "123",
                    "inline_configuration": {
                        "config": {"search_query": "x" * 26000}
                    },
                }
            }
        }
        errors = self.rule.validate(workflow, self.context)
        assert len(errors) == 1
        assert errors[0].severity == ErrorSeverity.ERROR
        assert errors[0].code == "INLINE_QUERY_SIZE_EXCEEDED"

    def test_empty_search_query_skipped(self):
        workflow = {
            "actions": {
                "Step1": {
                    "id": "123",
                    "inline_configuration": {"config": {"search_query": ""}},
                }
            }
        }
        errors = self.rule.validate(workflow, self.context)
        assert errors == []
