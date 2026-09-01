"""InlineQueryPipesRule - Validates inline LogScale query pipe/subquery limits.

LogScale enforces max=100 pipes per query.
Confirmed via LogScale API error: "Too many pipes/subqueries in query. count=101. max=100"
Reference: OWL-7321 (2026-02).

Pipe Counting Logic (verified against LogScale API, 2026-03-03):
- LogScale counts top-level '|' pipe operators only
- '|' inside string literals ("..."), regex literals (/.../), and
  brace blocks ({...} including case blocks) are NOT counted
- LogScale adds +1 implicit pipe for the query itself
- API count = top_level_pipes + 1; limit is count <= 100
- Therefore max 99 top-level '|' characters allowed

Previous bugs:
  v1 (original): Counted all '|' characters naively, over-counting on
    format strings and regex.
  v2 (2026-03-03 first fix): Used regex .*? to extract case blocks,
    which broke on nested braces. Also added incorrect case branch
    penalties based on a misunderstanding of LogScale counting.
  v3 (current): Character-level parser that skips |'s inside strings,
    regex, and braces. No case branch penalties — verified that LogScale
    treats case branch |'s as internal to the { } block.
"""

from typing import List, Dict
from ..rules.base import ValidationRule
from ..models.context import ValidationContext
from ..models.errors import ValidationError, ErrorSeverity, ErrorCategory
from ..models.location import ValidationLocation

QUERY_PIPE_SOFT_LIMIT = 95
QUERY_PIPE_HARD_LIMIT = 100


def _count_top_level_pipes(query: str) -> int:
    """Count top-level pipe operators in a LogScale query.

    Skips '|' characters inside:
    - String literals: "..."
    - Regex literals: /.../ (detected after = or ! or space)
    - Brace blocks: { ... } (includes case blocks, nested braces)

    Returns the number of top-level '|' pipe operators.
    """
    pipes = 0
    brace_depth = 0
    in_string = False
    in_regex = False
    i = 0
    n = len(query)

    while i < n:
        ch = query[i]

        if in_string:
            if ch == '\\' and i + 1 < n:
                i += 2  # skip escaped character
                continue
            if ch == '"':
                in_string = False
        elif in_regex:
            if ch == '\\' and i + 1 < n:
                i += 2  # skip escaped character
                continue
            if ch == '/':
                in_regex = False
        elif brace_depth > 0:
            # Inside braces — track nesting but skip pipe counting.
            # Still need to handle strings/regex inside braces to
            # correctly find the matching closing brace.
            if ch == '"':
                in_string = True
            elif ch == '/' and i > 0 and query[i - 1] in ('=', ' ', '!'):
                in_regex = True
            elif ch == '{':
                brace_depth += 1
            elif ch == '}':
                brace_depth -= 1
        else:
            # Top level — count pipes, track context
            if ch == '"':
                in_string = True
            elif ch == '/' and i > 0 and query[i - 1] in ('=', ' ', '!'):
                in_regex = True
            elif ch == '{':
                brace_depth += 1
            elif ch == '|':
                pipes += 1

        i += 1

    return pipes


class InlineQueryPipesRule(ValidationRule):

    @property
    def name(self) -> str:
        return "Inline Query Pipe Count"

    def _count_pipes(self, search_query: str) -> int:
        """Count pipes as LogScale would count them.

        LogScale API count = top_level_pipes + 1 (implicit first pipe).
        The limit is count <= 100, so max 99 top-level '|' characters.

        Returns:
            The LogScale API pipe count (top_level + 1).
        """
        return _count_top_level_pipes(search_query) + 1

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

            pipe_count = self._count_pipes(search_query)

            if pipe_count > QUERY_PIPE_HARD_LIMIT:
                errors.append(ValidationError(
                    severity=ErrorSeverity.ERROR,
                    category=ErrorCategory.PERFORMANCE,
                    code="INLINE_QUERY_PIPE_EXCEEDED",
                    message=(
                        f"Inline query '{action_name}' has {pipe_count} pipes "
                        f"(API count, includes +1 implicit) — "
                        f"exceeds {QUERY_PIPE_HARD_LIMIT} pipe limit. "
                        f"Fusion will reject with 'Too many pipes/subqueries' error."
                    ),
                    location=ValidationLocation(
                        file_path=context.file_path,
                        yaml_path=f"actions.{action_name}.inline_configuration.search_query",
                    ),
                    fix_suggestion="Remove self-assignment no-ops, consolidate logic, or remove dead code to reduce pipe count",
                ))
            elif pipe_count >= QUERY_PIPE_SOFT_LIMIT:
                headroom = QUERY_PIPE_HARD_LIMIT - pipe_count
                errors.append(ValidationError(
                    severity=ErrorSeverity.WARNING,
                    category=ErrorCategory.PERFORMANCE,
                    code="INLINE_QUERY_PIPE_WARNING",
                    message=(
                        f"Inline query '{action_name}' has {pipe_count} pipes "
                        f"(API count, includes +1 implicit) — "
                        f"approaching {QUERY_PIPE_HARD_LIMIT} pipe limit ({headroom} remaining). "
                        f"Adding more logic may hit the limit."
                    ),
                    location=ValidationLocation(
                        file_path=context.file_path,
                        yaml_path=f"actions.{action_name}.inline_configuration.search_query",
                    ),
                    fix_suggestion="Consider removing self-assignment no-ops and dead code to create headroom",
                ))

        return errors
