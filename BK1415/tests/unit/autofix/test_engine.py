def test_yaml_autofix_with_backup():
    from workflow_validator.autofix.engine import AutoFixEngine
    from workflow_validator.models.errors import ValidationError, ErrorSeverity, ErrorCategory
    from workflow_validator.models.location import ValidationLocation
    import tempfile
    from pathlib import Path

    # Create test YAML with field placement error
    test_yaml = """name: Test Workflow
actions:
  SendEmail:
    id: "test-id"
    properties:
      to: ["user@example.com"]
    workflow_csv_header_fields: []  # Wrong location
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(test_yaml)
        f.flush()

        location = ValidationLocation(file_path=f.name, line=6, yaml_path="actions.SendEmail.workflow_csv_header_fields")
        error = ValidationError(
            severity=ErrorSeverity.CRITICAL,
            category=ErrorCategory.CONFIGURATION,
            code="INVALID_FIELD_PLACEMENT",
            message="Field at wrong level",
            location=location
        )

        engine = AutoFixEngine()
        result = engine.apply_fix(error, backup=True)

        assert result.success == True
        assert result.backup_created == True
        assert Path(f.name + ".backup").exists()

        # Verify fix was applied
        fixed_content = Path(f.name).read_text()
        assert "workflow_csv_header_fields: []" in fixed_content
        assert "properties:" in fixed_content