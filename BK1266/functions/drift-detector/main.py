"""
Drift Detector - Compare snapshots and detect configuration drift
"""
import json
from datetime import datetime
import uuid
from falconpy import CustomStorage
from crowdstrike.foundry.function import Function, Request, Response, APIError
from logging import Logger
from typing import Dict, List, Optional, Any

func = Function.instance()

SNAPSHOTS_COLLECTION = "policy_snapshots"
DRIFT_COLLECTION = "drift_events"


def _get_snapshot(snapshot_id: str, logger: Logger) -> Optional[Dict]:
    """Fetch a single snapshot from Custom Storage by ID.

    Args:
        snapshot_id: UUID of the snapshot to fetch.
        logger: Logger instance.

    Returns:
        Snapshot dict or None if not found.
    """
    storage = CustomStorage()
    raw = storage.GetObject(
        collection_name=SNAPSHOTS_COLLECTION,
        object_key=snapshot_id,
    )
    if isinstance(raw, bytes):
        try:
            return json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            logger.error(f"Failed to parse snapshot {snapshot_id}: {exc}")
            return None
    logger.error(f"GetObject failed for snapshot {snapshot_id}: {raw}")
    return None


def _store_drift_events(events: List[Dict], logger: Logger) -> None:
    """Persist drift events to Custom Storage. Each event stored by event_id.

    Args:
        events: List of drift event dicts.
        logger: Logger instance.
    """
    storage = CustomStorage()
    for event in events:
        response = storage.PutObject(
            body=event,  # Pass dict directly — FalconPy serialises to JSON
            collection_name=DRIFT_COLLECTION,
            object_key=event["event_id"],
        )
        if response.get("status_code") not in (200, 201):
            logger.error(f"Failed to store drift event {event['event_id']}: {response}")


def _flatten_prevention_settings(prevention_settings) -> Dict:
    """Flatten a prevention_settings list-of-categories into {setting_id: value}.

    Args:
        prevention_settings: List of category dicts from Falcon API or snapshot.

    Returns:
        Flat dict mapping setting ID to its value.
    """
    flat: Dict = {}
    if not isinstance(prevention_settings, list):
        return flat
    for category in prevention_settings:
        if not isinstance(category, dict):
            continue
        for setting in category.get("settings", []):
            if not isinstance(setting, dict):
                continue
            setting_id = setting.get("id")
            if not setting_id:
                continue
            setting_type = setting.get("type")
            value_obj = setting.get("value", {})
            if setting_type == "toggle":
                flat[setting_id] = value_obj.get("enabled")
            else:
                flat[setting_id] = value_obj
    return flat


def compare_prevention_settings(baseline_settings, current_settings) -> List[Dict]:
    """Compare two prevention_settings structures and return changed settings.

    Supports both the Falcon API list-of-categories format and flat dicts.

    Args:
        baseline_settings: prevention_settings from the baseline snapshot.
        current_settings: prevention_settings from the current snapshot.

    Returns:
        List of dicts describing each changed setting.
    """
    baseline_flat = _flatten_prevention_settings(baseline_settings)
    current_flat = _flatten_prevention_settings(current_settings)

    changes = []
    all_ids = set(list(baseline_flat.keys()) + list(current_flat.keys()))

    for setting_id in all_ids:
        baseline_val = baseline_flat.get(setting_id)
        current_val = current_flat.get(setting_id)

        if baseline_val != current_val:
            if baseline_val is None:
                change_type = "added"
            elif current_val is None:
                change_type = "removed"
            else:
                change_type = "modified"

            changes.append({
                "setting_id": setting_id,
                "old_value": baseline_val,
                "new_value": current_val,
                "change_type": change_type,
            })

    return changes


def calculate_risk_score(drift_type: str, policy_type: str, changes: Dict) -> tuple[str, float]:
    """Calculate risk level and score for detected drift."""
    base_score = 0

    # Base scores by drift type
    if drift_type == "removed":
        base_score = 80
    elif drift_type == "disabled":
        base_score = 70
    elif drift_type == "modified":
        base_score = 50
    elif drift_type == "enabled":
        base_score = 20
    elif drift_type == "added":
        base_score = 10

    # Increase score for prevention policies (most critical)
    if policy_type == "prevention":
        base_score *= 1.2
    elif policy_type == "firewall":
        base_score *= 1.1

    # Cap at 100
    base_score = min(base_score, 100)

    # Determine risk level
    if base_score >= 80:
        risk_level = "CRITICAL"
    elif base_score >= 60:
        risk_level = "HIGH"
    elif base_score >= 40:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    return risk_level, base_score


def compare_policies(baseline_policies: List[Dict], current_policies: List[Dict],
                     policy_type: str, logger: Logger) -> List[Dict]:
    """Compare two sets of policies and detect differences."""
    drift_events = []

    # Create lookup dictionaries
    baseline_map = {p.get("id"): p for p in baseline_policies}
    current_map = {p.get("id"): p for p in current_policies}

    baseline_ids = set(baseline_map.keys())
    current_ids = set(current_map.keys())

    # Detect removed policies
    removed_ids = baseline_ids - current_ids
    for policy_id in removed_ids:
        policy = baseline_map[policy_id]
        risk_level, risk_score = calculate_risk_score("removed", policy_type, {})

        drift_events.append({
            "event_id": str(uuid.uuid4()),
            "detected_at": datetime.utcnow().isoformat() + "Z",
            "policy_type": policy_type,
            "policy_id": policy_id,
            "policy_name": policy.get("name", "Unknown"),
            "drift_type": "removed",
            "risk_level": risk_level,
            "risk_score": risk_score,
            "changes": {"action": "Policy removed from configuration"},
            "status": "open",
            "remediation_available": True,
            "remediation_action": f"Re-add {policy.get('name')} policy"
        })

    # Detect added policies
    added_ids = current_ids - baseline_ids
    for policy_id in added_ids:
        policy = current_map[policy_id]
        risk_level, risk_score = calculate_risk_score("added", policy_type, {})

        drift_events.append({
            "event_id": str(uuid.uuid4()),
            "detected_at": datetime.utcnow().isoformat() + "Z",
            "policy_type": policy_type,
            "policy_id": policy_id,
            "policy_name": policy.get("name", "Unknown"),
            "drift_type": "added",
            "risk_level": risk_level,
            "risk_score": risk_score,
            "changes": {"action": "New policy added"},
            "status": "open",
            "remediation_available": False,
            "remediation_action": "Review if this policy should be in baseline"
        })

    # Detect modifications in common policies
    common_ids = baseline_ids & current_ids
    for policy_id in common_ids:
        baseline_policy = baseline_map[policy_id]
        current_policy = current_map[policy_id]

        changes = {}

        # Check enabled status
        baseline_enabled = baseline_policy.get("enabled", False)
        current_enabled = current_policy.get("enabled", False)

        if baseline_enabled != current_enabled:
            changes["enabled"] = {
                "old_value": baseline_enabled,
                "new_value": current_enabled
            }

            drift_type = "enabled" if current_enabled else "disabled"
            risk_level, risk_score = calculate_risk_score(drift_type, policy_type, changes)

            drift_events.append({
                "event_id": str(uuid.uuid4()),
                "detected_at": datetime.utcnow().isoformat() + "Z",
                "policy_type": policy_type,
                "policy_id": policy_id,
                "policy_name": current_policy.get("name", "Unknown"),
                "drift_type": drift_type,
                "risk_level": risk_level,
                "risk_score": risk_score,
                "changes": changes,
                "status": "open",
                "remediation_available": True,
                "remediation_action": f"{'Enable' if baseline_enabled else 'Disable'} {current_policy.get('name')}"
            })

        # Check prevention settings (if applicable)
        if policy_type == "prevention":
            baseline_settings = baseline_policy.get("prevention_settings", {})
            current_settings = current_policy.get("prevention_settings", {})

            if baseline_settings != current_settings:
                # Detailed settings comparison
                detailed_changes = compare_prevention_settings(baseline_settings, current_settings)

                if detailed_changes:
                    changes["prevention_settings"] = detailed_changes

                    risk_level, risk_score = calculate_risk_score("modified", policy_type, changes)

                    drift_events.append({
                        "event_id": str(uuid.uuid4()),
                        "detected_at": datetime.utcnow().isoformat() + "Z",
                        "policy_type": policy_type,
                        "policy_id": policy_id,
                        "policy_name": current_policy.get("name", "Unknown"),
                        "drift_type": "modified",
                        "risk_level": risk_level,
                        "risk_score": risk_score,
                        "changes": changes,
                        "detailed_changes_count": len(detailed_changes),
                        "status": "open",
                        "remediation_available": True,
                        "remediation_action": f"Review {len(detailed_changes)} changed settings in {current_policy.get('name')}"
                    })

    return drift_events


@func.handler(method='POST', path='/api/drift/detect')
def detect_drift(request: Request, _config: Optional[Dict], logger: Logger) -> Response:
    """
    Detect drift between baseline and current snapshot.

    Request body:
    {
        "baseline_snapshot_id": "uuid",
        "current_snapshot_id": "uuid" (optional - will create new if not provided)
    }
    """
    try:
        # Validate request
        baseline_snapshot_id = request.body.get("baseline_snapshot_id")
        if not baseline_snapshot_id:
            return Response(
                code=400,
                errors=[APIError(code=400, message="baseline_snapshot_id required")]
            )

        current_snapshot_id = request.body.get("current_snapshot_id")

        logger.info(f"Detecting drift from baseline: {baseline_snapshot_id}")

        # Fetch baseline snapshot
        baseline_snapshot = _get_snapshot(baseline_snapshot_id, logger)
        if not baseline_snapshot:
            return Response(
                code=404,
                errors=[APIError(code=404, message="Baseline snapshot not found")]
            )

        # Fetch current snapshot
        if not current_snapshot_id:
            return Response(
                code=400,
                errors=[APIError(code=400, message="current_snapshot_id required")]
            )

        current_snapshot = _get_snapshot(current_snapshot_id, logger)
        if not current_snapshot:
            return Response(
                code=404,
                errors=[APIError(code=404, message="Current snapshot not found")]
            )

        logger.info("Comparing snapshots...")

        # Compare all policy types
        all_drift_events = []

        # Prevention policies
        prevention_drift = compare_policies(
            baseline_snapshot.get("prevention_policies", []),
            current_snapshot.get("prevention_policies", []),
            "prevention",
            logger
        )
        all_drift_events.extend(prevention_drift)

        # Response policies
        response_drift = compare_policies(
            baseline_snapshot.get("response_policies", []),
            current_snapshot.get("response_policies", []),
            "response",
            logger
        )
        all_drift_events.extend(response_drift)

        # Firewall policies
        firewall_drift = compare_policies(
            baseline_snapshot.get("firewall_policies", []),
            current_snapshot.get("firewall_policies", []),
            "firewall",
            logger
        )
        all_drift_events.extend(firewall_drift)

        logger.info(f"Detected {len(all_drift_events)} drift events")

        # Store drift events
        if all_drift_events:
            for event in all_drift_events:
                event["baseline_snapshot_id"] = baseline_snapshot_id
                event["current_snapshot_id"] = current_snapshot_id
            _store_drift_events(all_drift_events, logger)

        # Calculate summary statistics
        critical_count = sum(1 for e in all_drift_events if e["risk_level"] == "CRITICAL")
        high_count = sum(1 for e in all_drift_events if e["risk_level"] == "HIGH")
        medium_count = sum(1 for e in all_drift_events if e["risk_level"] == "MEDIUM")
        low_count = sum(1 for e in all_drift_events if e["risk_level"] == "LOW")

        return Response(
            body={
                "drift_detected": len(all_drift_events) > 0,
                "total_drift_events": len(all_drift_events),
                "summary": {
                    "critical": critical_count,
                    "high": high_count,
                    "medium": medium_count,
                    "low": low_count
                },
                "baseline_snapshot_id": baseline_snapshot_id,
                "current_snapshot_id": current_snapshot_id,
                "drift_events": all_drift_events,
                "message": f"Drift detection complete. Found {len(all_drift_events)} changes."
            },
            code=200
        )

    except Exception as e:
        logger.error(f"Error detecting drift: {str(e)}")
        return Response(
            code=500,
            errors=[APIError(code=500, message=f"Error detecting drift: {str(e)}")]
        )


@func.handler(method='GET', path='/api/audit/events')
def get_audit_events(request: Request, _config: Optional[Dict], logger: Logger) -> Response:
    """Return audit events for policy changes.

    Note: The FalconPy Audit service is not available in the current runtime.
    Returns an empty list so the caller degrades gracefully.
    """
    logger.warning("Audit service not available in current FalconPy runtime version")
    return Response(
        body={
            "audit_events": [],
            "count": 0,
            "message": "Audit log not available in this environment",
        },
        code=200,
    )


if __name__ == '__main__':
    func.run()
