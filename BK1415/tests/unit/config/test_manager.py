"""Tests for configuration management."""

import tempfile
from pathlib import Path
from workflow_validator.config.manager import ConfigurationManager
from workflow_validator.config.models import ValidationConfig


def test_configuration_loading():
    """Test loading configuration from YAML file."""
    config_yaml = """
rules:
  required_fields:
    enabled: true
    severity: critical
  style_checks:
    enabled: false

output:
  format: json
  verbose: true
  colors: false

parallel:
  max_workers: 4
  timeout: 60
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(config_yaml)
        config_path = Path(f.name)

    manager = ConfigurationManager()
    config = manager.load_config(config_path)

    assert isinstance(config, ValidationConfig)
    assert config.rules["required_fields"]["enabled"] == True
    assert config.rules["required_fields"]["severity"] == "critical"
    assert config.rules["style_checks"]["enabled"] == False
    assert config.output["format"] == "json"
    assert config.output["verbose"] == True
    assert config.output["colors"] == False
    assert config.parallel["max_workers"] == 4
    assert config.parallel["timeout"] == 60

    # Test rule helper methods
    assert config.is_rule_enabled("required_fields") == True
    assert config.is_rule_enabled("style_checks") == False
    assert config.get_rule_config("required_fields")["severity"] == "critical"

    # Cleanup
    config_path.unlink()
    print("Configuration loading test PASSED")


def test_default_configuration():
    """Test default configuration creation."""
    manager = ConfigurationManager()
    config = manager.load_config(Path("non_existent_config.yaml"))

    assert isinstance(config, ValidationConfig)
    assert config.is_rule_enabled("required_fields") == True
    assert config.output["format"] == "text"
    assert config.output["colors"] == True
    assert config.parallel["max_workers"] is None

    print("Default configuration test PASSED")


def test_configuration_save():
    """Test saving configuration to file."""
    config = ValidationConfig.default()
    config.output["format"] = "json"
    config.rules["required_fields"]["enabled"] = False

    with tempfile.NamedTemporaryFile(suffix='.yaml', delete=False) as f:
        config_path = Path(f.name)

    manager = ConfigurationManager()
    success = manager.save_config(config, config_path)

    assert success == True
    assert config_path.exists()

    # Load it back and verify
    loaded_config = manager.load_config(config_path)
    assert loaded_config.output["format"] == "json"
    assert loaded_config.is_rule_enabled("required_fields") == False

    # Cleanup
    config_path.unlink()
    print("Configuration save test PASSED")


if __name__ == "__main__":
    test_default_configuration()
    test_configuration_loading()
    test_configuration_save()