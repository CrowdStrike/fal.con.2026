def test_validation_rule_interface():
    from workflow_validator.rules.base import ValidationRule
    from workflow_validator.models.context import ValidationContext
    from workflow_validator.models.errors import ValidationError
    from typing import List

    class TestRule(ValidationRule):
        @property
        def name(self) -> str:
            return "Test Rule"

        def validate(self, workflow: dict, context: ValidationContext) -> List[ValidationError]:
            return []

    rule = TestRule()
    assert rule.name == "Test Rule"
    assert rule.validate({}, ValidationContext()) == []