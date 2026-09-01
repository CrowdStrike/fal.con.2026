"""OrphanedYamlFragmentsRule - Detects stray '- ${...}' list items.

A list item (- ${...}) is only truly orphaned if it doesn't appear under a
recognized list-valued property. Many Fusion SOAR action properties
legitimately contain YAML lists, so we check the parent field before flagging.

This rule operates on raw_content from the ValidationContext rather than the
parsed workflow dict, because YAML parsing may collapse or discard the
fragments we need to detect.
"""

from typing import List, Dict
from ..rules.base import ValidationRule
from ..models.context import ValidationContext
from ..models.errors import ValidationError, ErrorSeverity, ErrorCategory
from ..models.location import ValidationLocation

KNOWN_LIST_FIELDS = {
    'fields', '_fields', 'detections', 'email_addresses', 'ips',
    'tags', 'status', 'to', 'next', 'display', 'required',
    'workflow_csv_header_fields', 'execution_cid',
}


class OrphanedYamlFragmentsRule(ValidationRule):

    @property
    def name(self) -> str:
        return "Orphaned YAML Fragments"

    def validate(self, workflow: Dict, context: ValidationContext) -> List[ValidationError]:
        errors = []
        raw = context.raw_content
        if not raw:
            return errors

        lines = raw.split('\n')

        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped.startswith('- ${'):
                continue

            item_indent = len(line) - len(line.lstrip())

            # Walk backwards to find the parent key
            parent_key = None
            for j in range(i - 1, max(0, i - 10) - 1, -1):
                prev_line = lines[j]
                if not prev_line.strip() or prev_line.strip().startswith('#'):
                    continue
                prev_indent = len(prev_line) - len(prev_line.lstrip())
                if prev_indent < item_indent and ':' in prev_line:
                    parent_key = prev_line.strip().split(':')[0].strip()
                    break

            if parent_key and parent_key in KNOWN_LIST_FIELDS:
                continue

            # Check broader context for nearby recognized list fields
            context_start = max(0, i - 5)
            context_lines = lines[context_start:i]
            context_text = '\n'.join(context_lines)
            if any(f'{kf}:' in context_text for kf in KNOWN_LIST_FIELDS):
                continue

            line_num = i + 1
            errors.append(ValidationError(
                severity=ErrorSeverity.WARNING,
                category=ErrorCategory.SCHEMA,
                code="ORPHANED_YAML_FRAGMENT",
                message=(
                    f"List item '- ${{...}}' may be orphaned "
                    f"(parent field '{parent_key}' not recognized)"
                ),
                location=ValidationLocation(
                    file_path=context.file_path,
                    line=line_num,
                    yaml_path=f"line {line_num}",
                ),
                fix_suggestion="Verify this list item belongs to a valid parent field, or remove if leftover from editing",
            ))

        return errors
