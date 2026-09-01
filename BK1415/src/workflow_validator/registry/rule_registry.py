from typing import List, Dict, Optional
from ..rules.base import ValidationRule

class ValidationRuleRegistry:
    def __init__(self):
        self._rules: List[ValidationRule] = []
        self._disabled_rules: set = set()

    def register(self, rule: ValidationRule):
        """Register a validation rule"""
        self._rules.append(rule)

    def get_enabled_rules(self) -> List[ValidationRule]:
        """Get all enabled validation rules"""
        return [rule for rule in self._rules
                if rule.name not in self._disabled_rules and rule.enabled_by_default]

    def get_all_rules(self) -> List[ValidationRule]:
        """Get all registered rules regardless of enabled status"""
        return self._rules.copy()

    def disable_rule(self, rule_name: str):
        """Disable a rule by name"""
        self._disabled_rules.add(rule_name)

    def enable_rule(self, rule_name: str):
        """Enable a rule by name"""
        self._disabled_rules.discard(rule_name)