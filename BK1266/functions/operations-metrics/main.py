"""
Operations Metrics - Track uninstall protection, version currency, policy assignments, and EOL warnings
"""
from datetime import datetime, timedelta
from collections import defaultdict
from crowdstrike.foundry.function import Function, Request, Response, APIError
from falconpy import Hosts, PreventionPolicies
from logging import Logger
from typing import Dict, List, Optional

func = Function.instance()


def get_sensor_version_age(version: str) -> Dict:
    """Determine sensor version age category."""
    # Version format: X.Y.Z.NNNNN
    try:
        parts = version.split('.')
        if len(parts) >= 4:
            major = int(parts[0])
            minor = int(parts[1])
            # Simplified age categorization (adjust based on your support matrix)
            # N = current, N-1, N-2, N-3, N-4+
            version_num = major * 100 + minor

            # As of 2026, assume current major version is 7.x
            if major >= 7 and minor >= 17:
                return {"category": "N (Current)", "age_months": 0, "supported": True}
            elif major >= 7 and minor >= 15:
                return {"category": "N-1", "age_months": 3, "supported": True}
            elif major >= 7 and minor >= 13:
                return {"category": "N-2", "age_months": 6, "supported": True}
            elif major >= 7 and minor >= 10:
                return {"category": "N-3", "age_months": 9, "supported": True}
            else:
                return {"category": "N-4+ (EOL Risk)", "age_months": 12, "supported": False}
    except:
        pass

    return {"category": "Unknown", "age_months": 0, "supported": True}


def analyze_uninstall_protection(hosts: List[Dict], logger: Logger) -> Dict:
    """Analyze uninstall protection status by platform."""
    stats = {
        "total": len(hosts),
        "protected": 0,
        "unprotected": 0,
        "by_platform": {}
    }

    for host in hosts:
        platform = host.get('platform_name', 'Unknown')
        if platform not in stats["by_platform"]:
            stats["by_platform"][platform] = {
                "total": 0,
                "protected": 0,
                "unprotected": 0,
                "protection_rate": 0.0
            }

        stats["by_platform"][platform]["total"] += 1

        # Check uninstall protection token presence
        maintenance_token = host.get('device_policies', {}).get('prevention', {}).get('maintenance_token')
        if maintenance_token:
            stats["unprotected"] += 1
            stats["by_platform"][platform]["unprotected"] += 1
        else:
            stats["protected"] += 1
            stats["by_platform"][platform]["protected"] += 1

    # Calculate protection rates
    stats["protection_rate"] = round((stats["protected"] / stats["total"] * 100), 2) if stats["total"] > 0 else 0

    for platform in stats["by_platform"]:
        total = stats["by_platform"][platform]["total"]
        protected = stats["by_platform"][platform]["protected"]
        stats["by_platform"][platform]["protection_rate"] = round((protected / total * 100), 2) if total > 0 else 0

    return stats


def analyze_version_currency(hosts: List[Dict], logger: Logger) -> Dict:
    """Analyze sensor version distribution and currency."""
    version_stats = {
        "total_hosts": len(hosts),
        "version_distribution": defaultdict(int),
        "age_categories": {
            "N (Current)": 0,
            "N-1": 0,
            "N-2": 0,
            "N-3": 0,
            "N-4+ (EOL Risk)": 0,
            "Unknown": 0
        },
        "by_platform": {},
        "eol_warnings": []
    }

    for host in hosts:
        version = host.get('agent_version', 'Unknown')
        platform = host.get('platform_name', 'Unknown')
        hostname = host.get('hostname', 'Unknown')

        version_stats["version_distribution"][version] += 1

        # Get version age
        age_info = get_sensor_version_age(version)
        category = age_info["category"]
        version_stats["age_categories"][category] += 1

        # Track EOL warnings
        if not age_info["supported"]:
            version_stats["eol_warnings"].append({
                "hostname": hostname,
                "platform": platform,
                "version": version,
                "age_months": age_info["age_months"]
            })

        # By platform breakdown
        if platform not in version_stats["by_platform"]:
            version_stats["by_platform"][platform] = {
                "total": 0,
                "current": 0,
                "outdated": 0,
                "versions": defaultdict(int)
            }

        version_stats["by_platform"][platform]["total"] += 1
        version_stats["by_platform"][platform]["versions"][version] += 1

        if age_info["category"] == "N (Current)":
            version_stats["by_platform"][platform]["current"] += 1
        else:
            version_stats["by_platform"][platform]["outdated"] += 1

    # Convert defaultdicts to regular dicts for JSON serialization
    version_stats["version_distribution"] = dict(version_stats["version_distribution"])
    for platform in version_stats["by_platform"]:
        version_stats["by_platform"][platform]["versions"] = dict(version_stats["by_platform"][platform]["versions"])

    # Calculate currency percentage
    total = version_stats["total_hosts"]
    current = version_stats["age_categories"]["N (Current)"]
    version_stats["currency_percentage"] = round((current / total * 100), 2) if total > 0 else 0

    return version_stats


def analyze_policy_assignments(hosts: List[Dict], policies_data: Dict, logger: Logger) -> Dict:
    """Analyze policy assignment coverage and distribution."""
    assignment_stats = {
        "total_hosts": len(hosts),
        "assigned": 0,
        "unassigned": 0,
        "by_policy": {},
        "assignment_rate": 0.0
    }

    # Get prevention policies
    prevention_policies = policies_data.get("prevention", {})

    for host in hosts:
        prevention_policy_id = host.get('device_policies', {}).get('prevention', {}).get('policy_id')

        if prevention_policy_id:
            assignment_stats["assigned"] += 1

            # Find policy name
            policy_name = "Unknown Policy"
            for policy in prevention_policies:
                if policy.get('id') == prevention_policy_id:
                    policy_name = policy.get('name', 'Unknown Policy')
                    break

            if policy_name not in assignment_stats["by_policy"]:
                assignment_stats["by_policy"][policy_name] = {
                    "host_count": 0,
                    "policy_id": prevention_policy_id
                }

            assignment_stats["by_policy"][policy_name]["host_count"] += 1
        else:
            assignment_stats["unassigned"] += 1

    assignment_stats["assignment_rate"] = round((assignment_stats["assigned"] / assignment_stats["total_hosts"] * 100), 2) if assignment_stats["total_hosts"] > 0 else 0

    return assignment_stats


@func.handler(method='GET', path='/api/operations/metrics')
def get_metrics(request: Request, _config: Optional[Dict], logger: Logger) -> Response:
    """
    Comprehensive operational metrics including uninstall protection, version currency, and policy assignments.
    """
    try:
        logger.info("Starting operational metrics collection...")

        # Get hosts data
        hosts_api = Hosts()
        hosts_response = hosts_api.query_devices_by_filter_scroll(limit=5000)

        if hosts_response["status_code"] != 200:
            return Response(
                code=hosts_response["status_code"],
                errors=[APIError(code=hosts_response["status_code"], message="Failed to query hosts")]
            )

        host_ids = hosts_response.get("body", {}).get("resources", [])
        logger.info(f"Found {len(host_ids)} hosts")

        if not host_ids:
            return Response(
                body={
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "message": "No hosts found in CID",
                    "uninstall_protection": {},
                    "version_currency": {},
                    "policy_assignments": {}
                },
                code=200
            )

        # Get detailed host information
        details_response = hosts_api.get_device_details(ids=host_ids)

        if details_response["status_code"] != 200:
            return Response(
                code=details_response["status_code"],
                errors=[APIError(code=details_response["status_code"], message="Failed to get host details")]
            )

        hosts = details_response.get("body", {}).get("resources", [])
        logger.info(f"Retrieved details for {len(hosts)} hosts")

        # Get prevention policies for assignment analysis
        policies_api = PreventionPolicies()
        policies_response = policies_api.query_combined_policies(limit=100)

        prevention_policies = []
        if policies_response["status_code"] == 200:
            prevention_policies = policies_response.get("body", {}).get("resources", [])
            logger.info(f"Retrieved {len(prevention_policies)} prevention policies")

        # Analyze operational metrics
        logger.info("Analyzing uninstall protection...")
        uninstall_protection = analyze_uninstall_protection(hosts, logger)

        logger.info("Analyzing version currency...")
        version_currency = analyze_version_currency(hosts, logger)

        logger.info("Analyzing policy assignments...")
        policy_assignments = analyze_policy_assignments(
            hosts,
            {"prevention": prevention_policies},
            logger
        )

        # Build response
        response_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "total_hosts": len(hosts),
            "uninstall_protection": uninstall_protection,
            "version_currency": version_currency,
            "policy_assignments": policy_assignments,
            "summary": {
                "protection_rate": uninstall_protection["protection_rate"],
                "currency_rate": version_currency["currency_percentage"],
                "assignment_rate": policy_assignments["assignment_rate"],
                "eol_host_count": len(version_currency["eol_warnings"]),
                "critical_issues": []
            }
        }

        # Add critical issues
        if uninstall_protection["protection_rate"] < 95:
            response_data["summary"]["critical_issues"].append("Low uninstall protection rate")

        if version_currency["currency_percentage"] < 80:
            response_data["summary"]["critical_issues"].append("Many hosts on outdated sensor versions")

        if policy_assignments["assignment_rate"] < 100:
            response_data["summary"]["critical_issues"].append(f"{policy_assignments['unassigned']} hosts without policy assignment")

        if len(version_currency["eol_warnings"]) > 0:
            response_data["summary"]["critical_issues"].append(f"{len(version_currency['eol_warnings'])} hosts on EOL/unsupported versions")

        logger.info("Operational metrics collection complete")

        return Response(body=response_data, code=200)

    except Exception as e:
        logger.error(f"Error collecting operational metrics: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return Response(
            code=500,
            errors=[APIError(code=500, message=f"Error: {str(e)}")]
        )


if __name__ == '__main__':
    func.run()
