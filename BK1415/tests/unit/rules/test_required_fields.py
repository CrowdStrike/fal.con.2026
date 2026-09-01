def test_required_fields_rule():
    from workflow_validator.rules.required_fields import RequiredFieldsRule
    from workflow_validator.models.context import ValidationContext
    from workflow_validator.models.errors import ErrorSeverity

    rule = RequiredFieldsRule()
    context = ValidationContext(file_path="test.yaml")

    # Test missing required field
    workflow = {"name": "Test", "actions": {}}  # Missing trigger
    errors = rule.validate(workflow, context)

    assert len(errors) == 1
    assert errors[0].code == "MISSING_REQUIRED_FIELD"
    assert errors[0].severity == ErrorSeverity.CRITICAL
    assert "trigger" in errors[0].message