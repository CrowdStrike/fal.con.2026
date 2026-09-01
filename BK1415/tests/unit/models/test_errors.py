def test_validation_error_creation():
    from workflow_validator.models.errors import ValidationError, ErrorSeverity, ErrorCategory
    from workflow_validator.models.location import ValidationLocation

    location = ValidationLocation(
        file_path="test.yaml",
        line=23,
        yaml_path="actions.SendEmail.properties.to"
    )

    error = ValidationError(
        severity=ErrorSeverity.CRITICAL,
        category=ErrorCategory.CONFIGURATION,
        code="EMPTY_RECIPIENTS",
        message="SendEmail action has empty recipient list",
        location=location,
        fix_suggestion="Add recipient email addresses to the 'to:' array"
    )

    assert error.severity == ErrorSeverity.CRITICAL
    assert error.is_blocker() == True
    assert error.to_dict()["code"] == "EMPTY_RECIPIENTS"