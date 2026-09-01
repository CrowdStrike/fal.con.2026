from pathlib import Path
from typing import List, Dict, Set
from ..rules.base import ValidationRule
from ..models.context import ValidationContext
from ..models.errors import ValidationError, ErrorSeverity, ErrorCategory
from ..models.location import ValidationLocation


def _load_builtin_action_ids() -> Set[str]:
    """Load the allow-list of action UUIDs that don't require explicit `class:`.

    File lives next to this package at src/workflow_validator/known_action_ids.yaml.
    Fails safe (returns empty set) if the file is missing or unreadable.
    """
    ids: Set[str] = set()
    try:
        import yaml
    except ImportError:
        return ids
    path = Path(__file__).resolve().parent.parent / "known_action_ids.yaml"
    if not path.is_file():
        return ids
    try:
        data = yaml.safe_load(path.read_text()) or {}
    except Exception:
        return ids
    for entry in (data.get("builtin_action_ids") or []):
        if isinstance(entry, dict) and entry.get("id"):
            ids.add(str(entry["id"]).strip())
        elif isinstance(entry, str):
            ids.add(entry.strip())
    return ids


_BUILTIN_IDS: Set[str] = _load_builtin_action_ids()


class ActionStructureRule(ValidationRule):
    """Validates action structure requirements based on CrowdStrike research.

    Ensures actions have:
    - Required 'id' field
    - 'class' field for custom actions (not required for built-in actions)
    - Proper action definition structure
    """

    @property
    def name(self) -> str:
        return "Action Structure"

    @property
    def enabled_by_default(self) -> bool:
        return True

    def validate(self, workflow: Dict, context: ValidationContext) -> List[ValidationError]:
        errors = []

        if 'actions' not in workflow:
            return errors

        actions = workflow.get('actions', {})
        if not isinstance(actions, dict):
            return errors

        for action_name, action_def in actions.items():
            if not isinstance(action_def, dict):
                continue

            # Check for required action fields
            required_fields = ['id']
            for field in required_fields:
                if field not in action_def:
                    location = ValidationLocation(
                        file_path=context.file_path,
                        yaml_path=f"actions.{action_name}.{field}"
                    )
                    errors.append(ValidationError(
                        severity=ErrorSeverity.CRITICAL,
                        category=ErrorCategory.SCHEMA,
                        code="MISSING_ACTION_FIELD",
                        message=f"Action '{action_name}' missing required field: '{field}'",
                        location=location,
                        fix_suggestion=f"Add '{field}:' field to action '{action_name}'"
                    ))

            # Check for class field - informational, not a blocker.
            # Suppress for built-in actions (recognised by action id in
            # known_action_ids.yaml) or by naming heuristic. Built-in actions
            # don't use `class:` because Fusion infers the class from the id.
            if 'class' not in action_def:
                action_id = str(action_def.get('id', '')).strip()
                if self._is_builtin(action_name, action_id):
                    continue
                location = ValidationLocation(
                    file_path=context.file_path,
                    yaml_path=f"actions.{action_name}.class"
                )
                errors.append(ValidationError(
                    severity=ErrorSeverity.INFO,
                    category=ErrorCategory.CONFIGURATION,
                    code="MISSING_ACTION_CLASS",
                    message=f"Action '{action_name}' has no explicit 'class' field (Fusion may infer it at import)",
                    location=location,
                    fix_suggestion="Add 'class:' field to specify the action type explicitly"
                ))

        return errors

    def _is_builtin(self, action_name: str, action_id: str) -> bool:
        """An action is treated as built-in (no `class:` needed) if:

        - its `id` is in the shipped allow-list, OR
        - the Fusion composite-id (<builtin_id>~<suffix>) root is in the list, OR
        - its name matches a legacy built-in pattern (CreateVariable, Decision, Wait...).
        """
        if action_id:
            if action_id in _BUILTIN_IDS:
                return True
            # Composite ids like "<base>~<extension>" — base is what identifies type
            root = action_id.split('~', 1)[0]
            if root in _BUILTIN_IDS:
                return True

        return self._is_builtin_action(action_name)

    def _is_builtin_action(self, action_name: str) -> bool:
        """Legacy name-based heuristic (kept for backward-compat)."""
        builtin_patterns = ['CreateVariable', 'UpdateVariable', 'Decision', 'Wait']
        return any(pattern in action_name for pattern in builtin_patterns)
