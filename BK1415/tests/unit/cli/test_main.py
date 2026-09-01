"""Tests for main CLI interface."""

import tempfile
from pathlib import Path
from workflow_validator.cli.main import validate_files


def test_cli_validation():
    """Test CLI validation functionality."""
    # Create test workflow files
    valid_yaml = "name: Valid Test\ntrigger: {}\nactions: {}"
    invalid_yaml = "name: Invalid Test\nactions: {}"  # Missing trigger

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(valid_yaml)
        valid_file = Path(f.name)

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(invalid_yaml)
        invalid_file = Path(f.name)

    # Test with valid file
    exit_code = validate_files([valid_file])
    assert exit_code == 0, "Valid file should return exit code 0"

    # Test with invalid file
    exit_code = validate_files([invalid_file])
    assert exit_code == 1, "Invalid file should return exit code 1"

    # Test with mixed files
    exit_code = validate_files([valid_file, invalid_file])
    assert exit_code == 1, "Mixed files with errors should return exit code 1"

    # Cleanup
    valid_file.unlink()
    invalid_file.unlink()

    print("CLI validation test PASSED")


if __name__ == "__main__":
    test_cli_validation()