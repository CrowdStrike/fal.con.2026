"""
Host Health Checker - Consolidated operational health checks for hosts
Detects: RFM hosts, stale hosts, unmanaged hosts, isolated hosts, policy gaps, and host group health
"""
from datetime import datetime, timedelta
from falconpy import Hosts
from crowdstrike.foundry.function import Function, Request, Response, APIError
from logging import Logger
from typing import Dict, List, Optional
from collections import defaultdict

func = Function.instance()


def detect_rfm_hosts(devices: List[Dict], logger: Logger) -> Dict:
    """Detect hosts in Reduced Functionality Mode."""
    rfm_hosts = []

    for device in devices:
        # RFM field can be boolean True or string "yes"
        rfm_value = device.get("reduced_functionality_mode")

        # Check if host is actually in RFM
        # RFM is typically indicated by:
        # - reduced_functionality_mode = True (boolean)
        # - reduced_functionality_mode = "yes" (string)
        is_rfm = False

        if rfm_value is True:
            is_rfm = True
        elif isinstance(rfm_value, str) and rfm_value.lower() in ["yes", "true", "1"]:
            is_rfm = True

        if is_rfm:
            rfm_hosts.append({
                "device_id": device.get("device_id", ""),
                "hostname": device.get("hostname", "Unknown"),
                "platform": device.get("platform_name", "Unknown"),
                "last_seen": device.get("last_seen", "Unknown"),
                "issue_details": "Sensor in Reduced Functionality Mode - degraded protection"
            })

    logger.info(f"Found {len(rfm_hosts)} hosts in RFM")

    return {
        "count": len(rfm_hosts),
        "severity": "critical",
        "hosts": rfm_hosts[:100]  # Limit to first 100 for display
    }


def detect_stale_hosts(devices: List[Dict], threshold_days: int, logger: Logger) -> Dict:
    """Detect hosts not seen in threshold_days (default 7 days per spec)."""
    stale_threshold = datetime.utcnow() - timedelta(days=threshold_days)
    stale_hosts = []

    for device in devices:
        last_seen = device.get("last_seen")
        if last_seen:
            try:
                last_seen_dt = datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
                if last_seen_dt < stale_threshold:
                    days_stale = (datetime.utcnow().replace(tzinfo=last_seen_dt.tzinfo) - last_seen_dt).days
                    stale_hosts.append({
                        "device_id": device.get("device_id", ""),
                        "hostname": device.get("hostname", "Unknown"),
                        "platform": device.get("platform_name", "Unknown"),
                        "last_seen": last_seen,
                        "days_offline": days_stale,
                        "issue_details": f"Host offline for {days_stale} days"
                    })
            except Exception as e:
                logger.warning(f"Failed to parse last_seen for {device.get('hostname')}: {str(e)}")

    logger.info(f"Found {len(stale_hosts)} stale hosts (>{threshold_days} days)")

    return {
        "count": len(stale_hosts),
        "threshold_days": threshold_days,
        "severity": "medium",
        "hosts": stale_hosts[:100]  # Limit to first 100 for display
    }


def detect_unmanaged_hosts(devices: List[Dict], logger: Logger) -> Dict:
    """Detect discovered assets without sensor coverage."""
    unmanaged_hosts = []

    for device in devices:
        # Check if host is unmanaged (no sensor installed or status indicates unmanaged)
        status = device.get("status", "").lower()
        agent_version = device.get("agent_version")

        # Host is unmanaged if:
        # 1. Status explicitly says "unmanaged"
        # 2. Status is "normal" but no agent version (discovered but no sensor)
        is_unmanaged = (
            "unmanaged" in status or
            (status == "normal" and not agent_version)
        )

        if is_unmanaged:
            unmanaged_hosts.append({
                "device_id": device.get("device_id", ""),
                "hostname": device.get("hostname", "Unknown"),
                "platform": device.get("platform_name", "Unknown"),
                "status": status,
                "local_ip": device.get("local_ip", "Unknown"),
                "issue_details": "Asset discovered but no sensor deployed"
            })

    logger.info(f"Found {len(unmanaged_hosts)} unmanaged hosts")

    return {
        "count": len(unmanaged_hosts),
        "severity": "high",
        "hosts": unmanaged_hosts[:100]  # Limit to first 100 for display
    }


def detect_isolated_hosts(devices: List[Dict], logger: Logger) -> Dict:
    """Detect hosts under network containment."""
    isolated_hosts = []

    for device in devices:
        # Check for containment status
        # Falcon API uses "status" field or "device_policies" for containment
        status = device.get("status", "").lower()

        # Check if host is contained/isolated
        is_isolated = "contained" in status or "containment" in status

        # Also check device policies for containment state
        if not is_isolated:
            device_policies = device.get("device_policies", {})
            # Some versions use "sensor_update" policies to track containment
            for policy_type, policy_data in device_policies.items():
                if isinstance(policy_data, dict):
                    policy_settings = policy_data.get("settings", {})
                    if policy_settings.get("contained", False):
                        is_isolated = True
                        break

        if is_isolated:
            isolated_hosts.append({
                "device_id": device.get("device_id", ""),
                "hostname": device.get("hostname", "Unknown"),
                "platform": device.get("platform_name", "Unknown"),
                "status": status,
                "last_seen": device.get("last_seen", "Unknown"),
                "issue_details": "Host under network containment"
            })

    logger.info(f"Found {len(isolated_hosts)} isolated hosts")

    return {
        "count": len(isolated_hosts),
        "severity": "high",
        "hosts": isolated_hosts[:100]  # Limit to first 100 for display
    }


def detect_policy_gaps(devices: List[Dict], logger: Logger) -> Dict:
    """Detect hosts missing prevention policy assignments."""
    policy_gap_hosts = []

    for device in devices:
        # Check if host has a prevention policy assigned
        device_policies = device.get("device_policies", {})
        prevention_policy = device_policies.get("prevention", {})
        policy_id = prevention_policy.get("policy_id")

        if not policy_id:
            policy_gap_hosts.append({
                "device_id": device.get("device_id", ""),
                "hostname": device.get("hostname", "Unknown"),
                "platform": device.get("platform_name", "Unknown"),
                "last_seen": device.get("last_seen", "Unknown"),
                "issue_details": "No prevention policy assigned"
            })

    logger.info(f"Found {len(policy_gap_hosts)} hosts with policy gaps")

    return {
        "count": len(policy_gap_hosts),
        "severity": "critical",
        "hosts": policy_gap_hosts[:100]  # Limit to first 100 for display
    }


def analyze_host_groups(devices: List[Dict], logger: Logger) -> Dict:
    """Analyze health metrics by host group."""
    group_stats = defaultdict(lambda: {
        "total_hosts": 0,
        "rfm_count": 0,
        "stale_count": 0,
        "policy_gaps": 0,
        "health_score": 100
    })

    ungrouped_count = 0
    stale_threshold = datetime.utcnow() - timedelta(days=7)

    for device in devices:
        groups = device.get("groups", [])

        if not groups:
            ungrouped_count += 1
            groups = ["Ungrouped"]

        for group_id in groups:
            # Use group ID with a cleaner display format
            if group_id == "Ungrouped":
                group_display = "Ungrouped"
            else:
                # Show shortened group ID for better readability
                group_display = f"Group-{group_id[:8]}"

            group_stats[group_display]["total_hosts"] += 1

            # Check for issues
            rfm_value = device.get("reduced_functionality_mode")
            is_rfm = rfm_value is True or (isinstance(rfm_value, str) and rfm_value.lower() in ["yes", "true", "1"])
            if is_rfm:
                group_stats[group_display]["rfm_count"] += 1

            last_seen = device.get("last_seen")
            if last_seen:
                try:
                    last_seen_dt = datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
                    if last_seen_dt < stale_threshold:
                        group_stats[group_display]["stale_count"] += 1
                except:
                    pass

            device_policies = device.get("device_policies", {})
            prevention_policy = device_policies.get("prevention", {})
            if not prevention_policy.get("policy_id"):
                group_stats[group_display]["policy_gaps"] += 1

    # Calculate health scores per group
    groups_list = []
    for group_name, stats in group_stats.items():
        total = stats["total_hosts"]
        if total > 0:
            # Calculate penalties
            rfm_penalty = (stats["rfm_count"] / total) * 20
            stale_penalty = (stats["stale_count"] / total) * 10
            policy_penalty = (stats["policy_gaps"] / total) * 15

            health_score = max(0, 100 - rfm_penalty - stale_penalty - policy_penalty)

            groups_list.append({
                "group_name": group_name,
                "total_hosts": total,
                "health_score": round(health_score, 2),
                "rfm_count": stats["rfm_count"],
                "stale_count": stats["stale_count"],
                "policy_gaps": stats["policy_gaps"]
            })

    # Sort by health score (lowest first to highlight issues)
    groups_list.sort(key=lambda x: x["health_score"])

    logger.info(f"Analyzed {len(groups_list)} host groups")

    return {
        "total_groups": len(groups_list),
        "ungrouped_hosts": ungrouped_count,
        "groups": groups_list
    }


def calculate_host_health_score(counts: Dict, total_hosts: int) -> Dict:
    """Calculate 0-100 health score with penalties."""
    if total_hosts == 0:
        return {"score": 0, "status": "Unknown"}

    score = 100

    # Apply penalties with caps (per spec)
    rfm_penalty = min(counts["rfm"] * 10, 15)
    unmanaged_penalty = min(counts["unmanaged"] * 5, 10)
    policy_gap_penalty = min(counts["policy_gaps"] * 8, 10)
    stale_penalty = min(counts["stale"] * 2, 10)
    isolated_penalty = min(counts["isolated"] * 1, 5)

    score -= (rfm_penalty + unmanaged_penalty + policy_gap_penalty + stale_penalty + isolated_penalty)
    score = max(0, score)

    # Assign status
    if score >= 90:
        status = "Excellent"
    elif score >= 80:
        status = "Good"
    elif score >= 70:
        status = "Fair"
    elif score >= 60:
        status = "Needs Attention"
    else:
        status = "Critical"

    return {
        "score": round(score, 2),
        "status": status,
        "penalties": {
            "rfm": rfm_penalty,
            "unmanaged": unmanaged_penalty,
            "policy_gaps": policy_gap_penalty,
            "stale": stale_penalty,
            "isolated": isolated_penalty
        }
    }


def generate_recommendations(counts: Dict, host_data: Dict) -> List[Dict]:
    """Generate priority recommendations based on findings."""
    recommendations = []
    priority = 1

    # RFM hosts - highest priority
    if counts["rfm"] > 0:
        recommendations.append({
            "priority": priority,
            "severity": "critical",
            "issue": f"{counts['rfm']} hosts in Reduced Functionality Mode",
            "recommendation": "Investigate RFM hosts immediately - check sensor connectivity, licensing, and system health",
            "affected_count": counts["rfm"]
        })
        priority += 1

    # Policy gaps - critical
    if counts["policy_gaps"] > 0:
        recommendations.append({
            "priority": priority,
            "severity": "critical",
            "issue": f"{counts['policy_gaps']} hosts without prevention policy assignments",
            "recommendation": "Assign prevention policies to all hosts to ensure consistent security posture",
            "affected_count": counts["policy_gaps"]
        })
        priority += 1

    # Unmanaged hosts - high
    if counts["unmanaged"] > 0:
        recommendations.append({
            "priority": priority,
            "severity": "high",
            "issue": f"{counts['unmanaged']} unmanaged assets discovered",
            "recommendation": "Deploy sensors to unmanaged assets or validate if they should be excluded from monitoring",
            "affected_count": counts["unmanaged"]
        })
        priority += 1

    # Isolated hosts - high
    if counts["isolated"] > 0:
        recommendations.append({
            "priority": priority,
            "severity": "high",
            "issue": f"{counts['isolated']} hosts under network containment",
            "recommendation": "Review isolated hosts - complete incident response and lift containment when safe",
            "affected_count": counts["isolated"]
        })
        priority += 1

    # Stale hosts - medium
    if counts["stale"] > 0:
        recommendations.append({
            "priority": priority,
            "severity": "medium",
            "issue": f"{counts['stale']} hosts offline for 7+ days",
            "recommendation": "Review stale hosts - remove decommissioned assets or investigate offline systems",
            "affected_count": counts["stale"]
        })
        priority += 1

    # If no issues, add positive feedback
    if not recommendations:
        recommendations.append({
            "priority": 1,
            "severity": "success",
            "issue": "No critical host health issues detected",
            "recommendation": "Excellent! Continue monitoring for emerging issues",
            "affected_count": 0
        })

    return recommendations


@func.handler(method='POST', path='/api/hosts/health')
def get_host_health(request: Request, _config: Optional[Dict], logger: Logger) -> Response:
    """
    Comprehensive host health check analyzing RFM, stale, unmanaged, isolated hosts,
    policy gaps, and host group health.
    """
    try:
        logger.info("Starting consolidated host health check...")

        # Get threshold from request body (default 7 days per spec)
        body = request.body or {}
        threshold_days = body.get("threshold_days", 7)

        # Initialize Falcon Hosts API
        hosts_api = Hosts()

        # Query all hosts
        logger.info("Querying all hosts...")
        hosts_response = hosts_api.query_devices_by_filter_scroll(limit=5000)

        if hosts_response["status_code"] != 200:
            logger.error(f"Failed to query hosts: {hosts_response}")
            return Response(
                code=500,
                errors=[APIError(code=500, message="Failed to query hosts")]
            )

        device_ids = hosts_response.get("body", {}).get("resources", [])

        if not device_ids:
            logger.info("No devices found")
            return Response(
                body={
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "message": "No hosts found in environment",
                    "overall_health": {
                        "score": 0,
                        "status": "Unknown",
                        "total_hosts": 0,
                        "total_issues": 0
                    }
                },
                code=200
            )

        logger.info(f"Found {len(device_ids)} devices, fetching details...")

        # Get detailed device information
        details_response = hosts_api.get_device_details(ids=device_ids)

        if details_response["status_code"] != 200:
            logger.error(f"Failed to get device details: {details_response}")
            return Response(
                code=500,
                errors=[APIError(code=500, message="Failed to get device details")]
            )

        devices = details_response.get("body", {}).get("resources", [])
        logger.info(f"Retrieved details for {len(devices)} devices")

        # Run all detection checks
        logger.info("Running host health checks...")

        rfm_data = detect_rfm_hosts(devices, logger)
        stale_data = detect_stale_hosts(devices, threshold_days, logger)
        unmanaged_data = detect_unmanaged_hosts(devices, logger)
        isolated_data = detect_isolated_hosts(devices, logger)
        policy_gap_data = detect_policy_gaps(devices, logger)
        host_groups_data = analyze_host_groups(devices, logger)

        # Calculate counts for scoring
        counts = {
            "rfm": rfm_data["count"],
            "stale": stale_data["count"],
            "unmanaged": unmanaged_data["count"],
            "isolated": isolated_data["count"],
            "policy_gaps": policy_gap_data["count"]
        }

        total_issues = sum(counts.values())

        # Calculate overall health score
        health_score = calculate_host_health_score(counts, len(devices))

        # Generate recommendations
        recommendations = generate_recommendations(counts, {
            "rfm": rfm_data,
            "stale": stale_data,
            "unmanaged": unmanaged_data,
            "isolated": isolated_data,
            "policy_gaps": policy_gap_data
        })

        # Build response
        result = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "overall_health": {
                "score": health_score["score"],
                "status": health_score["status"],
                "total_hosts": len(devices),
                "total_issues": total_issues,
                "penalties": health_score.get("penalties", {})
            },
            "rfm_hosts": rfm_data,
            "unmanaged_hosts": unmanaged_data,
            "stale_hosts": stale_data,
            "isolated_hosts": isolated_data,
            "policy_gaps": policy_gap_data,
            "host_groups": host_groups_data,
            "recommendations": recommendations
        }

        logger.info(f"Host health check complete. Score: {health_score['score']}, Issues: {total_issues}")

        return Response(body=result, code=200)

    except Exception as e:
        logger.error(f"Error in host health check: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return Response(
            code=500,
            errors=[APIError(code=500, message=f"Error performing host health check: {str(e)}")]
        )


if __name__ == '__main__':
    func.run()
