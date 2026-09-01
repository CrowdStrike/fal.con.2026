"""InlineQuerySizeRule - Validates inline LogScale query character limits.

Fusion has an empirical ~26,000 character limit for inline queries.
Exceeding this causes generic 500 errors during execution.
"""

from typing import List, Dict
from ..rules.base import ValidationRule
from ..models.context import ValidationContext
from ..models.errors import ValidationError, ErrorSeverity, ErrorCategory
from ..models.location import ValidationLocation

# Empirical limits (no official documentation as of 2026-02).
QUERY_SIZE_SOFT_LIMIT = 25000
QUERY_SIZE_HARD_LIMIT = 26000


class InlineQuerySizeRule(ValidationRule):

    @property
    def name(self) -> str:
        return "Inline Query Size"

    def validate(self, workflow: Dict, context: ValidationContext) -> List[ValidationError]:
        errors = []
        actions = workflow.get('actions', {})
        if not isinstance(actions, dict):
            return errors

        for action_name, action_data in actions.items():
            if not isinstance(action_data, dict):
                continue

            inline_config = action_data.get('inline_configuration', {})
            if not inline_config:
                continue

            config = inline_config.get('config', {})
            if not isinstance(config, dict):
                continue

            search_query = config.get('search_query', '')
            if not search_query:
                continue

            char_count = len(search_query)
            line_count = search_query.count('\n') + 1

            if char_count >= QUERY_SIZE_HARD_LIMIT:
                errors.append(ValidationError(
                    severity=ErrorSeverity.ERROR,
                    category=ErrorCategory.PERFORMANCE,
                    code="INLINE_QUERY_SIZE_EXCEEDED",
                    message=(
                        f"Inline query '{action_name}' is {char_count:,} chars ({line_count} lines) — "
                        f"exceeds {QUERY_SIZE_HARD_LIMIT:,} char hard limit. "
                        f"Fusion will reject this with a generic 500 error."
                    ),
                    location=ValidationLocation(
                        file_path=context.file_path,
                        yaml_path=f"actions.{action_name}.inline_configuration.search_query",
                    ),
                    fix_suggestion="Strip comments, consolidate verbose formatting, and remove redundant assignments to reduce query size",
                ))
            elif char_count >= QUERY_SIZE_SOFT_LIMIT:
                headroom = QUERY_SIZE_HARD_LIMIT - char_count
                errors.append(ValidationError(
                    severity=ErrorSeverity.WARNING,
                    category=ErrorCategory.PERFORMANCE,
                    code="INLINE_QUERY_SIZE_WARNING",
                    message=(
                        f"Inline query '{action_name}' is {char_count:,} chars ({line_count} lines) — "
                        f"approaching {QUERY_SIZE_HARD_LIMIT:,} char limit ({headroom:,} chars remaining). "
                        f"Adding more logic may cause Fusion 500 errors."
                    ),
                    location=ValidationLocation(
                        file_path=context.file_path,
                        yaml_path=f"actions.{action_name}.inline_configuration.search_query",
                    ),
                    fix_suggestion="Consider stripping comments and consolidating formatting to create headroom",
                ))

        return errors
