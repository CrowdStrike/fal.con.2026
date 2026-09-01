from dataclasses import dataclass
from typing import Optional, List, Dict, Any

@dataclass
class ValidationLocation:
    file_path: str
    line: Optional[int] = None
    column: Optional[int] = None
    yaml_path: Optional[str] = None
    context_lines: Optional[List[str]] = None

    def get_friendly_path(self) -> str:
        if self.yaml_path:
            return self.yaml_path.replace(".", " → ")
        return "Unknown location"

    def has_context(self) -> bool:
        return bool(self.context_lines and len(self.context_lines) > 0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "line": self.line,
            "column": self.column,
            "yaml_path": self.yaml_path,
            "context_lines": self.context_lines
        }