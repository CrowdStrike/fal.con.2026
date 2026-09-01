"""Configuration models for workflow validator."""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class ValidationConfig:
    """Configuration for workflow validation."""
    rules: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    output: Dict[str, Any] = field(default_factory=dict)
    parallel: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def default(cls):
        """Create default configuration."""
        return cls(
            rules={
                "required_fields": {"enabled": True, "severity": "critical"},
                "action_structure": {"enabled": True, "severity": "critical"},
                "field_placement": {"enabled": True, "severity": "critical"},
                "sendemail_validation": {"enabled": True, "severity": "critical"},
            },
            output={
                "format": "text",
                "colors": True,
                "verbose": False
            },
            parallel={
                "max_workers": None,  # Use system default
                "timeout": 30
            }
        )

    def get_rule_config(self, rule_name: str) -> Dict[str, Any]:
        """Get configuration for a specific rule.

        Args:
            rule_name: Name of the rule to get config for

        Returns:
            Dictionary with rule configuration
        """
        return self.rules.get(rule_name, {"enabled": True, "severity": "warning"})

    def is_rule_enabled(self, rule_name: str) -> bool:
        """Check if a rule is enabled.

        Args:
            rule_name: Name of the rule to check

        Returns:
            True if rule is enabled, False otherwise
        """
        return self.get_rule_config(rule_name).get("enabled", True)