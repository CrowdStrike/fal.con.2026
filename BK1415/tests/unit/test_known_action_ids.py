"""Integrity tests for known_action_ids.yaml — the built-in action allow-list.

These guard against a broken or garbled refresh (see
scripts/fetch_all_activities.py --update-known-ids) landing in the file the
ActionStructureRule depends on. No network or API access required.
"""

import re
from pathlib import Path

import pytest
import yaml

YAML_PATH = (
    Path(__file__).resolve().parents[2]
    / "src" / "workflow_validator" / "known_action_ids.yaml"
)

# A real activity id is exactly 32 hex chars; composite ids are <32hex>~<suffix>.
_ID_RE = re.compile(r"^[0-9a-fA-F]{32}(~.+)?$")

# Curated builtins that must always be recognised — if a refresh ever drops
# these, MISSING_ACTION_CLASS would start firing on core platform actions.
_REQUIRED_IDS = {
    "aadbf530e35fc452a032f5f8acaaac2a": "Print data",
    "07413ef9ba7c47bf5a242799f59902cc": "Send email",
    "702d15788dbbffdf0b68d8e2f3599aa4": "Create variable",
    "4918bf9d85ecc06388eca16543bdbbdc": "Create a new Case",
    "1ba474f407d9228fc8fa02cdce8ae8ef": "Cloud HTTP Request",
}


def _load_raw():
    return yaml.safe_load(YAML_PATH.read_text()) or {}


def _ids_from_file():
    """All ids in the order they appear (list, so duplicates are visible)."""
    data = _load_raw()
    ids = []
    for entry in (data.get("builtin_action_ids") or []):
        if isinstance(entry, dict) and entry.get("id"):
            ids.append(str(entry["id"]).strip())
        elif isinstance(entry, str):
            ids.append(entry.strip())
    return ids


class TestKnownActionIdsIntegrity:
    def test_file_exists(self):
        assert YAML_PATH.is_file(), f"missing {YAML_PATH}"

    def test_parses_as_yaml_with_expected_key(self):
        data = _load_raw()
        assert isinstance(data, dict)
        assert "builtin_action_ids" in data
        assert isinstance(data["builtin_action_ids"], list)

    def test_not_empty(self):
        assert len(_ids_from_file()) > 0

    def test_all_ids_well_formed(self):
        bad = [i for i in _ids_from_file() if not _ID_RE.match(i)]
        assert not bad, f"malformed ids (expect 32-hex or 32hex~suffix): {bad}"

    def test_no_duplicate_ids(self):
        ids = _ids_from_file()
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        assert not dupes, f"duplicate ids: {dupes}"

    @pytest.mark.parametrize("action_id,name", sorted(_REQUIRED_IDS.items()))
    def test_required_builtins_present(self, action_id, name):
        assert action_id in _ids_from_file(), f"missing curated builtin: {name} ({action_id})"

    def test_loads_via_rule_loader(self):
        """The actual consumer must read a non-empty set from this file."""
        from workflow_validator.rules.action_structure import _load_builtin_action_ids
        ids = _load_builtin_action_ids()
        assert len(ids) >= len(_REQUIRED_IDS)
        assert _REQUIRED_IDS.keys() <= ids
