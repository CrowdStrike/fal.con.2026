"""Configuration manager for loading and managing validation settings."""

import yaml
from pathlib import Path
from typing import Optional

from .models import ValidationConfig


class ConfigurationManager:
    """Manages loading and validation of configuration files."""

    DEFAULT_CONFIG_NAMES = [
        '.workflow-validator.yaml',
        '.workflow-validator.yml',
        'workflow-validator.yaml',
        'workflow-validator.yml'
    ]

    def load_config(self, config_path: Optional[Path] = None) -> ValidationConfig:
        """Load configuration from file or return default.

        Args:
            config_path: Optional path to config file. If None, searches for default config files.

        Returns:
            ValidationConfig instance
        """
        if config_path:
            return self._load_config_file(config_path)

        # Search for default config files
        for config_name in self.DEFAULT_CONFIG_NAMES:
            config_file = Path(config_name)
            if config_file.exists():
                return self._load_config_file(config_file)

        # Return default configuration if no config file found
        return ValidationConfig.default()

    def _load_config_file(self, config_path: Path) -> ValidationConfig:
        """Load configuration from a specific file.

        Args:
            config_path: Path to configuration file

        Returns:
            ValidationConfig instance
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            if not data:
                return ValidationConfig.default()

            # Merge with defaults
            default_config = ValidationConfig.default()

            # Update rules configuration
            if 'rules' in data:
                for rule_name, rule_config in data['rules'].items():
                    if rule_name in default_config.rules:
                        default_config.rules[rule_name].update(rule_config)
                    else:
                        default_config.rules[rule_name] = rule_config

            # Update output configuration
            if 'output' in data:
                default_config.output.update(data['output'])

            # Update parallel configuration
            if 'parallel' in data:
                default_config.parallel.update(data['parallel'])

            return default_config

        except Exception as e:
            print(f"Warning: Failed to load config from {config_path}: {e}")
            return ValidationConfig.default()

    def save_config(self, config: ValidationConfig, config_path: Path) -> bool:
        """Save configuration to file.

        Args:
            config: ValidationConfig to save
            config_path: Path where to save the configuration

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            config_dict = {
                'rules': config.rules,
                'output': config.output,
                'parallel': config.parallel
            }

            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.safe_dump(config_dict, f, default_flow_style=False, indent=2)

            return True

        except Exception as e:
            print(f"Error: Failed to save config to {config_path}: {e}")
            return False