from dataclasses import dataclass
from typing import Dict, Any, Optional

@dataclass
class ValidationContext:
    file_path: str = ""
    raw_content: str = ""
    config: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}