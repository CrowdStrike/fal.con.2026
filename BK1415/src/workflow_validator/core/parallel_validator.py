"""Parallel validation engine for processing multiple workflow files concurrently."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Iterator, Optional
from pathlib import Path
from dataclasses import dataclass
import time
import yaml

from ..registry.rule_registry import ValidationRuleRegistry
from ..models.context import ValidationContext
from ..models.errors import ValidationError


@dataclass
class ValidationResult:
    """Result of validating a single workflow file."""
    file_path: Path
    success: bool
    errors: List[ValidationError] = None
    duration_ms: float = 0

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class ParallelValidator:
    """Validates multiple workflow files in parallel using ThreadPoolExecutor."""

    def __init__(self, registry: ValidationRuleRegistry, max_workers: int = None):
        """Initialize parallel validator.

        Args:
            registry: ValidationRuleRegistry containing validation rules
            max_workers: Maximum number of worker threads. If None, uses ThreadPoolExecutor default.
        """
        self.registry = registry
        self.max_workers = max_workers

    def validate_batch(self, file_paths: List[Path]) -> Iterator[ValidationResult]:
        """Validate multiple files in parallel.

        Args:
            file_paths: List of Path objects to validate

        Yields:
            ValidationResult objects as they complete
        """
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self._validate_single, path): path for path in file_paths}

            for future in as_completed(futures):
                yield future.result()

    def _validate_single(self, file_path: Path) -> ValidationResult:
        """Validate a single file using all registered validation rules.

        Args:
            file_path: Path to workflow file to validate

        Returns:
            ValidationResult with success/failure status and any errors found
        """
        start_time = time.time()
        all_errors = []

        try:
            # Load workflow content
            with open(file_path, 'r', encoding='utf-8') as f:
                raw_content = f.read()
                workflow = yaml.safe_load(raw_content)

            # Create validation context
            context = ValidationContext(
                file_path=str(file_path),
                raw_content=raw_content
            )

            # Run all enabled rules
            for rule in self.registry.get_enabled_rules():
                try:
                    rule_errors = rule.validate(workflow, context)
                    all_errors.extend(rule_errors)
                except Exception as e:
                    # Create error for rule failure
                    from ..models.location import ValidationLocation
                    from ..models.errors import ErrorSeverity, ErrorCategory

                    location = ValidationLocation(file_path=str(file_path))
                    rule_error = ValidationError(
                        severity=ErrorSeverity.ERROR,
                        category=ErrorCategory.SYSTEM,
                        code="RULE_EXECUTION_ERROR",
                        message=f"Rule '{rule.name}' failed to execute: {e}",
                        location=location
                    )
                    all_errors.append(rule_error)

            duration_ms = (time.time() - start_time) * 1000

            # Determine success - no critical or error level issues
            from ..models.errors import ErrorSeverity
            success = not any(
                error.severity in (ErrorSeverity.CRITICAL, ErrorSeverity.ERROR)
                for error in all_errors
            )

            return ValidationResult(
                file_path=file_path,
                success=success,
                errors=all_errors,
                duration_ms=duration_ms
            )

        except Exception as e:
            # Handle file loading errors
            duration_ms = (time.time() - start_time) * 1000
            from ..models.location import ValidationLocation
            from ..models.errors import ErrorSeverity, ErrorCategory

            location = ValidationLocation(file_path=str(file_path))
            error = ValidationError(
                severity=ErrorSeverity.CRITICAL,
                category=ErrorCategory.SYSTEM,
                code="FILE_LOAD_ERROR",
                message=f"Failed to load workflow file: {e}",
                location=location
            )

            return ValidationResult(
                file_path=file_path,
                success=False,
                errors=[error],
                duration_ms=duration_ms
            )