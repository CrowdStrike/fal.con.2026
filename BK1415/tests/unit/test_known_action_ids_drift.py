"""Offline drift check: known_action_ids.yaml vs the committed activity snapshot.

scripts/fetch_all_activities.py --update-known-ids refreshes
known_action_ids.yaml from a live CID. Between refreshes the file can silently
fall behind the platform. We cannot call the live API in CI, but we CAN compare
the curated list against the last committed `--stable-only` snapshot fixture:
every stable platform id in that snapshot SHOULD already be in the allow-list.

A failure here means either:
  * the snapshot was refreshed but known_action_ids.yaml was not (run the
    --update-known-ids step), or
  * an id was manually removed from the allow-list that the snapshot still has.

No network/API access — reads a committed fixture and runs the script's own
filter so the definition of "stable" stays in lock-step with the tool.
"""

import importlib.util
import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "fetch_all_activities.py"
FIXTURE = REPO / "tests" / "fixtures" / "sample-all_activities-stable.json"
YAML_PATH = REPO / "src" / "workflow_validator" / "known_action_ids.yaml"

_ID_RE = re.compile(r'^\s*-\s*id:\s*["\']?([0-9a-fA-F]{32})["\']?', re.MULTILINE)


def _load_filter_stable():
    """Import filter_stable from the standalone maintainer script."""
    spec = importlib.util.spec_from_file_location("fetch_all_activities", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.filter_stable


def _yaml_ids():
    return set(_ID_RE.findall(YAML_PATH.read_text()))


class TestKnownActionIdsDrift:
    def test_fixture_exists(self):
        assert FIXTURE.is_file(), (
            f"missing snapshot fixture {FIXTURE} — regenerate with "
            "scripts/fetch_all_activities.py --stable-only"
        )

    def test_script_importable(self):
        assert callable(_load_filter_stable())

    def test_allowlist_not_behind_snapshot(self):
        """Every stable id in the committed snapshot must be in the allow-list.

        Compares on composite roots (the rule matches `<base>~<suffix>` by root).
        """
        filter_stable = _load_filter_stable()
        snapshot = json.loads(FIXTURE.read_text())
        stable = filter_stable(snapshot, progress=lambda _m: None)

        snapshot_roots = {
            (r.get("id") or "").split("~", 1)[0]
            for r in stable
            if (r.get("id") or "")
        }
        yaml_roots = {i.split("~", 1)[0] for i in _yaml_ids()}

        missing = sorted(snapshot_roots - yaml_roots)
        assert not missing, (
            f"known_action_ids.yaml is behind the snapshot — {len(missing)} "
            f"stable id(s) present in the fixture but missing from the "
            f"allow-list. Run: python3 scripts/fetch_all_activities.py "
            f"--update-known-ids {YAML_PATH}. Missing: {missing[:10]}"
            + (" ..." if len(missing) > 10 else "")
        )

    def test_snapshot_is_actually_stable_filtered(self):
        """Guard: the committed fixture should already be --stable-only output
        (idempotent under the filter), not a raw full catalog."""
        filter_stable = _load_filter_stable()
        snapshot = json.loads(FIXTURE.read_text())
        refiltered = filter_stable(snapshot, progress=lambda _m: None)
        assert len(refiltered) == len(snapshot), (
            "fixture is not stable-only output; regenerate with --stable-only"
        )
