"""
Sensor Health - Analyze sensor versions, OS distributions, and operational status
"""
from datetime import datetime, timedelta
from falconpy import Hosts
from crowdstrike.foundry.function import Function, Request, Response, APIError
from logging import Logger
from typing import Dict, List, Optional

func = Function.instance()

# Try to import Collections, but make it optional
try:
    from crowdstrike.foundry.collections import Collections
    COLLECTIONS_AVAILABLE = True
except ImportError:
    COLLECTIONS_AVAILABLE = False


def calculate_sensor_health_score(sensor_data: Dict) -> Dict:
    """Calculate health score based on sensor metrics."""
    total_sensors = sensor_data.get("total_sensors", 0)
    inactive_count = sensor_data.get("inactive_count", 0)
    rfm_count = sensor_data.get("rfm_count", 0)
    outdated_count = sensor_data.get("version_analysis", {}).get("outdated_count", 0)

    if total_sensors == 0:
        return {
            "score": 0,
            "status": "Unknown",
            "message": "No sensors found"
        }

    # Calculate penalties
    inactive_penalty = (inactive_count / total_sensors) * 100 if total_sensors > 0 else 0
    rfm_penalty = (rfm_count / total_sensors) * 100 if total_sensors > 0 else 0
    outdated_penalty = (outdated_count / total_sensors) * 100 if total_sensors > 0 else 0

    # Start with 100 and subtract penalties
    score = 100 - (inactive_penalty * 0.5) - (rfm_penalty * 1.0) - (outdated_penalty * 0.3)
    score = max(0, min(100, score))

    # Determine status
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
        "inactive_percentage": round(inactive_penalty, 2),
        "rfm_percentage": round(rfm_penalty, 2),
        "outdated_percentage": round(outdated_penalty, 2)
    }


@func.handler(method='GET', path='/api/sensors/health')
def get_sensor_health(request: Request, _config: Optional[Dict], logger: Logger) -> Response:
    """
    Comprehensive sensor health check analyzing versions, OS, and operational status.
    """
    try:
        logger.info("Starting sensor health check...")

        # Initialize Falcon Hosts API
        hosts_api = Hosts()

        # Query all hosts
        logger.info("Querying all hosts...")
        hosts_response = hosts_api.query_devices_by_filter(limit=5000)

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
                    "total_sensors": 0,
                    "message": "No sensors found in environment"
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

        # Analyze sensors by platform
        platform_stats = {}
        inactive_threshold = datetime.utcnow() - timedelta(days=14)
        inactive_sensors = []
        rfm_sensors = []
        version_distribution = {}
        os_distribution = {}

        for device in devices:
            platform = device.get("platform_name", "Unknown")
            agent_version = device.get("agent_version", "Unknown")
            os_version = device.get("os_version", "Unknown")
            last_seen = device.get("last_seen")
            reduced_functionality_mode = device.get("reduced_functionality_mode", "no") == "yes"
            hostname = device.get("hostname", "Unknown")
            device_id = device.get("device_id", "")

            # Platform stats
            if platform not in platform_stats:
                platform_stats[platform] = {
                    "count": 0,
                    "active": 0,
                    "inactive": 0,
                    "rfm": 0
                }
            platform_stats[platform]["count"] += 1

            # Check inactive status
            if last_seen:
                try:
                    last_seen_dt = datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
                    if last_seen_dt < inactive_threshold:
                        inactive_sensors.append({
                            "device_id": device_id,
                            "hostname": hostname,
                            "platform": platform,
                            "last_seen": last_seen
                        })
                        platform_stats[platform]["inactive"] += 1
                    else:
                        platform_stats[platform]["active"] += 1
                except:
                    platform_stats[platform]["active"] += 1
            else:
                platform_stats[platform]["active"] += 1

            # Check RFM status
            if reduced_functionality_mode:
                rfm_sensors.append({
                    "device_id": device_id,
                    "hostname": hostname,
                    "platform": platform
                })
                platform_stats[platform]["rfm"] += 1

            # Version distribution
            version_key = f"{platform}:{agent_version}"
            if version_key not in version_distribution:
                version_distribution[version_key] = 0
            version_distribution[version_key] += 1

            # OS distribution
            os_key = f"{platform}:{os_version}"
            if os_key not in os_distribution:
                os_distribution[os_key] = 0
            os_distribution[os_key] += 1

        # Calculate total sensors
        total_sensors = len(devices)
        inactive_count = len(inactive_sensors)
        rfm_count = len(rfm_sensors)

        # Version analysis (simplified - would need version comparison logic for accurate N-2, N-3, etc.)
        outdated_count = 0  # Placeholder - would need version comparison

        # Calculate health score
        health_data = {
            "total_sensors": total_sensors,
            "inactive_count": inactive_count,
            "rfm_count": rfm_count,
            "version_analysis": {
                "outdated_count": outdated_count
            }
        }
        health_score = calculate_sensor_health_score(health_data)

        # Build response
        result = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "health_score": health_score,
            "summary": {
                "total_sensors": total_sensors,
                "active_sensors": total_sensors - inactive_count,
                "inactive_sensors": inactive_count,
                "rfm_sensors": rfm_count
            },
            "platform_breakdown": platform_stats,
            "version_distribution": version_distribution,
            "os_distribution": os_distribution,
            "top_issues": []
        }

        # Add issues
        if inactive_count > 0:
            result["top_issues"].append({
                "severity": "HIGH" if inactive_count > 10 else "MEDIUM",
                "issue": f"{inactive_count} sensors inactive for 14+ days",
                "recommendation": "Investigate inactive sensors and remove stale devices"
            })

        if rfm_count > 0:
            result["top_issues"].append({
                "severity": "CRITICAL",
                "issue": f"{rfm_count} sensors in Reduced Functionality Mode",
                "recommendation": "Check sensor connectivity and licensing issues"
            })

        logger.info(f"Sensor health check complete. Score: {health_score['score']}")

        # Store in collection for historical tracking (if available)
        if COLLECTIONS_AVAILABLE:
            try:
                collections = Collections()
                collections.upsert(
                    collection_name="sensor_health",
                    data=[result]
                )
                logger.info("Sensor health data stored in collection")
            except Exception as e:
                logger.warning(f"Failed to store sensor health data: {str(e)}")
        else:
            logger.info("Collections not available, skipping historical storage")

        return Response(body=result, code=200)

    except Exception as e:
        logger.error(f"Error in sensor health check: {str(e)}")
        return Response(
            code=500,
            errors=[APIError(code=500, message=f"Error performing sensor health check: {str(e)}")]
        )


if __name__ == '__main__':
    func.run()
