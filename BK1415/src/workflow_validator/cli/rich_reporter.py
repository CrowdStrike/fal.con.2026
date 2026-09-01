"""Rich reporter for enhanced CLI error formatting and output."""

from io import StringIO
import sys
from typing import List, Dict, Optional
from ..models.errors import ValidationError, ErrorSeverity


class RichReporter:
    """Provides enhanced error formatting with rich output for CLI."""

    # Color codes for different severities
    COLORS = {
        ErrorSeverity.CRITICAL: '\033[91m',  # Red
        ErrorSeverity.ERROR: '\033[91m',     # Red
        ErrorSeverity.WARNING: '\033[93m',   # Yellow
        ErrorSeverity.INFO: '\033[94m',      # Blue
    }
    RESET_COLOR = '\033[0m'
    BOLD = '\033[1m'

    # Emoji/symbols for severities
    SYMBOLS = {
        ErrorSeverity.CRITICAL: '🚨',
        ErrorSeverity.ERROR: '❌',
        ErrorSeverity.WARNING: '⚠️',
        ErrorSeverity.INFO: 'ℹ️',
    }

    def __init__(self, output_stream=None, use_colors: bool = True):
        """Initialize rich reporter.

        Args:
            output_stream: Output stream to write to. If None, uses sys.stdout.
            use_colors: Whether to use ANSI color codes in output.
        """
        self.output = output_stream or sys.stdout
        self.use_colors = use_colors and hasattr(self.output, 'isatty') and self.output.isatty()

    def _colorize(self, text: str, severity: ErrorSeverity) -> str:
        """Apply color formatting to text based on severity."""
        if not self.use_colors:
            return text

        color = self.COLORS.get(severity, '')
        return f"{color}{text}{self.RESET_COLOR}"

    def report_error(self, error: ValidationError):
        """Format and report a single validation error.

        Args:
            error: ValidationError to format and report
        """
        # Get symbol and severity
        symbol = self.SYMBOLS.get(error.severity, '•')
        severity_str = error.severity.value.upper()

        # Format severity with color
        severity_display = self._colorize(f"{symbol} {severity_str}", error.severity)

        # Add location information if available
        location_str = ""
        if error.location:
            if error.location.yaml_path:
                location_str = f" at {self._colorize(error.location.yaml_path, ErrorSeverity.INFO)}"
            elif error.location.file_path:
                file_display = error.location.file_path
                if error.location.line:
                    file_display += f":{error.location.line}"
                location_str = f" in {self._colorize(file_display, ErrorSeverity.INFO)}"

        # Build main message
        message = f"{severity_display}: {error.message}{location_str}"

        # Add error code if available
        if error.code:
            code_display = self._colorize(f"[{error.code}]", ErrorSeverity.INFO)
            message = f"{code_display} {message}"

        # Write main message
        self.output.write(message + "\n")

        # Add fix suggestion if available
        if error.fix_suggestion:
            fix_prefix = self._colorize("  💡 Fix:", ErrorSeverity.INFO)
            self.output.write(f"{fix_prefix} {error.fix_suggestion}\n")

    def report_file_summary(self, file_path: str, errors: List[ValidationError]):
        """Report summary for a single file.

        Args:
            file_path: Path to the file being reported
            errors: List of errors found in the file
        """
        if not errors:
            success_msg = f"✅ {file_path} - No issues found"
            self.output.write(self._colorize(success_msg, ErrorSeverity.INFO) + "\n")
            return

        # Count errors by severity
        severity_counts = {}
        for error in errors:
            severity_counts[error.severity] = severity_counts.get(error.severity, 0) + 1

        # Format counts
        count_parts = []
        for severity in [ErrorSeverity.CRITICAL, ErrorSeverity.ERROR, ErrorSeverity.WARNING, ErrorSeverity.INFO]:
            count = severity_counts.get(severity, 0)
            if count > 0:
                symbol = self.SYMBOLS.get(severity, '•')
                count_display = self._colorize(f"{symbol} {count} {severity.value}", severity)
                count_parts.append(count_display)

        counts_str = ", ".join(count_parts)
        file_header = f"📄 {file_path} - {counts_str}"
        self.output.write(file_header + "\n")

    def report_batch_summary(self, total_files: int, total_errors: int, files_with_errors: int):
        """Report summary for batch validation.

        Args:
            total_files: Total number of files processed
            total_errors: Total number of errors found
            files_with_errors: Number of files with errors
        """
        self.output.write("\n" + "="*60 + "\n")
        self.output.write(f"📊 BATCH SUMMARY\n")
        self.output.write(f"   Files processed: {total_files}\n")
        self.output.write(f"   Files with issues: {files_with_errors}\n")
        self.output.write(f"   Total issues: {total_errors}\n")

        if total_errors == 0:
            success_msg = "🎉 All files passed validation!"
            self.output.write(self._colorize(success_msg, ErrorSeverity.INFO) + "\n")
        else:
            clean_files = total_files - files_with_errors
            if clean_files > 0:
                self.output.write(f"   Clean files: {clean_files}\n")

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