"""SoarPayloadSizeRule - Detects CreateLookupFile actions combining multiple SOAR outputs.

When a CreateLookupFile CEL expression references multiple upstream SOAR action
outputs, the combined payload can exceed Fusion's ~1MB message size limit at runtime.
SOAR actions return full API response objects (~14KB per MS Graph alert, 50/page),
and combining 2+ pages easily exceeds 1MB.

Created after the Defender-Sync v2 incident (2026-03-26) where combined alert pages
caused error_code 500, "message size is too large".
"""

import re
from typing import List, Dict

from ..rules.base import ValidationRule
from ..models.context import ValidationContext
from ..models.errors import ValidationError, ErrorSeverity, ErrorCategory
from ..models.location import ValidationLocation

# Matches data["<ActionNodeId>.API_Integration.<namespace>.body.value"]
# Captures the ActionNodeId prefix (everything before .API_Integration).
SOAR_DATA_REF_PATTERN = re.compile(
    r'data\["([^"]+?)\.API_Integration\.[^"]*?\.body\.value"\]'
)


class SoarPayloadSizeRule(ValidationRule):
    """Flags CreateLookupFile actions that reference 2+ distinct SOAR action outputs.

    Each SOAR action returns a full API response (~700KB for 50 MS Graph alerts).
    Combining multiple SOAR outputs in one CEL expression risks exceeding
    Fusion's ~1MB message size limit.
    """

    @property
    def name(self) -> str:
        return "SOAR Payload Size"

    @property
    def enabled_by_default(self) -> bool:
        return True

    def validate(self, workflow: Dict, context: ValidationContext) -> List[ValidationError]:
        errors = []

        actions = workflow.get('actions', {})
        for action_key, action_data in actions.items():
            if not isinstance(action_data, dict):
                continue

            if action_data.get('class') != 'CreateLookupFile':
                continue

            cel_text = action_data.get('properties', {}).get('lookup_file_content_text', '')
            if not cel_text:
                continue

            refs = SOAR_DATA_REF_PATTERN.findall(cel_text)
            unique_sources = set(refs)

            if len(unique_sources) >= 2:
                errors.append(ValidationError(
                    severity=ErrorSeverity.ERROR,
                    category=ErrorCategory.PERFORMANCE,
                    code="SOAR_MULTI_PAGE_LOOKUP_RISK",
                    message=(
                        f"CreateLookupFile '{action_key}' references {len(unique_sources)} "
                        f"SOAR action outputs in one CEL expression: {sorted(unique_sources)}. "
                        f"SOAR actions return full API response objects (often 10-40KB per item) "
                        f"and do NOT support $select to reduce payload size. With 50+ items per "
                        f"page, combined payloads routinely exceed Fusion's ~1MB message size "
                        f"limit, causing runtime error_code 500 \"message size is too large\"."
                    ),
                    location=ValidationLocation(
                        file_path=context.file_path,
                        yaml_path=f"actions.{action_key}.properties.lookup_file_content_text",
                    ),
                    fix_suggestion=(
                        "Split into one CreateLookupFile per SOAR page. Change routing to "
                        "interleave: SOAR(page1) -> CreateLookupFile_P1 -> SOAR(page2) -> "
                        "CreateLookupFile_P2. Each CreateLookupFile CEL should reference only "
                        "its page's data. Update the downstream Inline.QueryEvent to accept "
                        "multiple lookup file inputs and add a separate case{} branch per "
                        "file (they can share the same field mappings)."
                    ),
                ))

        return errors
