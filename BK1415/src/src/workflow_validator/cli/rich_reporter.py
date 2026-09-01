"""Rich reporter for enhanced CLI error formatting and output."""

from io import StringIO
import sys
from typing import List
from ..models.errors import ValidationError, ErrorSeverity


class RichReporter:
    """Provides enhanced error formatting with rich output for CLI."""

    def __init__(self, output_stream=None):
        """Initialize rich reporter.

        Args:
            output_stream: Output stream to write to. If None, uses StringIO.
        """
        self.output = output_stream or StringIO()

    def report_error(self, error: ValidationError):
        """Format and report a single validation error.

        Args:
            error: ValidationError to format and report
        """
        # Format severity with uppercase
        severity_str = error.severity.value.upper()

        # Add location information if available
        location_str = ""
        if error.location:
            if error.location.yaml_path:
                location_str = f" at {error.location.yaml_path}"
            elif error.location.file_path:
                location_str = f" in {error.location.file_path}"
                if error.location.line:
                    location_str += f":{error.location.line}"

        # Build main message
        message = f"{severity_str}: {error.message}{location_str}"

        # Add fix suggestion if available
        if error.fix_suggestion:
            message += f"\n  Fix: {error.fix_suggestion}"

        # Write to output
        self.output.write(message + "\n")

    def report_summary(self, errors: List, warnings: List, infos: List):
        """Report validation summary with counts.

        Args:
            errors: List of error messages/objects
            warnings: List of warning messages/objects
            infos: List of info messages/objects
        """
        error_count = len(errors)
        warning_count = len(warnings)
        info_count = len(infos)

        summary = f"\nSummary: {error_count} errors, {warning_count} warnings, {info_count} info\n"
        self.output.write(summary)

    def get_output(self) -> str:
        """Get the accumulated output as a string.

        Returns:
            String containing all formatted output
        """
        if isinstance(self.output, StringIO):
            return self.output.getvalue()
        return ""