"""Tests for SoarPayloadSizeRule - detects multi-source SOAR lookups risking 1MB limit."""

import yaml
from pathlib import Path

from workflow_validator.rules.soar_payload_size import SoarPayloadSizeRule, SOAR_DATA_REF_PATTERN
from workflow_validator.models.context import ValidationContext
from workflow_validator.models.errors import ErrorSeverity, ErrorCategory

FIXTURE_DIR = Path(__file__).resolve().parent.parent.parent / "test_workflows"


class TestSoarPayloadSizeRule:
    def setup_method(self):
        self.rule = SoarPayloadSizeRule()
        self.context = ValidationContext(file_path="test.yaml")

    def test_name(self):
        assert self.rule.name == "SOAR Payload Size"

    def test_no_actions(self):
        assert self.rule.validate({}, self.context) == []

    def test_non_create_lookup_file_ignored(self):
        """Actions that aren't CreateLookupFile should never be flagged."""
        workflow = {
            "actions": {
                "PrintData": {
                    "id": "abc",
                    "class": "PrintData",
                    "properties": {"text_data": "hello"},
                }
            }
        }
        assert self.rule.validate(workflow, self.context) == []

    def test_single_soar_source_passes(self):
        """CreateLookupFile referencing only one SOAR action output should pass."""
        workflow = {
            "actions": {
                "CreateAlertLookup": {
                    "id": "123",
                    "class": "CreateLookupFile",
                    "properties": {
                        "lookup_file_content_text": (
                            '${data["ListAlerts.API_Integration.Custom_API.List_Alerts.body.value"]'
                            '.map(a, a.id).join("\\n")}'
                        ),
                    },
                }
            }
        }
        assert self.rule.validate(workflow, self.context) == []

    def test_two_soar_sources_errors(self):
        """CreateLookupFile referencing 2 SOAR action outputs should error."""
        workflow = {
            "actions": {
                "CreateAlertLookup": {
                    "id": "123",
                    "class": "CreateLookupFile",
                    "properties": {
                        "lookup_file_content_text": (
                            '${data["ListAlerts.API_Integration.Custom_API.List_Alerts.body.value"]'
                            '.map(a, a.id).join("\\n") + "\\n" + '
                            'data["ListAlertsPage2.API_Integration.Custom_API.List_Alerts.body.value"]'
                            '.map(a, a.id).join("\\n")}'
                        ),
                    },
                }
            }
        }
        errors = self.rule.validate(workflow, self.context)
        assert len(errors) == 1
        assert errors[0].severity == ErrorSeverity.ERROR
        assert errors[0].category == ErrorCategory.PERFORMANCE
        assert errors[0].code == "SOAR_MULTI_PAGE_LOOKUP_RISK"
        assert "ListAlerts" in errors[0].message
        assert "ListAlertsPage2" in errors[0].message
        assert "$select" in errors[0].message
        assert "error_code 500" in errors[0].message

    def test_query_event_refs_not_flagged(self):
        """CreateLookupFile referencing QueryEvent results (not SOAR) should pass."""
        workflow = {
            "actions": {
                "CreateLookup": {
                    "id": "123",
                    "class": "CreateLookupFile",
                    "properties": {
                        "lookup_file_content_text": (
                            '${data["QueryStep1.results"].map(r, r.field).join("\\n")}'
                        ),
                    },
                }
            }
        }
        assert self.rule.validate(workflow, self.context) == []

    def test_empty_cel_expression_passes(self):
        """CreateLookupFile with empty or missing CEL text should pass."""
        workflow = {
            "actions": {
                "CreateLookup": {
                    "id": "123",
                    "class": "CreateLookupFile",
                    "properties": {
                        "lookup_file_content_text": "",
                    },
                }
            }
        }
        assert self.rule.validate(workflow, self.context) == []

    def test_three_soar_sources_errors_with_count(self):
        """Three distinct SOAR sources should error with correct count."""
        refs = [
            'data["Page1.API_Integration.SomeAPI.body.value"].map(a, a.id).join("\\n")',
            'data["Page2.API_Integration.SomeAPI.body.value"].map(a, a.id).join("\\n")',
            'data["Page3.API_Integration.SomeAPI.body.value"].map(a, a.id).join("\\n")',
        ]
        workflow = {
            "actions": {
                "BigLookup": {
                    "id": "123",
                    "class": "CreateLookupFile",
                    "properties": {
                        "lookup_file_content_text": '${' + ' + "\\n" + '.join(refs) + '}',
                    },
                }
            }
        }
        errors = self.rule.validate(workflow, self.context)
        assert len(errors) == 1
        assert "3 SOAR action outputs" in errors[0].message

    # ── Fixture-based tests ────────────────────────────────────────

    def test_fixture_bad_workflow_errors(self):
        """soar_payload_size_bad.yaml should trigger exactly 1 error."""
        workflow = yaml.safe_load((FIXTURE_DIR / "soar_payload_size_bad.yaml").read_text())
        ctx = ValidationContext(file_path="soar_payload_size_bad.yaml")
        errors = self.rule.validate(workflow, ctx)
        assert len(errors) == 1
        assert errors[0].code == "SOAR_MULTI_PAGE_LOOKUP_RISK"
        assert errors[0].severity == ErrorSeverity.ERROR

    def test_fixture_good_workflow_passes(self):
        """soar_payload_size_good.yaml should trigger no warnings."""
        workflow = yaml.safe_load((FIXTURE_DIR / "soar_payload_size_good.yaml").read_text())
        ctx = ValidationContext(file_path="soar_payload_size_good.yaml")
        errors = self.rule.validate(workflow, ctx)
        assert len(errors) == 0

    def test_fixture_real_incident_errors(self):
        """soar_payload_size_real_incident.yaml should flag both multi-source lookups."""
        workflow = yaml.safe_load(
            (FIXTURE_DIR / "soar_payload_size_real_incident.yaml").read_text()
        )
        ctx = ValidationContext(file_path="soar_payload_size_real_incident.yaml")
        errors = self.rule.validate(workflow, ctx)
        # Both CreateAlertLookupFile and CreateIncidentLookupFile combine 2 pages
        assert len(errors) == 2
        action_keys = sorted(e.location.yaml_path.split(".")[1] for e in errors)
        assert action_keys == ["CreateAlertLookupFile", "CreateIncidentLookupFile"]


class TestSoarDataRefPattern:
    """Unit tests for the regex pattern itself."""

    def test_matches_standard_soar_ref(self):
        text = 'data["ListAlerts.API_Integration.Custom_API.List_Alerts.body.value"]'
        matches = SOAR_DATA_REF_PATTERN.findall(text)
        assert matches == ["ListAlerts"]

    def test_matches_with_escaped_quotes(self):
        text = "data[\"ListAlerts.API_Integration.Custom_Microsoft_Defender_For_Office_365_API''s.MS_Defender_for_Office_365_-_List_Alerts.body.value\"]"
        matches = SOAR_DATA_REF_PATTERN.findall(text)
        assert matches == ["ListAlerts"]

    def test_no_match_for_query_event_ref(self):
        text = 'data["QueryStep.results"]'
        matches = SOAR_DATA_REF_PATTERN.findall(text)
        assert matches == []

    def test_multiple_refs_in_one_string(self):
        text = (
            'data["Page1.API_Integration.SomeAPI.body.value"] + '
            'data["Page2.API_Integration.SomeAPI.body.value"]'
        )
        matches = SOAR_DATA_REF_PATTERN.findall(text)
        assert sorted(matches) == ["Page1", "Page2"]
