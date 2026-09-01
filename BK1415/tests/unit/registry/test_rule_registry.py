def test_rule_registry_registration():
    from workflow_validator.registry.rule_registry import ValidationRuleRegistry
    from workflow_validator.rules.base import ValidationRule
    from workflow_validator.models.context import ValidationContext
    from workflow_validator.models.errors import ValidationError

    class MockRule(ValidationRule):
        @property
        def name(self) -> str:
            return "Mock Rule"

        def validate(self, workflow: dict, context: ValidationContext) -> List[ValidationError]:
            return []

    registry = ValidationRuleRegistry()
    rule = MockRule()

    registry.register(rule)
    rules = registry.get_enabled_rules()

    assert len(rules) == 1
    assert rules[0].name == "Mock Rule"