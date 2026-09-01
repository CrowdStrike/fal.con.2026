"""Tests for OrphanedYamlFragmentsRule - detects stray '- ${...}' list items."""

from workflow_validator.rules.orphaned_yaml_fragments import OrphanedYamlFragmentsRule
from workflow_validator.models.context import ValidationContext
from workflow_validator.models.errors import ErrorSeverity


class TestOrphanedYamlFragmentsRule:
    def setup_method(self):
        self.rule = OrphanedYamlFragmentsRule()

    def test_name(self):
        assert self.rule.name == "Orphaned YAML Fragments"

    def test_no_raw_content(self):
        context = ValidationContext(file_path="test.yaml", raw_content="")
        assert self.rule.validate({}, context) == []

    def test_valid_list_under_known_field(self):
        """List items under recognized fields like 'to:' are not orphaned."""
        raw = (
            "actions:\n"
            "  SendEmail:\n"
            "    properties:\n"
            "      to:\n"
            "        - ${user.email}\n"
        )
        context = ValidationContext(file_path="test.yaml", raw_content=raw)
        errors = self.rule.validate({}, context)
        assert len(errors) == 0

    def test_orphaned_fragment_warns(self):
        """A '- ${...}' not under a recognized list field should warn."""
        raw = (
            "actions:\n"
            "  Step1:\n"
            "    some_unknown_field:\n"
            "      - ${leftover.variable}\n"
        )
        context = ValidationContext(file_path="test.yaml", raw_content=raw)
        errors = self.rule.validate({}, context)
        assert len(errors) == 1
        assert errors[0].severity == ErrorSeverity.WARNING
        assert errors[0].code == "ORPHANED_YAML_FRAGMENT"

    def test_list_under_fields_is_valid(self):
        raw = (
            "actions:\n"
            "  Step1:\n"
            "    properties:\n"
            "      fields:\n"
            "        - ${detection.id}\n"
        )
        context = ValidationContext(file_path="test.yaml", raw_content=raw)
        assert self.rule.validate({}, context) == []

    def test_list_under_detections_is_valid(self):
        raw = (
            "actions:\n"
            "  Step1:\n"
            "    properties:\n"
            "      detections:\n"
            "        - ${det.value}\n"
        )
        context = ValidationContext(file_path="test.yaml", raw_content=raw)
        assert self.rule.validate({}, context) == []

    def test_nearby_known_field_context_forgives(self):
        """If a recognized list field is in nearby context, benefit of the doubt."""
        raw = (
            "actions:\n"
            "  Step1:\n"
            "    properties:\n"
            "      email_addresses:\n"
            "        - someone@example.com\n"
            "        - ${user.email}\n"
        )
        context = ValidationContext(file_path="test.yaml", raw_content=raw)
        assert self.rule.validate({}, context) == []
