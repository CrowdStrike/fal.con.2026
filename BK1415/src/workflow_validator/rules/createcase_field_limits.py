"""Validates CreateCase action field length limits against Fusion Cases API constraints."""

import re
from typing import List, Dict

from ..rules.base import ValidationRule
from ..models.context import ValidationContext
from ..models.errors import ValidationError, ErrorSeverity, ErrorCategory
from ..models.location import ValidationLocation

# Fusion Cases API limits (observed runtime errors)
DESCRIPTION_HARD_LIMIT = 2000
DESCRIPTION_SOFT_LIMIT = 1800  # 90% threshold for early warning

# Pattern matching dynamic expression bindings like ${data['...']}
DYNAMIC_EXPR_RE = re.compile(r'\$\{.+\}')

# Action classes that create cases
CREATECASE_CLASSES = {'CreateCaseV1', 'CreateCase'}

# Known action name patterns for case creation (class may be absent in exports)
CREATECASE_NAME_PATTERNS = ['create a new case', 'create case', 'createanewcase']

# Patterns that indicate the dynamic expression has a length/truncation guard.
# Each is a compiled regex tested against the raw description string.
# If ANY pattern matches, the expression is considered guarded.
LENGTH_GUARD_PATTERNS = [
    # JUEL/SpEL: .size() or .length() checks (typically in ternaries)
    re.compile(r'\.(?:size|length)\s*\(\s*\)'),
    # JUEL/SpEL: .substring(0, N) truncation
    re.compile(r'\.substring\s*\(\s*0\s*,'),
    # Python-style slice: [:N] or [:N]
    re.compile(r'\[:\s*\d+\s*\]'),
    # Generic truncate/trim function calls
    re.compile(r'(?:truncate|trim|limit|shorten)\s*\(', re.IGNORECASE),
    # Jinja2-style truncate filter: |truncate(N)
    re.compile(r'\|\s*truncate\s*\('),
    # Conditional with length comparison: > N, < N, >= N, <= N
    # (catches ternary guards like  size() > 1900 ? truncated : full)
    re.compile(r'(?:size|length|len)\s*\(\s*\)\s*[><=]{1,2}\s*\d+'),
]


class CreateCaseFieldLimitsRule(ValidationRule):
    """Checks CreateCase actions for field values that exceed Fusion API limits.

    Detects:
    - Static description strings over 2000 chars (ERROR)
    - Static description strings over 1800 chars (WARNING - near limit)
    - Dynamic expressions with a recognized truncation guard (INFO)
    - Dynamic expressions with no recognized guard (WARNING)
    """

    @property
    def name(self) -> str:
        return "CreateCase Field Limits"

    def validate(self, workflow: Dict, context: ValidationContext) -> List[ValidationError]:
        errors = []

        actions = workflow.get('actions', {})
        if not isinstance(actions, dict):
            return errors

        for action_key, action_def in actions.items():
            if not isinstance(action_def, dict):
                continue

            if not self._is_createcase_action(action_key, action_def):
                continue

            errors.extend(self._check_description(action_key, action_def, context))

        return errors

    def _is_createcase_action(self, action_key: str, action_def: Dict) -> bool:
        """Determine if this action creates a case, by class or by name."""
        action_class = action_def.get('class', '')
        if action_class in CREATECASE_CLASSES:
            return True

        # Many exported workflows omit class -- fall back to name heuristics
        action_name = action_def.get('name', '')
        key_lower = action_key.lower().replace('_', '').replace('-', '')
        name_lower = action_name.lower()

        return any(
            pattern in key_lower or pattern in name_lower
            for pattern in CREATECASE_NAME_PATTERNS
        )

    @staticmethod
    def _has_length_guard(description_str: str) -> bool:
        """Check whether a dynamic description contains a recognized truncation guard."""
        return any(pattern.search(description_str) for pattern in LENGTH_GUARD_PATTERNS)

    def _check_description(self, action_key: str, action_def: Dict,
                           context: ValidationContext) -> List[ValidationError]:
        """Check the description field for length violations."""
        errors = []
        props = action_def.get('properties', {})
        if not isinstance(props, dict):
            return errors

        description = props.get('description')
        if description is None:
            return errors

        description_str = str(description)
        location = ValidationLocation(
            file_path=context.file_path,
            yaml_path=f"actions.{action_key}.properties.description"
        )

        if DYNAMIC_EXPR_RE.search(description_str):
            if self._has_length_guard(description_str):
                errors.append(ValidationError(
                    severity=ErrorSeverity.INFO,
                    category=ErrorCategory.CONFIGURATION,
                    code="CREATECASE_DESCRIPTION_GUARDED",
                    message=(
                        f"Action '{action_key}' uses a dynamic expression for Description "
                        f"with a detected length guard. Ensure the guard truncates to "
                        f"under {DESCRIPTION_HARD_LIMIT} chars."
                    ),
                    location=location,
                ))
            else:
                errors.append(ValidationError(
                    severity=ErrorSeverity.WARNING,
                    category=ErrorCategory.CONFIGURATION,
                    code="CREATECASE_DESCRIPTION_DYNAMIC",
                    message=(
                        f"Action '{action_key}' uses a dynamic expression for Description "
                        f"with no recognized length guard. Runtime values could exceed the "
                        f"{DESCRIPTION_HARD_LIMIT}-char API limit."
                    ),
                    location=location,
                    fix_suggestion=(
                        "Add truncation logic to the expression, e.g.: "
                        "a .size() check with .substring(0, 1900), "
                        "Python slicing [:1900], "
                        "or move verbose details to a case comment."
                    )
                ))
        else:
            length = len(description_str)
            if length > DESCRIPTION_HARD_LIMIT:
                errors.append(ValidationError(
                    severity=ErrorSeverity.ERROR,
                    category=ErrorCategory.CONFIGURATION,
                    code="CREATECASE_DESCRIPTION_OVER_LIMIT",
                    message=(
                        f"Action '{action_key}' Description is {length:,} characters, "
                        f"exceeding the {DESCRIPTION_HARD_LIMIT:,}-char API limit."
                    ),
                    location=location,
                    fix_suggestion=(
                        f"Shorten the Description to under {DESCRIPTION_HARD_LIMIT:,} characters "
                        f"or move verbose content to a case comment."
                    )
                ))
            elif length > DESCRIPTION_SOFT_LIMIT:
                errors.append(ValidationError(
                    severity=ErrorSeverity.WARNING,
                    category=ErrorCategory.CONFIGURATION,
                    code="CREATECASE_DESCRIPTION_NEAR_LIMIT",
                    message=(
                        f"Action '{action_key}' Description is {length:,} characters, "
                        f"approaching the {DESCRIPTION_HARD_LIMIT:,}-char API limit "
                        f"(soft threshold: {DESCRIPTION_SOFT_LIMIT:,})."
                    ),
                    location=location,
                    fix_suggestion=(
                        "Consider shortening the Description or moving verbose sections "
                        "to a case comment to avoid runtime failures."
                    )
                ))

        return errors
