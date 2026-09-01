"""InvalidVariableSubscriptRule - Detects invalid integer subscripting in Fusion
``${Trigger.*}`` references.

Fusion variable expressions of the form ``${Trigger.X.Y[0]}`` (or any ``[<integer>]``
subscripting applied to a ``Trigger.*`` path) are INVALID syntax. Falcon's
``--validate-only`` API pre-check silently passes them, but post-deploy the workflow
fails with::

    property "Message" contains unknown variable "Trigger.Detection.NGSIEM.DestinationHosts[0]"

Correct usage is to reference the whole array with no subscript -
``${Trigger.Detection.NGSIEM.DestinationHosts}`` - which renders as a comma-separated
list. If a single value is needed for downstream logic, use a ``CreateVariable`` action.

Scope limits - this rule intentionally does NOT flag the following valid patterns:

* ``${data['ActionName.results'][0].field}`` -- valid string-interpolation syntax in
  comment bodies, email bodies, tag values, and other text properties. Produced
  workflows using this pattern have been server-validated, mock-executed, and run in
  client production.
* ``${data['LoopName.Iteration']}`` -- string-key bracket notation, not integer
  subscripting.
* ``${data['Action.results.#.field']}`` -- loop/array wildcard syntax (inside a
  string literal, no integer subscript token).

In ``cel_expression:`` condition fields, ``data['Action.results'][0].field`` is also
valid and is not flagged here.
"""

import re
from typing import List, Dict, Any
from ..rules.base import ValidationRule
from ..models.context import ValidationContext
from ..models.errors import ValidationError, ErrorSeverity, ErrorCategory
from ..models.location import ValidationLocation


# Matches ${Trigger....[<digits>]...} anywhere inside a ${ ... } expression where
# the variable path begins with `Trigger.`. This narrow scope avoids false
# positives on the production-valid ${data['X.results'][0].field} pattern while
# still catching ${Trigger.X.Y[0]} which genuinely fails post-deploy.
#
# Pattern breakdown:
#   \$\{          literal ${
#   \s*           optional whitespace
#   Trigger\.     path root we care about
#   [^}]*         any characters (excluding }) before the subscript
#   \[\d+\]       integer subscript e.g. [0], [12]
#   [^}]*         any characters (excluding }) after
#   \}            literal }
INVALID_SUBSCRIPT_PATTERN = re.compile(r'\$\{\s*Trigger\.[^}]*\[\d+\][^}]*\}')


class InvalidVariableSubscriptRule(ValidationRule):
    """Detects ``${...[N]...}`` integer subscripting in Fusion variable references."""

    @property
    def name(self) -> str:
        return "Invalid Variable Subscript"

    @property
    def enabled_by_default(self) -> bool:
        return True

    def validate(self, workflow: Dict, context: ValidationContext) -> List[ValidationError]:
        errors: List[ValidationError] = []

        # Top-level actions
        actions = workflow.get('actions', {}) or {}
        if isinstance(actions, dict):
            for action_name, action_def in actions.items():
                if not isinstance(action_def, dict):
                    continue
                properties = action_def.get('properties', {})
                if isinstance(properties, dict):
                    self._scan_mapping(
                        properties,
                        f"actions.{action_name}.properties",
                        context,
                        errors,
                    )

        # Top-level conditions
        conditions = workflow.get('conditions', {}) or {}
        if isinstance(conditions, dict):
            for cond_name, cond_def in conditions.items():
                if not isinstance(cond_def, dict):
                    continue
                self._scan_condition(
                    cond_def,
                    f"conditions.{cond_name}",
                    context,
                    errors,
                )

        # Loops
        loops = workflow.get('loops', {}) or {}
        if isinstance(loops, dict):
            for loop_name, loop_def in loops.items():
                if not isinstance(loop_def, dict):
                    continue

                loop_actions = loop_def.get('actions', {}) or {}
                if isinstance(loop_actions, dict):
                    for action_name, action_def in loop_actions.items():
                        if not isinstance(action_def, dict):
                            continue
                        properties = action_def.get('properties', {})
                        if isinstance(properties, dict):
                            self._scan_mapping(
                                properties,
                                f"loops.{loop_name}.actions.{action_name}.properties",
                                context,
                                errors,
                            )

                loop_conditions = loop_def.get('conditions', {}) or {}
                if isinstance(loop_conditions, dict):
                    for cond_name, cond_def in loop_conditions.items():
                        if not isinstance(cond_def, dict):
                            continue
                        self._scan_condition(
                            cond_def,
                            f"loops.{loop_name}.conditions.{cond_name}",
                            context,
                            errors,
                        )

        # Trigger (scan all string values)
        trigger = workflow.get('trigger', {})
        if isinstance(trigger, dict):
            self._scan_mapping(trigger, "trigger", context, errors)

        return errors

    def _scan_condition(
        self,
        cond_def: Dict,
        base_path: str,
        context: ValidationContext,
        errors: List[ValidationError],
    ) -> None:
        for field in ("expression", "cel_expression"):
            if field in cond_def:
                value = cond_def[field]
                if isinstance(value, str):
                    self._scan_string(value, f"{base_path}.{field}", context, errors)

    def _scan_mapping(
        self,
        node: Any,
        path: str,
        context: ValidationContext,
        errors: List[ValidationError],
    ) -> None:
        """Recursively scan a mapping/list for string values containing invalid subscripts."""
        if isinstance(node, dict):
            for key, value in node.items():
                child_path = f"{path}.{key}"
                self._scan_mapping(value, child_path, context, errors)
        elif isinstance(node, list):
            for i, item in enumerate(node):
                self._scan_mapping(item, f"{path}[{i}]", context, errors)
        elif isinstance(node, str):
            self._scan_string(node, path, context, errors)

    def _scan_string(
        self,
        value: str,
        yaml_path: str,
        context: ValidationContext,
        errors: List[ValidationError],
    ) -> None:
        matches = INVALID_SUBSCRIPT_PATTERN.findall(value)
        if not matches:
            return
        for match in matches:
            errors.append(
                ValidationError(
                    severity=ErrorSeverity.CRITICAL,
                    category=ErrorCategory.CONFIGURATION,
                    code="INVALID_VARIABLE_SUBSCRIPT",
                    message=(
                        f"Invalid integer subscript on Trigger variable '{match}'. "
                        "Fusion '${Trigger.*}' references do not support '[N]' "
                        "subscripting; the Falcon validate-only pre-check passes "
                        "but the workflow fails post-deploy with 'unknown variable' "
                        "errors. (Note: ${data['Action.results'][0].field} subscripting "
                        "IS valid and is not flagged by this rule.)"
                    ),
                    location=ValidationLocation(
                        file_path=context.file_path,
                        yaml_path=yaml_path,
                    ),
                    fix_suggestion=(
                        "Remove `[N]` subscript from the ${Trigger.*} reference "
                        "and use the whole array (renders as comma-separated), "
                        "or extract a single value via a CreateVariable action. "
                        "If the subscript was on a ${data['...results']...} path, "
                        "that form IS valid and should not have been flagged."
                    ),
                )
            )
