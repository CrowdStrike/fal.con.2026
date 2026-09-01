#!/usr/bin/env python3
"""
fetch_all_activities.py — Enumerate every Falcon Fusion SOAR workflow action
(activity) available in the loaded CID, and snapshot them to JSON + a summary.

This is a modernized, FalconPy-based rewrite of the internal
`fetch_all_activities.sh` (from ~OLAGZIEL/fusionai
.claude/skills/create-fusion-workflow/). The original hit an internal-only
endpoint (csworkflowapi-*.dodo.eyrie.cloud) with X-CS-CUSTID/USERNAME/USERUUID
headers and a hardcoded internal CID — not usable with standard OAuth2 API
creds. This version uses the public, documented endpoint that FalconPy's
Workflows service collection cleanly exposes:

    GET /workflows/combined/activities/v1   (FalconPy: Workflows.search_activities)

CREDENTIALS
-----------
Loads creds the same way ~/dev/tools/auth_check.py does: walk up from CWD to
the nearest .env and read FALCON_CLIENT_ID / FALCON_CLIENT_SECRET /
FALCON_BASE_URL. No hardcoded secrets. Environment variables already set in the
shell take precedence over .env values (matching auth_check's setdefault order
is intentional: .env fills only what's missing).

OUTPUT
------
  ./all_activities.json          Pretty-printed JSON array of every activity.
  ./all_activities-summary.md    Total count, counts by execution_route, and a
                                 sample of 10 action names/ids.

Both are written to the CURRENT WORKING DIRECTORY (not the script's dir), so
run it from wherever you want the snapshot to land.

IDEMPOTENT / RE-RUNNABLE
------------------------
Safe to run repeatedly. By default it overwrites the output files with a fresh
pull. Use --skip-existing to no-op when all_activities.json already exists
(mirrors the original script's early-exit behavior).

USAGE
-----
    python3 fetch_all_activities.py                      # full snapshot to CWD
    python3 fetch_all_activities.py --skip-existing      # no-op if output exists
    python3 fetch_all_activities.py --limit 1000         # page size (default 500)
    python3 fetch_all_activities.py --out-dir /tmp       # write somewhere else
    python3 fetch_all_activities.py --stable-only        # portable platform core
    python3 fetch_all_activities.py --stable-only --include-foundry  # + gce/faas

FILTERING TIERS
---------------
  (default)                    Full catalog the CID exposes (thousands of actions,
                               incl. installed plugins and tenant content).
  --stable-only                Portable platform-builtin core (~155-160 actions;
                               155 verified identical across a US-1 and a US-2 CID).
  --stable-only --include-foundry
                               Core plus gce.command (Global Command Engine) and
                               faas (Foundry Functions) — platform capabilities
                               whose actions are tenant-authored, so they vary by CID.

This enumerates the available-action CATALOG, not actions used in existing
workflows. (A CID with 14 workflows still exposes thousands of catalog actions.)
"""
import argparse
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path


def _today():
    """Return today's date as YYYY-MM-DD (local)."""
    from datetime import date
    return date.today().isoformat()


def load_dotenv():
    """Walk up from CWD to the nearest .env; fill missing FALCON_* vars.

    Mirrors ~/dev/tools/auth_check.py exactly. Returns the .env path used, or
    None if none was found (in which case we rely on already-exported vars).
    """
    search_dir = Path.cwd().resolve()
    while True:
        env_file = search_dir / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip().strip("'\""))
            return env_file
        if search_dir == search_dir.parent:
            return None
        search_dir = search_dir.parent


def fetch_all_activities(client, limit, progress=print):
    """Page through ALL activities via offset pagination.

    Uses meta.pagination.total as the authoritative end condition, with a
    short-page fallback. Returns (resources, reported_total).
    """
    resources = []
    offset = 0
    reported_total = None

    while True:
        resp = client.search_activities(offset=offset, limit=limit)
        status = resp["status_code"]
        body = resp.get("body", {}) or {}

        if status != 200:
            errs = body.get("errors") or []
            raise RuntimeError(
                f"API returned HTTP {status} at offset {offset}: {errs}"
            )

        page = body.get("resources") or []
        meta_pag = (body.get("meta") or {}).get("pagination") or {}
        if reported_total is None:
            reported_total = meta_pag.get("total")
            if reported_total is not None:
                progress(f"  API reports {reported_total} total activities.")

        resources.extend(page)
        progress(
            f"  offset={offset:>5}  got {len(page):>4}  "
            f"(accumulated {len(resources)})"
        )

        # Stop conditions: empty page, or we've collected the reported total,
        # or the page was short (fewer than requested -> last page).
        if not page:
            break
        if reported_total is not None and len(resources) >= reported_total:
            break
        if len(page) < limit:
            break

        offset += limit

    return resources, reported_total


def dedupe_by_id(resources, progress=print):
    """Collapse duplicate activity ids (defensive — keeps first seen)."""
    seen = {}
    for r in resources:
        rid = r.get("id")
        key = rid if rid is not None else json.dumps(r, sort_keys=True)
        if key not in seen:
            seen[key] = r
    if len(seen) != len(resources):
        progress(
            f"  Deduped {len(resources)} -> {len(seen)} unique by id."
        )
    return list(seen.values())


# Platform-builtin execution_route prefixes present on every production tenant.
# An activity's category = the substring of execution_route before the first ".".
# Adapted from the crowdtalks assets reference script.
#
# Tiering (see --stable-only / --include-foundry):
#   * STABLE_CATEGORIES = the truly portable core: actions whose IDs are
#     identical across tenants/clouds (verified: 155 shared between a bare lab
#     CID on US-1 and a built-out one on US-2).
#   * FOUNDRY_CATEGORIES (gce, faas) are real PLATFORM capabilities, but the
#     individual actions are TENANT-AUTHORED (your Foundry functions, your
#     promoted GCE commands) so they vary by CID. Excluded from --stable-only;
#     re-added only with --include-foundry.
#
# What --stable-only always removes is tenant-specific content: installed Store
# plugins (plugin.*), non-standard http_request connector configs, custom_storage
# collections, rtr.custom_script, on_demand_workflow, logscale.search_result,
# and test/dummy routes.
STABLE_CATEGORIES = {
    "automated_lead", "break", "case_files", "case_management", "cases",
    "containment", "create_variable", "cspm", "customer", "detection",
    "detects", "device", "email", "entitymirroring", "event_search",
    "file_vantage", "identity_protection", "incidents", "investigatable",
    "ioa", "ioc", "logscale", "netskope", "on_demand_scan", "pages", "policy",
    "privileged_access", "quickscan", "resume_after_error", "rtr", "sandbox",
    "threatgraph", "update_variable", "user_input", "utility", "workflow",
    "xdr_incident", "xdr_incident_ai", "xdr_response_actions",
}
# Platform capabilities whose actions are tenant-authored — opt in with
# --include-foundry. gce = Global Command Engine (promoted RTR-style commands);
# faas = Foundry Functions (custom code registered per-tenant).
FOUNDRY_CATEGORIES = {"gce", "faas"}
# The three standard HTTP Request actions that exist on every tenant (Cloud,
# CrowdStrike, On-Premises). All other http_request entries are tenant connector
# configs and are excluded by --stable-only.
STANDARD_HTTP_IDS = {
    "1ba474f407d9228fc8fa02cdce8ae8ef",  # Cloud HTTP Request
    "ad9b77de3da84531b79740e5b4076571",  # CrowdStrike HTTP Request
    "50b8a7cc77ea4ebb9d0bbe96d8def095",  # On-Premises HTTP Request
}
# Categories that are always dropped even if otherwise allowlisted.
DROP_CATEGORIES = {"test", "dummy", "noop"}
# Activity-name prefixes that mark test fixtures (their routes look stable but the
# action is a placeholder, often with a sequential-hex id like a1b2c3d4...).
# Routes are additionally screened for a "test" token in any segment (see
# filter_stable), which catches utility.test_operations, logscale.meng_test, etc.
TEST_NAME_MARKERS = ("test ", "test_")
# Specific full execution_route values that are tenant-authored content even
# though their CATEGORY (rtr, logscale) is otherwise a stable platform category.
# These must be dropped explicitly because the category-level allowlist is too
# coarse to distinguish e.g. rtr.builtin.run (platform) from rtr.custom_script
# (tenant scripts), or logscale.query_event (platform) from
# logscale.search_result (tenant saved searches).
DROP_ROUTES = {
    "rtr.custom_script",
    "rtr.custom_command",
    "logscale.search_result",
}


def filter_stable(resources, include_foundry=False, progress=print):
    """Keep only platform-builtin actions likely present on every tenant.

    Returns the filtered list. See STABLE_CATEGORIES for the policy. Special
    cases that override the category allowlist:
      * http_request -> only the 3 standard HTTP actions survive.
      * DROP_ROUTES  -> tenant-authored sub-routes of an otherwise-stable
        category (rtr.custom_script, logscale.search_result, ...) are removed.
      * gce / faas   -> excluded unless include_foundry=True.
    """
    allowed = STABLE_CATEGORIES | (FOUNDRY_CATEGORIES if include_foundry else set())
    out = []
    for r in resources:
        rid = r.get("id") or ""
        route = r.get("execution_route") or ""
        name = (r.get("name") or "")
        cat = route.split(".")[0] if route else ""

        if cat in DROP_CATEGORIES:
            continue
        if route in DROP_ROUTES:
            continue
        # Drop platform-side / tenant test fixtures that leak into stable
        # categories (e.g. utility.test_operations, logscale.meng_test,
        # "Test Detection Management"). Their ids are placeholders or personal
        # dev artifacts, not real builtin action ids. Match "test" as a token in
        # any route segment, or as a leading word in the name.
        route_segments = re.split(r"[._-]", route)
        if any(seg == "test" or seg.endswith("test") or seg.startswith("test")
               for seg in route_segments):
            continue
        if name.lower().startswith(TEST_NAME_MARKERS):
            continue
        # Drop malformed ids (real activity ids are exactly 32 hex chars; a
        # composite id is <32hex>~<suffix>).
        root = rid.split("~", 1)[0]
        if len(root) != 32 or not all(c in "0123456789abcdefABCDEF" for c in root):
            continue
        if route == "http_request":
            if rid in STANDARD_HTTP_IDS:
                out.append(r)
            continue
        if cat in allowed:
            out.append(r)

    foundry_note = " +foundry" if include_foundry else ""
    progress(
        f"  --stable-only{foundry_note}: kept {len(out)} of {len(resources)} "
        f"(dropped {len(resources) - len(out)} tenant-specific/test actions)."
    )
    return out


def write_outputs(resources, out_dir, progress=print):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "all_activities.json"
    summary_path = out_dir / "all_activities-summary.md"

    with json_path.open("w") as f:
        json.dump(resources, f, indent=2, sort_keys=False)
        f.write("\n")
    progress(f"  Wrote {json_path} ({json_path.stat().st_size:,} bytes)")

    # Summary
    route_counts = Counter(
        (r.get("execution_route") or "(none)") for r in resources
    )
    sample = resources[:10]

    lines = []
    lines.append("# all_activities — summary")
    lines.append("")
    lines.append(f"- **Total actions:** {len(resources)}")
    lines.append(f"- **Distinct execution_route values:** {len(route_counts)}")
    lines.append("")
    lines.append("## Count by execution_route")
    lines.append("")
    lines.append("| execution_route | count |")
    lines.append("|---|---:|")
    for route, count in route_counts.most_common():
        lines.append(f"| `{route}` | {count} |")
    lines.append("")
    lines.append("## Sample (first 10 actions)")
    lines.append("")
    lines.append("| # | name | id | execution_route |")
    lines.append("|---:|---|---|---|")
    for i, r in enumerate(sample, 1):
        name = (r.get("name") or "").replace("|", "\\|")
        lines.append(
            f"| {i} | {name} | `{r.get('id')}` | `{r.get('execution_route')}` |"
        )
    lines.append("")

    summary_path.write_text("\n".join(lines))
    progress(f"  Wrote {summary_path}")
    return json_path, summary_path, route_counts


# Matches a quoted or bare 32-hex action id following `- id:` in
# known_action_ids.yaml. Tolerant of optional quotes and trailing comments.
_KNOWN_ID_RE = re.compile(
    r'^\s*-\s*id:\s*["\']?([0-9a-fA-F]{32})["\']?', re.MULTILINE
)


def update_known_action_ids(resources, yaml_path, date_str, progress=print):
    """Additively merge stable-only action ids into known_action_ids.yaml.

    The validator (action_structure.py) reads only the `id` field, and matches
    composite ids by their root (`<base>~<suffix>`). So we:
      * parse existing 32-hex ids from the file with a regex (no yaml dep here),
      * skip any candidate already present (by exact id OR composite root),
      * append the genuinely-new ids in a dated, clearly-marked block at the end
        so a human can review them in the MR.

    The function is APPEND-ONLY: it never reorders, rewrites, or drops the
    hand-curated entries above. Returns the count of newly-added ids.
    """
    yaml_path = Path(yaml_path)
    if not yaml_path.is_file():
        progress(f"  ERROR: {yaml_path} not found; cannot update.")
        return None

    text = yaml_path.read_text()
    existing = set(_KNOWN_ID_RE.findall(text))
    existing_lower = {i.lower() for i in existing}
    progress(f"  known_action_ids.yaml currently lists {len(existing)} ids.")

    # Candidate ids = stable-only core, normalised to their composite root.
    new_entries = {}  # root_id -> human name (first seen)
    for r in resources:
        rid = (r.get("id") or "").strip()
        if not rid:
            continue
        root = rid.split("~", 1)[0]
        if len(root) != 32:
            continue
        if root.lower() in existing_lower or root in new_entries:
            continue
        new_entries[root] = r.get("name") or ""

    if not new_entries:
        progress("  No new built-in ids to add; known_action_ids.yaml is current.")
        return 0

    block = [
        "",
        f"  # --- Auto-discovered {date_str} via fetch_all_activities.py "
        "--stable-only ---",
        "  # Cross-CID-stable platform actions not previously listed. Review names "
        "before merge.",
    ]
    for root, name in sorted(new_entries.items(), key=lambda kv: (kv[1].lower(), kv[0])):
        comment = f"  # {name}" if name else ""
        block.append(f'  - id: "{root}"{comment}')
    block.append("")

    new_text = text.rstrip("\n") + "\n" + "\n".join(block) + "\n"
    yaml_path.write_text(new_text)
    progress(
        f"  Added {len(new_entries)} new id(s) to {yaml_path} "
        f"(appended, dated {date_str})."
    )
    return len(new_entries)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Snapshot all Falcon Fusion SOAR activities from the "
        "loaded CID to JSON + summary."
    )
    parser.add_argument(
        "--limit", type=int, default=500,
        help="Page size for pagination (default: 500).",
    )
    parser.add_argument(
        "--out-dir", default=".",
        help="Directory for output files (default: current directory).",
    )
    parser.add_argument(
        "--skip-existing", action="store_true",
        help="No-op if all_activities.json already exists in --out-dir.",
    )
    parser.add_argument(
        "--stable-only", action="store_true",
        help="Keep only the portable platform-builtin core present on every "
        "tenant (drops installed plugins, tenant http_request connector "
        "configs, custom_storage, rtr.custom_script, on_demand_workflow, "
        "logscale.search_result, gce.command, faas, and test routes). "
        "~155-160 actions; 155 verified identical across CIDs.",
    )
    parser.add_argument(
        "--include-foundry", action="store_true",
        help="With --stable-only, also include gce.command (Global Command "
        "Engine) and faas (Foundry Functions). These are platform capabilities "
        "but the actions are tenant-authored, so the set varies by CID.",
    )
    parser.add_argument(
        "--update-known-ids", metavar="PATH",
        help="Additively merge the stable-only platform-builtin ids into the "
        "given known_action_ids.yaml (e.g. the fusion-workflow-validator's "
        "src/workflow_validator/known_action_ids.yaml). Append-only: existing "
        "curated entries are preserved; new ids are added in a dated block for "
        "review. Implies --stable-only.",
    )
    parser.add_argument(
        "--date", metavar="YYYY-MM-DD",
        help="Date label for the --update-known-ids block (default: today).",
    )
    args = parser.parse_args(argv)

    out_json = Path(args.out_dir) / "all_activities.json"
    if args.skip_existing and out_json.exists():
        print(f"{out_json} already exists and --skip-existing set. Nothing to do.")
        return 0

    env_file = load_dotenv()
    if env_file:
        print(f"Loaded .env from {env_file}")
    else:
        print("No .env found walking up from CWD; relying on exported env vars.")

    required = ["FALCON_CLIENT_ID", "FALCON_CLIENT_SECRET"]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        print(f"ERROR: missing required env vars: {missing}", file=sys.stderr)
        return 2

    base_url = os.environ.get("FALCON_BASE_URL", "https://api.crowdstrike.com")
    print(f"FALCON_BASE_URL={base_url}")
    print(f"FALCON_CLIENT_ID={os.environ['FALCON_CLIENT_ID'][:8]}...")

    try:
        from falconpy import Workflows
    except ImportError:
        print("ERROR: falconpy not installed (pip install crowdstrike-falconpy)",
              file=sys.stderr)
        return 2

    client = Workflows(
        client_id=os.environ["FALCON_CLIENT_ID"],
        client_secret=os.environ["FALCON_CLIENT_SECRET"],
        base_url=base_url,
    )

    print("Fetching activities (paginated)...")
    try:
        resources, reported_total = fetch_all_activities(client, args.limit)
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    resources = dedupe_by_id(resources)

    if reported_total is not None and len(resources) != reported_total:
        print(
            f"  NOTE: collected {len(resources)} unique vs API-reported "
            f"{reported_total} (duplicates across pages or live drift)."
        )

    if args.stable_only or args.update_known_ids:
        resources = filter_stable(resources, include_foundry=args.include_foundry)
    elif args.include_foundry:
        print("  NOTE: --include-foundry has no effect without --stable-only; "
              "full snapshot already includes gce/faas.")

    print("Writing outputs...")
    json_path, summary_path, route_counts = write_outputs(resources, args.out_dir)

    added = 0
    update_failed = False
    if args.update_known_ids:
        date_str = args.date or _today()
        print(f"Updating {args.update_known_ids} ...")
        added = update_known_action_ids(resources, args.update_known_ids, date_str)
        if added is None:
            # Target YAML did not exist — the snapshot still wrote out, but the
            # requested merge could not happen. Report it as a failure.
            update_failed = True
            added = 0

    print()
    print(f"DONE. {len(resources)} unique actions.")
    print(f"  JSON:    {json_path}")
    print(f"  Summary: {summary_path}")
    if args.update_known_ids:
        if update_failed:
            print(f"  known_action_ids.yaml: NOT updated ({args.update_known_ids} not found)")
        else:
            print(f"  known_action_ids.yaml: +{added} new id(s)")
    print("  By execution_route:")
    for route, count in route_counts.most_common():
        print(f"    {route}: {count}")

    return 1 if update_failed else 0


if __name__ == "__main__":
    sys.exit(main())
