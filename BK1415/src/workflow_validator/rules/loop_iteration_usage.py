"""LoopIterationUsageRule - Warns when a loop's actions never reference its iteration value.

Fusion's own UI emits a warning when a loop-internal action doesn't reference the
loop iteration value::

    It is recommended to use an iteration value from the loop '<name>' in your action.

That warning indicates the loop is running N times but doing the same thing each
iteration - usually a bug (someone forgot to reference the current user/detection/item
in the action's body).

The iteration reference syntax is ``${data['<LoopName>.Iteration']}`` (capital I,
singular). It may appear with double quotes or with YAML-escape-doubled single quotes
(``${data[''<LoopName>.Iteration'']}``) in emitted YAML; after ``yaml.safe_load``
parses the string, the doubled single quotes collapse to literal singles.

If NO action inside a loop references the iteration variable in any string value,
this rule emits a single WARNING for that loop.
"""

from typing import List, Dict, Any, Iterable
from ..rules.base import ValidationRule
from ..models.context import ValidationContext
from ..models.errors import ValidationError, ErrorSeverity, ErrorCategory
from ..models.location import ValidationLocation


class LoopIterationUsageRule(ValidationRule):
    """Warns when a loop contains no action referencing ``${data['<LoopName>.Iteration']}``."""

    @property
    def name(self) -> str:
        return "Loop Iteration Usage"

    @property
    def enabled_by_default(self) -> bool:
        return True

    def validate(self, workflow: Dict, context: ValidationContext) -> List[ValidationError]:
        errors: List[ValidationError] = []

        loops = workflow.get('loops', {}) or {}
        if not isinstance(loops, dict):
            return errors

        for loop_name, loop_def in loops.items():
            if not isinstance(loop_def, dict):
                continue

            loop_actions = loop_def.get('actions', {}) or {}
            if not isinstance(loop_actions, dict) or not loop_actions:
                # No inner actions -- nothing to warn about.
                continue

            # Build all three literal variants we want to look for.
            # The doubled-single-quote form is what raw (unparsed) YAML would contain;
            # after yaml.safe_load it collapses to the single-quote form, but we match
            # it anyway in case the scanner is handed raw text.
            needles = (
                f"data['{loop_name}.Iteration']",
                f'data["{loop_name}.Iteration"]',
                f"data[''{loop_name}.Iteration'']",
            )

            found = False
            for action_name, action_def in loop_actions.items():
                if not isinstance(action_def, dict):
                    continue
                properties = action_def.get('properties', {})
                if self._contains_any(properties, needles):
                    found = True
                    break

            if not found:
                errors.append(
                    ValidationError(
                        severity=ErrorSeverity.WARNING,
                        category=ErrorCategory.CONFIGURATION,
                        code="LOOP_ITERATION_NOT_USED",
                        message=(
                            f"Loop '{loop_name}' has no action referencing its iteration "
                            f"value. Fusion recommends using an iteration value "
                            f"(${{data['{loop_name}.Iteration']}}) from the loop in at "
                            f"least one inner action; otherwise the loop does the same "
                            f"thing each iteration."
                        ),
                        location=ValidationLocation(
                            file_path=context.file_path,
                            yaml_path=f"loops.{loop_name}",
                        ),
                        fix_suggestion=(
                            f"Reference the current iteration via "
                            f"${{data['{loop_name}.Iteration']}} in at least one "
                            f"loop-internal action's field (subject, msg, parameter). "
                            f"If the loop intentionally runs constant work, exclude "
                            f"this rule in config."
                        ),
                    )
                )

        return errors

    def _contains_any(self, node: Any, needles: Iterable[str]) -> bool:
        """Return True if any string inside `node` (recursively) contains any needle."""
        if isinstance(node, dict):
            for v in node.values():
                if self._contains_any(v, needles):
                    return True
            return False
        if isinstance(node, list):
            for item in node:
                if self._contains_any(item, needles):
                    return True
            return False
        if isinstance(node, str):
            return any(n in node for n in needles)
        return False
