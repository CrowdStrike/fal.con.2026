"""Tests for ParallelValidator - validates multiple files concurrently."""

import pytest
import tempfile
from pathlib import Path
from workflow_validator.core.parallel_validator import ParallelValidator, ValidationResult
from workflow_validator.registry.rule_registry import ValidationRuleRegistry
from workflow_validator.rules.required_fields import RequiredFieldsRule


class TestParallelValidator:

    def test_parallel_validation(self):
        """Test parallel validation of multiple workflow files."""
        # Set up registry with rules
        registry = ValidationRuleRegistry()
        registry.register(RequiredFieldsRule())

        # Create multiple test files
        test_files = []
        for i in range(3):
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                f.write(f"name: Test {i}\ntrigger: {{}}\nactions: {{}}")
                test_files.append(Path(f.name))

        validator = ParallelValidator(registry, max_workers=2)
        results = list(validator.validate_batch(test_files))

        assert len(results) == 3
        for result in results:
            assert result.success == True
            assert isinstance(result.file_path, Path)
            assert result.errors is not None

        # Clean up test files
        for test_file in test_files:
            test_file.unlink()

    def test_validation_result_dataclass(self):
        """Test ValidationResult dataclass structure."""
        test_path = Path("test.yaml")
        result = ValidationResult(
            file_path=test_path,
            success=True,
            errors=[],
            duration_ms=100.5
        )

        assert result.file_path == test_path
        assert result.success == True
        assert result.errors == []
        assert result.duration_ms == 100.5

    def test_invalid_file_handling(self):
        """Test handling of invalid/non-existent files."""
        # Set up registry
        registry = ValidationRuleRegistry()
        registry.register(RequiredFieldsRule())

        # Create a non-existent file path
        invalid_file = Path("non_existent.yaml")

        validator = ParallelValidator(registry, max_workers=1)
        results = list(validator.validate_batch([invalid_file]))

        assert len(results) == 1
        result = results[0]
        assert result.file_path == invalid_file
        assert result.success == False
        assert result.errors is not None
        assert len(result.errors) > 0  # Should have a file load error