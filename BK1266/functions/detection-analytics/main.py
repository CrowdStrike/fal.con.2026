"""
Detection Analytics - Analyze recent detections, severity breakdown, and trending
Version: 2.7.0
"""
from datetime import datetime, timedelta
from falconpy import Detects
from crowdstrike.foundry.function import Function, Request, Response
from logging import Logger
from typing import Dict, List, Optional

func = Function.instance()


def calculate_detection_score(detection_data: Dict) -> Dict:
    """Calculate health score based on detection metrics.

    Lower score = more critical detections (indicates active threats)
    Higher score = fewer/lower severity detections (better security posture)
    """
    total_count = detection_data.get("total_count", 0)
    counts = detection_data.get("counts_by_severity", {})

    critical = counts.get("critical", 0)
    high = counts.get("high", 0)
    medium = counts.get("medium", 0)
    low = counts.get("low", 0)

    if total_count == 0:
        return {
            "score": 100,
            "status": "Excellent",
            "message": "No recent detections"
        }

    # Calculate penalties based on severity
    # Critical detections are most concerning
    critical_penalty = critical * 5  # 5 points per critical
    high_penalty = high * 2          # 2 points per high
    medium_penalty = medium * 0.5    # 0.5 points per medium
    low_penalty = low * 0.1          # 0.1 points per low

    # Start with 100 and subtract penalties (max 50 deduction)
    score = 100 - min(50, critical_penalty + high_penalty + medium_penalty + low_penalty)
    score = max(0, min(100, score))

    # Determine status
    if score >= 90:
        status = "Excellent"
        severity = "none"
    elif score >= 75:
        status = "Good"
        severity = "low"
    elif score >= 60:
        status = "Fair"
        severity = "medium"
    elif score >= 40:
        status = "Needs Attention"
        severity = "high"
    else:
        status = "Critical"
        severity = "critical"

    return {
        "score": round(score, 1),
        "status": status,
        "severity": severity,
        "message": f"{total_count} detections in last 7 days"
    }


def analyze_detection_types(detections: List[Dict]) -> List[Dict]:
    """Analyze and rank detection types by frequency."""
    type_counts = {}

    for detection in detections:
        # Get detection type/tactic
        det_type = detection.get("behaviors", [{}])[0].get("tactic", "Unknown") if detection.get("behaviors") else "Unknown"

        if det_type not in type_counts:
            type_counts[det_type] = {
                "type": det_type,
                "count": 0,
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0
            }

        type_counts[det_type]["count"] += 1

        # Count by severity
        severity = detection.get("max_severity_displayname", "").lower()
        if severity in type_counts[det_type]:
            type_counts[det_type][severity] += 1

    # Sort by count descending and take top 10
    sorted_types = sorted(type_counts.values(), key=lambda x: x["count"], reverse=True)
    return sorted_types[:10]


@func.handler(method="GET", path="/api/detections/analytics")
def get_detection_analytics(request: Request, _config: Optional[Dict], logger: Logger) -> Response:
    """
    Analyze recent detections (last 7 days) with severity breakdown and trending.

    Returns:
        {
            "timestamp": "2026-08-14T...",
            "period_days": 7,
            "total_count": 145,
            "detection_score": {
                "score": 82.5,
                "status": "Good",
                "severity": "low",
                "message": "145 detections in last 7 days"
            },
            "counts_by_severity": {
                "critical": 5,
                "high": 20,
                "medium": 60,
                "low": 50,
                "informational": 10
            },
            "top_detection_types": [
                {
                    "type": "Malware",
                    "count": 45,
                    "critical": 3,
                    "high": 10,
                    "medium": 25,
                    "low": 7
                }
            ],
            "recent_critical": [
                {
                    "detection_id": "...",
                    "timestamp": "...",
                    "severity": "Critical",
                    "tactic": "...",
                    "hostname": "...",
                    "status": "new|in_progress|resolved"
                }
            ],
            "trending": {
                "daily_counts": [...],
                "trend": "increasing|decreasing|stable"
            }
        }
    """
    logger.info("Starting detection analytics...")

    try:
        # Initialize Detects API
        falcon_detects = Detects()

        # Calculate date range (last 7 days)
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=7)

        # Format dates for Falcon API (RFC3339)
        start_str = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_str = end_date.strftime("%Y-%m-%dT%H:%M:%SZ")

        logger.info(f"Querying detections from {start_str} to {end_str}")

        # Query detection IDs with date filter
        filter_query = f"created_timestamp:>'{start_str}'+created_timestamp:<'{end_str}'"

        query_response = falcon_detects.query_detects(
            filter=filter_query,
            limit=5000,  # Get up to 5000 detections
            sort="created_timestamp.desc"
        )

        if query_response["status_code"] != 200:
            logger.error(f"Failed to query detections: {query_response}")
            return Response(
                code=query_response["status_code"],
                body={
                    "error": f"Failed to query detections: {query_response.get('errors', [])}",
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
            )

        detection_ids = query_response["body"].get("resources", [])
        total_count = len(detection_ids)

        logger.info(f"Found {total_count} detections")

        if total_count == 0:
            # No detections - return empty structure
            return Response(
                code=200,
                body={
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "period_days": 7,
                    "total_count": 0,
                    "detection_score": {
                        "score": 100,
                        "status": "Excellent",
                        "severity": "none",
                        "message": "No detections in last 7 days"
                    },
                    "counts_by_severity": {
                        "critical": 0,
                        "high": 0,
                        "medium": 0,
                        "low": 0,
                        "informational": 0
                    },
                    "top_detection_types": [],
                    "recent_critical": [],
                    "trending": {
                        "daily_counts": [0, 0, 0, 0, 0, 0, 0],
                        "trend": "stable"
                    }
                }
            )

        # Get detection details (in batches of 1000)
        detections = []
        batch_size = 1000

        for i in range(0, len(detection_ids), batch_size):
            batch_ids = detection_ids[i:i+batch_size]

            details_response = falcon_detects.get_detect_summaries(ids=batch_ids)

            if details_response["status_code"] != 200:
                logger.warning(f"Failed to get detection details for batch {i}: {details_response}")
                continue

            batch_detections = details_response["body"].get("resources", [])
            detections.extend(batch_detections)

        logger.info(f"Retrieved details for {len(detections)} detections")

        # Analyze severity breakdown
        counts_by_severity = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "informational": 0
        }

        recent_critical = []
        daily_counts = [0] * 7  # Last 7 days

        for detection in detections:
            # Count by severity
            severity = detection.get("max_severity_displayname", "Informational").lower()
            if severity in counts_by_severity:
                counts_by_severity[severity] += 1
            else:
                counts_by_severity["informational"] += 1

            # Track recent critical detections
            if severity == "critical" and len(recent_critical) < 20:
                recent_critical.append({
                    "detection_id": detection.get("detection_id", ""),
                    "timestamp": detection.get("created_timestamp", ""),
                    "severity": detection.get("max_severity_displayname", ""),
                    "tactic": detection.get("behaviors", [{}])[0].get("tactic", "Unknown") if detection.get("behaviors") else "Unknown",
                    "hostname": detection.get("device", {}).get("hostname", "Unknown"),
                    "status": detection.get("status", "new")
                })

            # Count by day for trending
            try:
                det_date = datetime.fromisoformat(detection.get("created_timestamp", "").replace("Z", "+00:00"))
                days_ago = (end_date - det_date).days
                if 0 <= days_ago < 7:
                    daily_counts[6 - days_ago] += 1
            except Exception:
                # Skip detections with invalid timestamps
                pass

        # Analyze detection types
        top_detection_types = analyze_detection_types(detections)

        # Calculate trending
        if len(daily_counts) >= 3:
            recent_avg = sum(daily_counts[-3:]) / 3
            older_avg = sum(daily_counts[:3]) / 3 if len(daily_counts) >= 3 else 0

            if recent_avg > older_avg * 1.2:
                trend = "increasing"
            elif recent_avg < older_avg * 0.8:
                trend = "decreasing"
            else:
                trend = "stable"
        else:
            trend = "stable"

        # Calculate detection score
        detection_score = calculate_detection_score({
            "total_count": total_count,
            "counts_by_severity": counts_by_severity
        })

        # Build response
        result = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "period_days": 7,
            "total_count": total_count,
            "detection_score": detection_score,
            "counts_by_severity": counts_by_severity,
            "top_detection_types": top_detection_types,
            "recent_critical": recent_critical,
            "trending": {
                "daily_counts": daily_counts,
                "trend": trend
            }
        }

        logger.info("Detection analytics completed successfully")
        return Response(code=200, body=result)

    except Exception as e:
        logger.error(f"Error in detection analytics: {e}")
        return Response(
            code=500,
            body={"error": str(e), "timestamp": datetime.utcnow().isoformat() + "Z"}
        )
