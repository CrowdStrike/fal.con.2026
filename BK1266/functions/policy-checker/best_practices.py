"""
Best Practice Compliance Checking
Compares Falcon prevention policies against CrowdStrike recommended settings.
Version: 1.0.0
"""
import json
import os
from typing import Dict, List, Optional, Tuple


# Load best practices from JSON file
BEST_PRACTICES_FILE = os.path.join(os.path.dirname(__file__), "best_practices.json")

try:
    with open(BEST_PRACTICES_FILE, 'r') as f:
        BEST_PRACTICES = json.load(f)
except Exception as e:
    # Fallback to empty structure if file not found
    BEST_PRACTICES = {
        "version": "2024.08",
        "source": "CrowdStrike Prevention Policy Best Practices",
        "platforms": {},
        "ml_levels": {
            "Disabled": 0,
            "Cautious": 1,
            "Moderate": 2,
            "Moderate+": 2.5,
            "Aggressive": 3,
            "Extra Aggressive": 4
        }
    }


def compare_setting(current_value, recommended_value, setting_type="boolean") -> bool:
    """
    Compare a current policy setting against the recommended value.

    Args:
        current_value: The actual setting value from the policy (bool, dict, or string)
        recommended_value: The recommended value from best practices
        setting_type: Type of setting - "boolean", "ml_level", or "string"

    Returns:
        True if current setting matches or exceeds recommendation, False otherwise
    """
    if current_value is None:
        return False

    if setting_type == "boolean":
        if recommended_value == "Enabled":
            return current_value is True
        elif recommended_value == "Disabled":
            return current_value is False
        return False

    elif setting_type == "ml_level":
        ml_levels = BEST_PRACTICES.get("ml_levels", {})

        # For mlslider settings, current_value is a dict like:
        # {"detection": "AGGRESSIVE", "prevention": "MODERATE"}
        # We check the "prevention" level (stricter compliance check)
        if isinstance(current_value, dict):
            current_level_str = current_value.get('prevention') or current_value.get('detection', 'DISABLED')
        else:
            current_level_str = str(current_value)

        current_level = ml_levels.get(current_level_str, 0)
        recommended_level = ml_levels.get(str(recommended_value), 0)
        return current_level >= recommended_level

    elif setting_type == "string":
        return str(current_value).lower() == str(recommended_value).lower()

    return False


def _check_mlslider_compliance(current_value, detection_rec: str, prevention_rec: str) -> bool:
    """Check if an mlslider meets both detection and prevention recommendations.

    Args:
        current_value: Current mlslider value dict {"detection": ..., "prevention": ...}.
        detection_rec: Required detection level string (e.g. "Aggressive").
        prevention_rec: Required prevention level string (e.g. "Moderate+").

    Returns:
        True if both detection >= detection_rec and prevention >= prevention_rec.
    """
    if not isinstance(current_value, dict):
        return False

    ml_levels = BEST_PRACTICES.get("ml_levels", {})

    current_detection = ml_levels.get(current_value.get("detection", "DISABLED"), 0)
    current_prevention = ml_levels.get(current_value.get("prevention", "DISABLED"), 0)

    required_detection = ml_levels.get(detection_rec, 0)
    required_prevention = ml_levels.get(prevention_rec, 0)

    return current_detection >= required_detection and current_prevention >= required_prevention


def calculate_compliance_score(policy_settings: Dict, platform: str) -> Dict:
    """
    Calculate compliance score for a policy against best practices.

    Args:
        policy_settings: Dictionary of current policy settings {setting_id: value}
        platform: "Windows", "Mac", or "Linux"

    Returns:
        {
            "compliance_percentage": 85.5,
            "total_checks": 100,
            "compliant_count": 85,
            "non_compliant_count": 15,
            "critical_issues": 2,
            "high_issues": 5,
            "medium_issues": 8,
            "compliant_settings": [...],
            "non_compliant_settings": [
                {
                    "setting_id": "SensorTamperingProtection",
                    "current": False,
                    "recommended": "Enabled",
                    "severity": "CRITICAL",
                    "description": "Block processes with suspicious behavior"
                }
            ]
        }
    """
    # Handle list format (sometimes Falcon API returns settings as a list)
    if isinstance(policy_settings, list):
        policy_settings = policy_settings[0] if policy_settings else {}

    if not isinstance(policy_settings, dict):
        policy_settings = {}

    platform_best_practices = BEST_PRACTICES.get("platforms", {}).get(platform, {})

    if not platform_best_practices:
        return {
            "compliance_percentage": 0,
            "total_checks": 0,
            "compliant_count": 0,
            "non_compliant_count": 0,
            "critical_issues": 0,
            "high_issues": 0,
            "medium_issues": 0,
            "compliant_settings": [],
            "non_compliant_settings": [],
            "error": f"No best practices defined for platform: {platform}"
        }

    compliant_settings = []
    non_compliant_settings = []
    severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}

    # Iterate through all best practice settings for this platform
    for setting_id, setting_info in platform_best_practices.items():
        if not isinstance(setting_info, dict):
            continue

        severity = setting_info.get("severity", "MEDIUM")
        description = setting_info.get("description", "")
        current_value = policy_settings.get(setting_id)

        # --- mlslider with separate detection/prevention recommendations ---
        if "detection_recommendation" in setting_info:
            detection_rec = setting_info["detection_recommendation"]
            prevention_rec = setting_info["prevention_recommendation"]
            is_compliant = _check_mlslider_compliance(current_value, detection_rec, prevention_rec)
            recommended_display = f"Detection: {detection_rec}, Prevention: {prevention_rec}"
        else:
            # --- toggle or single-level recommendation ---
            recommendation = setting_info.get("recommendation")
            if recommendation in ["Enabled", "Disabled"]:
                setting_type = "boolean"
            elif recommendation in BEST_PRACTICES.get("ml_levels", {}):
                setting_type = "ml_level"
            else:
                setting_type = "string"
            is_compliant = compare_setting(current_value, recommendation, setting_type)
            recommended_display = recommendation

        setting_result = {
            "setting_id": setting_id,
            "current": current_value,
            "recommended": recommended_display,
            "severity": severity,
            "description": description
        }

        if is_compliant:
            compliant_settings.append(setting_result)
        else:
            non_compliant_settings.append(setting_result)
            if severity in severity_counts:
                severity_counts[severity] += 1

    total_checks = len(compliant_settings) + len(non_compliant_settings)
    compliant_count = len(compliant_settings)
    non_compliant_count = len(non_compliant_settings)

    compliance_percentage = (compliant_count / total_checks * 100) if total_checks > 0 else 0

    return {
        "compliance_percentage": round(compliance_percentage, 1),
        "total_checks": total_checks,
        "compliant_count": compliant_count,
        "non_compliant_count": non_compliant_count,
        "critical_issues": severity_counts["CRITICAL"],
        "high_issues": severity_counts["HIGH"],
        "medium_issues": severity_counts["MEDIUM"],
        "low_issues": severity_counts["LOW"],
        "compliant_settings": compliant_settings,
        "non_compliant_settings": non_compliant_settings
    }


def get_best_practices_summary() -> Dict:
    """
    Get metadata about the loaded best practices.
    
    Returns:
        {
            "version": "2024.08",
            "source": "CrowdStrike Prevention Policy Best Practices",
            "platforms": ["Windows", "Mac", "Linux"],
            "total_settings": {
                "Windows": 100,
                "Mac": 30,
                "Linux": 25
            }
        }
    """
    platforms = list(BEST_PRACTICES.get("platforms", {}).keys())
    total_settings = {}
    
    for platform, categories in BEST_PRACTICES.get("platforms", {}).items():
        count = 0
        for category_settings in categories.values():
            if isinstance(category_settings, dict):
                count += len(category_settings)
        total_settings[platform] = count
    
    return {
        "version": BEST_PRACTICES.get("version", "unknown"),
        "source": BEST_PRACTICES.get("source", ""),
        "platforms": platforms,
        "total_settings": total_settings
    }


def generate_remediation_plan(non_compliant_settings: List[Dict]) -> List[Dict]:
    """
    Generate a prioritized remediation plan from non-compliant settings.
    
    Args:
        non_compliant_settings: List of non-compliant settings from calculate_compliance_score
    
    Returns:
        List of remediation actions sorted by priority (CRITICAL first)
    """
    severity_priority = {"CRITICAL": 1, "HIGH": 2, "MEDIUM": 3, "LOW": 4}
    
    # Sort by severity
    sorted_settings = sorted(
        non_compliant_settings,
        key=lambda x: severity_priority.get(x.get("severity", "LOW"), 5)
    )
    
    remediation_plan = []
    for idx, setting in enumerate(sorted_settings, 1):
        remediation_plan.append({
            "priority": idx,
            "severity": setting.get("severity"),
            "category": setting.get("category"),
            "setting": setting.get("setting"),
            "action": f"Change from '{setting.get('current')}' to '{setting.get('recommended')}'",
            "description": setting.get("description"),
            "recommended_value": setting.get("recommended")
        })
    
    return remediation_plan
