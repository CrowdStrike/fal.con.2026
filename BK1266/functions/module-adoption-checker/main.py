"""
Module Adoption Checker.

Simple, consistent adoption check for each Falcon module:
a module is considered "In Use" when it has at least one enabled policy.
"""
from datetime import datetime
from falconpy import (
    PreventionPolicies,
    ResponsePolicies,
    FirewallPolicies,
    DeviceControlPolicies,
    SpotlightVulnerabilities,
    Hosts,
)
from crowdstrike.foundry.function import Function, Request, Response, APIError
from logging import Logger
from typing import Dict, List, Optional, Tuple

func = Function.instance()


def _policy_status(total: int, enabled: int) -> Tuple[str, int, List[Dict]]:
    """Return adoption_level, adoption_score and features for a policy-based module.

    Args:
        total: Total number of policies found.
        enabled: Number of enabled policies.

    Returns:
        Tuple of (adoption_level, adoption_score, features).
    """
    in_use = enabled > 0

    if not in_use:
        level = "Not in Use"
        score = 0
    elif enabled == total:
        level = "Active"
        score = 100
    else:
        level = "Partial"
        score = round((enabled / total) * 100)

    features = [
        {
            "feature_name": "Policies Created",
            "enabled": total > 0,
            "detail": f"{total} {'policy' if total == 1 else 'policies'} found",
        },
        {
            "feature_name": "Policies Enabled",
            "enabled": in_use,
            "detail": f"{enabled} of {total} enabled",
        },
    ]

    recommendation = (
        "Enable at least one policy to start using this module."
        if not in_use
        else f"All {total} policies enabled — good coverage!"
        if enabled == total
        else f"{total - enabled} {'policy' if (total - enabled) == 1 else 'policies'} still disabled."
    )

    return level, score, features, recommendation


def _query_combined(api, logger: Logger, label: str) -> Optional[List[Dict]]:
    """Call query_combined_policies and return resources, or None on failure.

    Args:
        api: FalconPy service object with query_combined_policies method.
        logger: Logger instance.
        label: Human-readable module name for log messages.

    Returns:
        List of policy dicts, or None if the call failed.
    """
    try:
        response = api.query_combined_policies(limit=100)
        if response["status_code"] != 200:
            logger.warning(f"{label}: query_combined_policies returned {response['status_code']}")
            return None
        return response.get("body", {}).get("resources", [])
    except Exception as exc:
        logger.error(f"{label}: {exc}")
        return None


def check_prevent(logger: Logger) -> Optional[Dict]:
    """Check Falcon Prevent adoption via prevention policies.

    Args:
        logger: Logger instance.

    Returns:
        Adoption dict or None if the API call failed.
    """
    policies = _query_combined(PreventionPolicies(), logger, "Falcon Prevent")
    if policies is None:
        return None

    total = len(policies)
    enabled = sum(1 for p in policies if p.get("enabled", False))
    level, score, features, recommendation = _policy_status(total, enabled)

    return {
        "adoption_level": level,
        "adoption_score": score,
        "features": features,
        "top_recommendation": recommendation,
    }


def check_insight(logger: Logger) -> Optional[Dict]:
    """Check Falcon Insight EDR adoption via response policies.

    Args:
        logger: Logger instance.

    Returns:
        Adoption dict or None if the API call failed.
    """
    policies = _query_combined(ResponsePolicies(), logger, "Falcon Insight EDR")
    if policies is None:
        return None

    total = len(policies)
    enabled = sum(1 for p in policies if p.get("enabled", False))
    level, score, features, recommendation = _policy_status(total, enabled)

    return {
        "adoption_level": level,
        "adoption_score": score,
        "features": features,
        "top_recommendation": recommendation,
    }


def check_firewall(logger: Logger) -> Optional[Dict]:
    """Check Falcon Firewall Management adoption via firewall policies.

    Args:
        logger: Logger instance.

    Returns:
        Adoption dict or None if the API call failed.
    """
    policies = _query_combined(FirewallPolicies(), logger, "Falcon Firewall Management")
    if policies is None:
        return None

    total = len(policies)
    enabled = sum(1 for p in policies if p.get("enabled", False))
    level, score, features, recommendation = _policy_status(total, enabled)

    return {
        "adoption_level": level,
        "adoption_score": score,
        "features": features,
        "top_recommendation": recommendation,
    }


def check_device_control(logger: Logger) -> Optional[Dict]:
    """Check Falcon Device Control adoption via device control policies.

    Args:
        logger: Logger instance.

    Returns:
        Adoption dict or None if the API call failed.
    """
    try:
        api = DeviceControlPolicies()
        policies = _query_combined(api, logger, "Falcon Device Control")
        if policies is None:
            return None

        total = len(policies)
        enabled = sum(1 for p in policies if p.get("enabled", False))
        level, score, features, recommendation = _policy_status(total, enabled)

        return {
            "adoption_level": level,
            "adoption_score": score,
            "features": features,
            "top_recommendation": recommendation,
        }
    except Exception as exc:
        logger.error(f"Device Control: {exc}")
        return None


def check_spotlight(logger: Logger) -> Optional[Dict]:
    """Check Falcon Spotlight VM adoption by querying vulnerability findings.

    Args:
        logger: Logger instance.

    Returns:
        Adoption dict or None if the API call failed.
    """
    try:
        api = SpotlightVulnerabilities()
        response = api.query_vulnerabilities(limit=1, filter="status:'open'")

        if response.get("status_code") not in (200, 201):
            logger.warning(f"Spotlight: query returned {response.get('status_code')}")
            return None

        total = response.get("body", {}).get("meta", {}).get("pagination", {}).get("total", 0)
        in_use = total > 0

        return {
            "adoption_level": "Active" if in_use else "Not in Use",
            "adoption_score": 100 if in_use else 0,
            "features": [
                {
                    "feature_name": "Vulnerability Scanning",
                    "enabled": in_use,
                    "detail": f"{total} open findings" if in_use else "No findings — scanning may not be active",
                }
            ],
            "top_recommendation": (
                "Spotlight is actively scanning. Review and remediate open vulnerabilities."
                if in_use
                else "Deploy Spotlight sensors and enable vulnerability scanning."
            ),
        }
    except Exception as exc:
        logger.error(f"Spotlight: {exc}")
        return None


def check_identity_protection(logger: Logger) -> Optional[Dict]:
    """Check Falcon Identity Protection adoption via host counts with identity data.

    Uses the Hosts API to check if any sensors are reporting identity telemetry
    (Windows domain-joined sensors are required for identity protection to function).

    Args:
        logger: Logger instance.

    Returns:
        Adoption dict or None if the API call failed.
    """
    try:
        api = Hosts()
        response = api.query_devices_by_filter(
            filter="product_type_desc:'Domain Controller'",
            limit=100,
        )

        if response.get("status_code") != 200:
            logger.warning(f"Identity Protection: host query returned {response.get('status_code')}")
            return None

        dc_count = len(response.get("body", {}).get("resources", []))
        in_use = dc_count > 0

        return {
            "adoption_level": "Active" if in_use else "Not in Use",
            "adoption_score": 100 if in_use else 0,
            "features": [
                {
                    "feature_name": "Domain Controllers Covered",
                    "enabled": in_use,
                    "detail": f"{dc_count} DC{'s' if dc_count != 1 else ''} with sensor installed" if in_use else "No Domain Controllers with sensor found",
                }
            ],
            "top_recommendation": (
                f"Identity protection active on {dc_count} DC(s). Ensure all DCs are covered."
                if in_use
                else "Install Falcon sensor on Domain Controllers to enable Identity Protection."
            ),
        }
    except Exception as exc:
        logger.error(f"Identity Protection: {exc}")
        return None


# Core modules checked via live API
CORE_MODULES = [
    {
        "module_name": "Falcon Prevent",
        "module_key": "prevent",
        "icon": "shield-fill-check",
        "check_fn": check_prevent,
    },
    {
        "module_name": "Falcon Insight EDR",
        "module_key": "insight",
        "icon": "eye-fill",
        "check_fn": check_insight,
    },
    {
        "module_name": "Falcon Firewall Management",
        "module_key": "firewall",
        "icon": "fire",
        "check_fn": check_firewall,
    },
    {
        "module_name": "Falcon Device Control",
        "module_key": "device_control",
        "icon": "usb-symbol",
        "check_fn": check_device_control,
    },
    {
        "module_name": "Spotlight Vulnerability Management",
        "module_key": "spotlight",
        "icon": "bug-fill",
        "check_fn": check_spotlight,
    },
    {
        "module_name": "Falcon Identity Protection",
        "module_key": "identity",
        "icon": "person-badge-fill",
        "check_fn": check_identity_protection,
    },
]


def build_scored_modules(logger: Logger) -> List[Dict]:
    """Run all core module checks and return scored results.

    Args:
        logger: Logger instance.

    Returns:
        List of module dicts with adoption scores.
    """
    results = []
    for module in CORE_MODULES:
        logger.info(f"Checking {module['module_name']}...")
        result = module["check_fn"](logger)
        if result:
            results.append({
                "module_name": module["module_name"],
                "module_key": module["module_key"],
                "icon": module["icon"],
                "licensed": True,
                "scored": True,
                **result,
            })
            logger.info(f"  {module['module_name']}: {result['adoption_level']} ({result['adoption_score']}%)")
    return results


@func.handler(method='GET', path='/api/adoption/check')
def check_adoption(request: Request, _config: Optional[Dict], logger: Logger) -> Response:
    """Check module adoption across all core Falcon modules.

    Returns one entry per module with adoption_level and adoption_score
    derived purely from whether enabled policies exist.
    """
    try:
        logger.info("Starting module adoption check...")

        modules = build_scored_modules(logger)

        if modules:
            avg_score = sum(m["adoption_score"] for m in modules) / len(modules)
            overall_level = (
                "Excellent" if avg_score >= 80
                else "Good" if avg_score >= 60
                else "Partial" if avg_score >= 30
                else "Needs Attention"
            )
        else:
            avg_score = 0
            overall_level = "Unknown"

        return Response(
            body={
                "scan_timestamp": datetime.utcnow().isoformat() + "Z",
                "overall_score": round(avg_score, 2),
                "overall_level": overall_level,
                "modules": modules,
                "scored_module_count": len(modules),
                "total_module_count": len(modules),
            },
            code=200,
        )

    except Exception as exc:
        logger.error(f"Error in module adoption check: {exc}")
        import traceback
        logger.error(traceback.format_exc())
        return Response(
            code=500,
            errors=[APIError(code=500, message=f"Error: {exc}")],
        )


@func.handler(method='GET', path='/api/adoption/discover-utilization')
def check_discover_utilization(request: Request, _config: Optional[Dict], logger: Logger) -> Response:
    """Check Falcon Discover utilization by counting discovered hosts.

    Args:
        request: Incoming Foundry request.
        _config: Unused config dict.
        logger: Logger instance.

    Returns:
        Response with host counts and utilization status.
    """
    try:
        logger.info("Checking Falcon Discover utilization...")
        hosts_api = Hosts()

        response = hosts_api.query_devices_by_filter_scroll(limit=5000)
        if response["status_code"] != 200:
            return Response(
                body={"data_available": False, "utilization_status": "Unknown"},
                code=200,
            )

        host_ids = response.get("body", {}).get("resources", [])
        total_hosts = len(host_ids)

        if total_hosts == 0:
            return Response(
                body={
                    "data_available": False,
                    "total_hosts": 0,
                    "utilization_status": "No Data",
                    "message": "No assets discovered yet.",
                    "recommendation": "Deploy Falcon sensors to start discovering assets.",
                },
                code=200,
            )

        return Response(
            body={
                "data_available": True,
                "total_hosts": total_hosts,
                "utilization_status": "Active" if total_hosts > 0 else "No Data",
                "message": f"{total_hosts} hosts visible in Falcon Discover.",
                "recommendation": "Review unmanaged assets regularly.",
                "timestamp": datetime.utcnow().isoformat() + "Z",
            },
            code=200,
        )

    except Exception as exc:
        logger.error(f"Error checking Discover utilization: {exc}")
        return Response(
            code=500,
            errors=[APIError(code=500, message=f"Error: {exc}")],
        )


if __name__ == '__main__':
    func.run()
