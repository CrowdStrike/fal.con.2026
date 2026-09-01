"""Tests for RichReporter - enhanced CLI error formatting."""

import pytest
from io import StringIO
from workflow_validator.cli.rich_reporter import RichReporter
from workflow_validator.models.errors import ValidationError, ErrorSeverity, ErrorCategory
from workflow_validator.models.location import ValidationLocation


class TestRichReporter:

    def test_rich_error_formatting(self):
        """Test rich formatting of validation errors."""
        location = ValidationLocation(
            file_path="test.yaml",
            line=10,
            yaml_path="actions.SendEmail.properties.to"
        )
        error = ValidationError(
            severity=ErrorSeverity.CRITICAL,
            category=ErrorCategory.CONFIGURATION,
            code="EMPTY_RECIPIENTS",
            message="SendEmail has empty recipients",
            location=location,
            fix_suggestion="Add email addresses"
        )

        output = StringIO()
        reporter = RichReporter(output)
        reporter.report_error(error)

        result = output.getvalue()
        assert "CRITICAL" in result
        assert "SendEmail" in result
        assert "Add email addresses" in result
        assert "actions.SendEmail.properties.to" in result

    def test_error_without_location(self):
        """Test formatting errors without location information."""
        error = ValidationError(
            severity=ErrorSeverity.WARNING,
            category=ErrorCategory.SCHEMA,
            code="STYLE_ISSUE",
            message="Minor formatting issue",
            location=None,
            fix_suggestion="Fix formatting"
        )

        output = StringIO()
        reporter = RichReporter(output)
        reporter.report_error(error)

        result = output.getvalue()
        assert "WARNING" in result
        assert "Minor formatting issue" in result
        assert "Fix formatting" in result

    def test_error_without_fix_suggestion(self):
        """Test formatting errors without fix suggestions."""
        location = ValidationLocation(file_path="test.yaml", line=5)
        error = ValidationError(
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.SCHEMA,
            code="SYNTAX_ERROR",
            message="Invalid YAML syntax",
            location=location,
            fix_suggestion=None
        )

        output = StringIO()
        reporter = RichReporter(output)
        reporter.report_error(error)

        result = output.getvalue()
        assert "ERROR" in result
        assert "Invalid YAML syntax" in result
        assert "Fix:" not in result  # Should not show fix section

    def test_report_summary(self):
        """Test summary reporting functionality."""
        output = StringIO()
        reporter = RichReporter(output)

        errors = ["error1", "error2"]
        warnings = ["warning1"]
        infos = []

        reporter.report_summary(errors, warnings, infos)

        result = output.getvalue()
        assert "Summary:" in result
        assert "2 errors" in result
        assert "1 warnings" in result
        assert "0 info" in result