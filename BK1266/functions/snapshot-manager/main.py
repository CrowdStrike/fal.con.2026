"""
Snapshot Manager - Create and manage policy snapshots for drift detection.
"""
import json
from datetime import datetime
import uuid
from falconpy import PreventionPolicies, ResponsePolicies, FirewallManagement, CustomStorage
from crowdstrike.foundry.function import Function, Request, Response, APIError
from logging import Logger
from typing import Dict, List, Optional

func = Function.instance()

COLLECTION_NAME = "policy_snapshots"


def _storage() -> CustomStorage:
    """Return an authenticated CustomStorage client.

    Returns:
        CustomStorage instance (uses Foundry context auth).
    """
    return CustomStorage()


def _slim_policy(policy: Dict) -> Dict:
    """Strip a policy down to only the fields needed for drift detection.

    Args:
        policy: Full policy object from Falcon API.

    Returns:
        Lightweight dict with id, name, platform, enabled, and prevention_settings.
    """
    return {
        "id": policy.get("id"),
        "name": policy.get("name"),
        "platform_name": policy.get("platform_name"),
        "enabled": policy.get("enabled"),
        "modified_timestamp": policy.get("modified_timestamp"),
        "prevention_settings": policy.get("prevention_settings", []),
    }


def _put_snapshot(snapshot: Dict, logger: Logger) -> str:
    """Persist a snapshot document to Custom Storage.

    Args:
        snapshot: Snapshot dict to store.
        logger: Logger instance.

    Returns:
        Empty string on success, error message on failure.
    """
    payload = json.dumps(snapshot)
    size_kb = len(payload) / 1024
    logger.info(f"Storing snapshot {snapshot['snapshot_id']} ({size_kb:.1f} KB)")

    storage = _storage()
    response = storage.PutObject(
        body=snapshot,  # Pass dict directly — FalconPy serialises to JSON
        collection_name=COLLECTION_NAME,
        object_key=snapshot["snapshot_id"],
    )
    status = response.get("status_code") if isinstance(response, dict) else None
    if status not in (200, 201):
        err = response.get("body", response) if isinstance(response, dict) else response
        logger.error(f"PutObject failed (status={status}): {err}")
        return f"PutObject returned status {status}: {err}"
    return ""


def _list_snapshot_keys(limit: int, logger: Logger) -> List[str]:
    """Return object keys from Custom Storage for the snapshots collection.

    Args:
        limit: Max number of keys to return.
        logger: Logger instance.

    Returns:
        List of object key strings.
    """
    storage = _storage()
    response = storage.ListObjects(
        collection_name=COLLECTION_NAME,
        limit=limit,
    )
    if response.get("status_code") != 200:
        logger.error(f"ListObjects failed: {response}")
        return []
    return response.get("body", {}).get("resources", [])


def _get_snapshot_by_key(key: str, logger: Logger) -> Optional[Dict]:
    """Fetch and deserialise a single snapshot by its object key.

    Args:
        key: Object key (snapshot_id).
        logger: Logger instance.

    Returns:
        Snapshot dict or None if not found / parse error.
    """
    storage = _storage()
    raw = storage.GetObject(
        collection_name=COLLECTION_NAME,
        object_key=key,
    )
    # GetObject returns bytes on success, dict on failure
    if isinstance(raw, bytes):
        try:
            return json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            logger.error(f"Failed to parse snapshot {key}: {exc}")
            return None
    logger.error(f"GetObject failed for key {key}: {raw}")
    return None


def _get_snapshots(keys: List[str], logger: Logger) -> List[Dict]:
    """Fetch multiple snapshots by their keys.

    Args:
        keys: List of object keys.
        logger: Logger instance.

    Returns:
        List of successfully parsed snapshot dicts.
    """
    results = []
    for key in keys:
        snapshot = _get_snapshot_by_key(key, logger)
        if snapshot:
            results.append(snapshot)
    return results


def fetch_all_policies(logger: Logger) -> Dict:
    """Fetch prevention, response, and firewall policies from Falcon.

    Args:
        logger: Logger instance.

    Returns:
        Dict with prevention_policies, response_policies, firewall_policies lists.
    """
    logger.info("Fetching all policies for snapshot...")

    result: Dict[str, List] = {
        "prevention_policies": [],
        "response_policies": [],
        "firewall_policies": [],
    }

    try:
        api = PreventionPolicies()
        r = api.query_policies()
        if r["status_code"] == 200 and r["body"]["resources"]:
            d = api.get_policies(ids=r["body"]["resources"])
            if d["status_code"] == 200:
                result["prevention_policies"] = d["body"]["resources"]
                logger.info(f"Fetched {len(result['prevention_policies'])} prevention policies")
    except Exception as exc:
        logger.error(f"Error fetching prevention policies: {exc}")

    try:
        api = ResponsePolicies()
        r = api.query_policies()
        if r["status_code"] == 200 and r["body"]["resources"]:
            d = api.get_policies(ids=r["body"]["resources"])
            if d["status_code"] == 200:
                result["response_policies"] = d["body"]["resources"]
                logger.info(f"Fetched {len(result['response_policies'])} response policies")
    except Exception as exc:
        logger.error(f"Error fetching response policies: {exc}")

    try:
        api = FirewallManagement()
        r = api.query_policies()
        if r["status_code"] == 200 and r["body"]["resources"]:
            d = api.get_policies(ids=r["body"]["resources"])
            if d["status_code"] == 200:
                result["firewall_policies"] = d["body"]["resources"]
                logger.info(f"Fetched {len(result['firewall_policies'])} firewall policies")
    except Exception as exc:
        logger.error(f"Error fetching firewall policies: {exc}")

    return result


@func.handler(method='POST', path='/api/snapshot/create')
def create_snapshot(request: Request, _config: Optional[Dict], logger: Logger) -> Response:
    """Create a snapshot of all current policies and persist it.

    Args:
        request: Body fields: snapshot_type (str), description (str).
        _config: Unused.
        logger: Logger instance.

    Returns:
        Response with snapshot_id, timestamp, total_policies.
    """
    try:
        snapshot_type = request.body.get("snapshot_type", "manual")
        description = request.body.get("description", "")

        snapshot_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat() + "Z"

        logger.info(f"Creating {snapshot_type} snapshot: {snapshot_id}")

        policies = fetch_all_policies(logger)
        total_policies = (
            len(policies["prevention_policies"])
            + len(policies["response_policies"])
            + len(policies["firewall_policies"])
        )

        # Store only the fields needed for drift detection (keeps payload small)
        snapshot = {
            "snapshot_id": snapshot_id,
            "timestamp": timestamp,
            "snapshot_type": snapshot_type,
            "description": description,
            "prevention_policies": [_slim_policy(p) for p in policies["prevention_policies"]],
            "response_policies": [
                {"id": p.get("id"), "name": p.get("name"), "platform_name": p.get("platform_name"), "enabled": p.get("enabled")}
                for p in policies["response_policies"]
            ],
            "firewall_policies": [
                {"id": p.get("id"), "name": p.get("name"), "platform_name": p.get("platform_name"), "enabled": p.get("enabled")}
                for p in policies["firewall_policies"]
            ],
            "total_policies": total_policies,
            "created_by": request.context.get("user", {}).get("uuid", "system"),
        }

        err = _put_snapshot(snapshot, logger)
        if err:
            return Response(
                code=500,
                errors=[APIError(code=500, message=f"Failed to store snapshot: {err}")],
            )

        logger.info(f"Snapshot {snapshot_id} stored successfully")

        return Response(
            body={
                "snapshot_id": snapshot_id,
                "timestamp": timestamp,
                "total_policies": total_policies,
                "message": f"{snapshot_type.capitalize()} snapshot created successfully",
            },
            code=200,
        )

    except Exception as exc:
        logger.error(f"Error creating snapshot: {exc}")
        return Response(
            code=500,
            errors=[APIError(code=500, message=f"Error creating snapshot: {exc}")],
        )


@func.handler(method='GET', path='/api/snapshot/list')
def list_snapshots(request: Request, _config: Optional[Dict], logger: Logger) -> Response:
    """List stored snapshots.

    Args:
        request: Query params: limit (int, default 50).
        _config: Unused.
        logger: Logger instance.

    Returns:
        Response with snapshots list and count.
    """
    try:
        limit_param = request.params.query.get("limit")
        limit = int(limit_param[0]) if limit_param else 50

        logger.info("Fetching snapshot list...")

        keys = _list_snapshot_keys(limit, logger)
        snapshots = _get_snapshots(keys, logger)

        snapshot_list = [
            {
                "snapshot_id": s.get("snapshot_id"),
                "timestamp": s.get("timestamp"),
                "snapshot_type": s.get("snapshot_type"),
                "total_policies": s.get("total_policies"),
                "description": s.get("description", ""),
            }
            for s in snapshots
        ]

        return Response(body={"snapshots": snapshot_list, "count": len(snapshot_list)}, code=200)

    except Exception as exc:
        logger.error(f"Error listing snapshots: {exc}")
        return Response(
            code=500,
            errors=[APIError(code=500, message=f"Error listing snapshots: {exc}")],
        )


@func.handler(method='GET', path='/api/snapshot/{snapshot_id}')
def get_snapshot(request: Request, _config: Optional[Dict], logger: Logger) -> Response:
    """Retrieve a single snapshot by ID.

    Args:
        request: Path param: snapshot_id.
        _config: Unused.
        logger: Logger instance.

    Returns:
        Full snapshot document or 404.
    """
    try:
        snapshot_id = request.params.path.get("snapshot_id")

        if not snapshot_id:
            return Response(
                code=400,
                errors=[APIError(code=400, message="snapshot_id is required")],
            )

        logger.info(f"Fetching snapshot: {snapshot_id}")

        snapshot = _get_snapshot_by_key(snapshot_id, logger)
        if not snapshot:
            return Response(
                code=404,
                errors=[APIError(code=404, message="Snapshot not found")],
            )

        return Response(body=snapshot, code=200)

    except Exception as exc:
        logger.error(f"Error getting snapshot: {exc}")
        return Response(
            code=500,
            errors=[APIError(code=500, message=f"Error getting snapshot: {exc}")],
        )


if __name__ == '__main__':
    func.run()
