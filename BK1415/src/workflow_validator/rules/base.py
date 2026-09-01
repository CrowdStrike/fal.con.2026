from abc import ABC, abstractmethod
from typing import List, Dict

class ValidationRule(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name for this rule"""
        pass

    @abstractmethod
    def validate(self, workflow: Dict, context: 'ValidationContext') -> List['ValidationError']:
        """Validate workflow and return any errors found"""
        pass

    @property
    def dependencies(self) -> List[str]:
        """Names of rules that must run before this one"""
        return []

    @property
    def enabled_by_default(self) -> bool:
        """Whether this rule is enabled by default"""
        return True