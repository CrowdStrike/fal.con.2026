from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any

class ErrorSeverity(Enum):
    CRITICAL = "critical"  # Blocks import
    ERROR = "error"       # Should fix before import
    WARNING = "warning"   # Best practice violations
    INFO = "info"         # Informational

class ErrorCategory(Enum):
    SCHEMA = "schema"
    CONFIGURATION = "configuration"
    SECURITY = "security"
    PERFORMANCE = "performance"
    COMPATIBILITY = "compatibility"
    SYSTEM = "system"

@dataclass
class ValidationError:
    severity: ErrorSeverity
    category: ErrorCategory
    code: str
    message: str
    location: 'ValidationLocation'
    fix_suggestion: Optional[str] = None
    auto_fix_yaml: Optional[str] = None
    metadata: Dict[str, Any] = None

    def is_blocker(self) -> bool:
        return self.severity in (ErrorSeverity.CRITICAL, ErrorSeverity.ERROR)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity.value,
            "category": self.category.value,
            "code": self.code,
            "message": self.message,
            "location": self.location.to_dict() if self.location else None,
            "fix_suggestion": self.fix_suggestion,
            "auto_fix_yaml": self.auto_fix_yaml
        }