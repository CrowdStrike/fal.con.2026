from datetime import datetime
from falconpy import PreventionPolicies, ResponsePolicies, FirewallPolicies, Hosts
from crowdstrike.foundry.function import Function, Request, Response, APIError
from logging import Logger
from typing import Dict, List, Optional
from best_practices import (
    BEST_PRACTICES,
    compare_setting,
    calculate_compliance_score,
    get_best_practices_summary,
    generate_remediation_plan
)

func = Function.instance()


def extract_settings_from_policy_as_dict(policy: Dict, logger: Logger) -> Dict:
    """
    Extract settings from a policy as a flat dictionary.

    Args:
        policy: Full policy object from Falcon API

    Returns:
        {setting_id: value} flat dictionary
    """
    settings_dict = {}

    prevention_settings = policy.get('prevention_settings', [])

    if not isinstance(prevention_settings, list):
        logger.warning(f"prevention_settings is not a list: {type(prevention_settings)}")
        return {}

    # Iterate through categories
    for category in prevention_settings:
        if not isinstance(category, dict):
            continue

        category_settings = category.get('settings', [])

        if not isinstance(category_settings, list):
            continue

        # Iterate through settings in this category
        for setting in category_settings:
            if not isinstance(setting, dict):
                continue

            setting_id = setting.get('id')
            setting_type = setting.get('type')  # 'toggle' or 'mlslider'
            setting_value_obj = setting.get('value', {})

            if not setting_id:
                continue

            # Extract the actual value based on type
            if setting_type == 'toggle':
                # For toggles: {"enabled": true, "configured": true}
                actual_value = setting_value_obj.get('enabled')
            elif setting_type == 'mlslider':
                # For mlsliders: {"detection": "AGGRESSIVE", "prevention": "MODERATE"}
                actual_value = setting_value_obj
            else:
                # Unknown type, store as-is
                actual_value = setting_value_obj

            settings_dict[setting_id] = actual_value

    return settings_dict


def get_sensor_policy_coverage(hosts_api: Hosts, prevention_policies: List[Dict], logger: Logger) -> Dict:
    """
    Calculate how many sensors have each policy applied.
    Returns: {policy_id: sensor_count}
    """
    try:
        logger.info("Fetching sensor-to-policy mappings...")

        # Query all hosts
        hosts_response = hosts_api.query_devices_by_filter(limit=5000)

        if hosts_response["status_code"] != 200:
            logger.warning("Failed to query hosts for coverage calculation")
            return {}

        device_ids = hosts_response.get("body", {}).get("resources", [])

        if not device_ids:
            logger.warning("No devices found")
            return {}

        logger.info(f"Found {len(device_ids)} devices")

        # Get device details including policy assignments
        details_response = hosts_api.get_device_details(ids=device_ids)

        if details_response["status_code"] != 200:
            logger.warning("Failed to get device details")
            return {}

        devices = details_response.get("body", {}).get("resources", [])

        # Count sensors per policy and total sensors per platform
        policy_sensor_count = {}
        platform_totals = {}
        rfm_count = 0

        for device in devices:
            platform = device.get("platform_name", "Unknown")
            prevention_policy_id = device.get("device_policies", {}).get("prevention", {}).get("policy_id")
            is_rfm = device.get("reduced_functionality_mode", "no") == "yes"

            # Track platform totals
            if platform not in platform_totals:
                platform_totals[platform] = 0
            platform_totals[platform] += 1

            # Track RFM
            if is_rfm:
                rfm_count += 1

            # Track policy assignments
            if prevention_policy_id:
                if prevention_policy_id not in policy_sensor_count:
                    policy_sensor_count[prevention_policy_id] = 0
                policy_sensor_count[prevention_policy_id] += 1

        logger.info(f"Policy coverage calculated: {len(policy_sensor_count)} policies assigned, {rfm_count} RFM sensors")
        logger.info(f"Platform totals: {platform_totals}")

        return {
            "policy_sensor_count": policy_sensor_count,
            "platform_totals": platform_totals,
            "total_sensors": len(devices),
            "rfm_sensors": rfm_count
        }

    except Exception as e:
        logger.error(f"Error calculating sensor coverage: {str(e)}")
        return {}


def calculate_policy_health_score(policies: List[Dict]) -> Dict:
    """Calculate detailed health score based on policy configuration."""
    if not policies:
        return {
            "score": 0,
            "status": "Critical",
            "enabled_count": 0,
            "total_count": 0,
            "enabled_percentage": 0
        }

    total = len(policies)
    enabled = sum(1 for p in policies if p.get('enabled', False))
    percentage = (enabled / total * 100) if total > 0 else 0

    # Determine status based on enabled percentage
    if percentage >= 90:
        status = "Excellent"
    elif percentage >= 80:
        status = "Good"
    elif percentage >= 70:
        status = "Fair"
    elif percentage >= 60:
        status = "Needs Attention"
    else:
        status = "Critical"

    return {
        "score": round(percentage, 2),
        "status": status,
        "enabled_count": enabled,
        "total_count": total,
        "enabled_percentage": round(percentage, 2)
    }


def analyze_prevention_settings(policy: Dict, logger: Logger, coverage_data: Dict = None) -> Dict:
    """
    Deep analysis of prevention policy settings against best practices.
    Returns detailed configuration breakdown with compliance status and coverage %.

    coverage_data: {
        'policy_sensor_count': {policy_id: sensor_count},
        'platform_totals': {platform: total_sensors},
        'total_sensors': int
    }
    """
    settings = policy.get('prevention_settings')
    platform = policy.get('platform_name', 'Windows')
    policy_id = policy.get('id')

    logger.info(f"Analyzing policy: {policy.get('name')} (Platform: {platform})")
    logger.info(f"Prevention settings keys: {list(settings.keys()) if isinstance(settings, dict) else 'Not a dict'}")

    # Handle Falcon API structure: prevention_settings is a list of category objects
    # Each category has: {"name": "Category Name", "settings": [{id, name, type, value}, ...]}
    if isinstance(settings, list):
        logger.info(f"Prevention settings is a list with {len(settings)} categories")

        # Convert to flat dict: {setting_id: value}
        settings_dict = {}

        for category in settings:
            if not isinstance(category, dict):
                continue

            category_name = category.get('name', 'Unknown')
            category_settings = category.get('settings', [])

            logger.info(f"Processing category: {category_name} with {len(category_settings)} settings")

            for setting in category_settings:
                if not isinstance(setting, dict):
                    continue

                setting_id = setting.get('id')
                setting_type = setting.get('type')  # 'toggle' or 'mlslider'
                setting_value_obj = setting.get('value', {})

                if not setting_id:
                    continue

                # Extract the actual value based on type
                if setting_type == 'toggle':
                    # For toggles, value is like: {"enabled": true, "configured": true}
                    # We care about "enabled"
                    actual_value = setting_value_obj.get('enabled')
                elif setting_type == 'mlslider':
                    # For mlsliders, value is like: {"detection": "AGGRESSIVE", "prevention": "MODERATE"}
                    # Store the whole dict so we can check both
                    actual_value = setting_value_obj
                else:
                    # Unknown type, store as-is
                    actual_value = setting_value_obj

                settings_dict[setting_id] = actual_value

                # Log first 5 settings for debugging
                if len(settings_dict) <= 5:
                    logger.info(f"  Setting: {setting_id} = {actual_value}")

        logger.info(f"Converted {len(settings)} categories to flat dict with {len(settings_dict)} setting IDs")
        logger.info(f"Sample setting IDs: {list(settings_dict.keys())[:10]}")
        settings = settings_dict

    if not settings or not isinstance(settings, dict):
        logger.warning(f"Unable to parse prevention settings for policy {policy.get('name')}")
        return {
            "issues": [],
            "recommendations": [],
            "risk_level": "UNKNOWN",
            "detailed_config": {},
            "compliance_percentage": 0,
            "total_checks": 0,
            "compliant_checks": 0,
            "critical_issues": 0,
            "high_issues": 0,
            "medium_issues": 0,
            "raw_settings_available": False,
            "coverage_percentage": 0,
            "sensor_count": 0
        }

    # Log all setting IDs we found
    logger.info(f"Final settings dict has {len(settings)} setting IDs: {list(settings.keys())}")

    # Use the new calculate_compliance_score function
    compliance_result = calculate_compliance_score(settings, platform)

    # Build issues list from non-compliant settings (top 10 most severe)
    issues = []
    recommendations = []

    for nc_setting in compliance_result.get("non_compliant_settings", [])[:10]:
        severity = nc_setting.get("severity", "MEDIUM")
        setting_id = nc_setting.get("setting_id", "")
        current = nc_setting.get("current", "")
        recommended = nc_setting.get("recommended", "")
        description = nc_setting.get("description", "")

        issue_text = f"[{severity}] {setting_id}: {current} (should be {recommended})"
        issues.append(issue_text)
        recommendations.append(f"Set {setting_id} to {recommended} - {description}")

    # Determine risk level
    compliance_pct = compliance_result.get("compliance_percentage", 0)
    critical_count = compliance_result.get("critical_issues", 0)
    high_count = compliance_result.get("high_issues", 0)

    if critical_count > 5 or compliance_pct < 50:
        risk_level = "CRITICAL"
    elif critical_count > 0 or high_count > 10 or compliance_pct < 75:
        risk_level = "HIGH"
    elif high_count > 0 or compliance_pct < 90:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    # Calculate coverage percentage (how many sensors have this policy)
    coverage_percentage = 0
    sensor_count = 0
    if coverage_data and policy_id:
        sensor_count = coverage_data.get('policy_sensor_count', {}).get(policy_id, 0)
        platform_total = coverage_data.get('platform_totals', {}).get(platform, 0)
        if platform_total > 0:
            coverage_percentage = (sensor_count / platform_total) * 100

    return {
        "issues": issues,
        "recommendations": recommendations[:10],
        "risk_level": risk_level,
        "compliance_percentage": compliance_result.get("compliance_percentage", 0),
        "total_checks": compliance_result.get("total_checks", 0),
        "compliant_checks": compliance_result.get("compliant_count", 0),
        "critical_issues": compliance_result.get("critical_issues", 0),
        "high_issues": compliance_result.get("high_issues", 0),
        "medium_issues": compliance_result.get("medium_issues", 0),
        "non_compliant_settings": compliance_result.get("non_compliant_settings", []),
        "raw_settings_available": True,
        "coverage_percentage": round(coverage_percentage, 1),
        "sensor_count": sensor_count
    }


@func.handler(method='POST', path='/api/health/check')
def on_post(request: Request, _config: Optional[Dict], logger: Logger) -> Response:
    """
    Comprehensive Falcon health check analyzing all policy types.
    Uses Foundry context-aware authentication - no credentials needed!
    """

    try:
        logger.info("Starting comprehensive health check...")

        # Initialize FalconPy clients with Foundry context authentication
        # No client_id/client_secret needed - Foundry handles this automatically!
        prevention_falcon = PreventionPolicies()
        response_falcon = ResponsePolicies()
        firewall_falcon = FirewallPolicies()  # Changed from FirewallManagement
        hosts_falcon = Hosts()

        # Fetch Prevention Policies
        logger.info("Fetching prevention policies...")
        prev_response = prevention_falcon.query_policies()
        prevention_policies = []

        if prev_response["status_code"] == 200 and prev_response["body"]["resources"]:
            policy_ids = prev_response["body"]["resources"]
            details_response = prevention_falcon.get_policies(ids=policy_ids)

            if details_response["status_code"] == 200:
                prevention_policies = details_response["body"]["resources"]
                logger.info(f"Found {len(prevention_policies)} prevention policies")

        # Calculate sensor-to-policy coverage
        coverage_data = get_sensor_policy_coverage(hosts_falcon, prevention_policies, logger)

        # Fetch Response Policies
        logger.info("Fetching response policies...")
        resp_response = response_falcon.query_policies()
        response_policies = []

        if resp_response["status_code"] == 200 and resp_response["body"]["resources"]:
            policy_ids = resp_response["body"]["resources"]
            details_response = response_falcon.get_policies(ids=policy_ids)

            if details_response["status_code"] == 200:
                response_policies = details_response["body"]["resources"]
                logger.info(f"Found {len(response_policies)} response policies")

        # Fetch Firewall Policies
        logger.info("Fetching firewall policies...")
        fw_response = firewall_falcon.query_policies()
        firewall_policies = []

        if fw_response["status_code"] == 200 and fw_response["body"]["resources"]:
            policy_ids = fw_response["body"]["resources"]
            details_response = firewall_falcon.get_policies(ids=policy_ids)

            if details_response["status_code"] == 200:
                firewall_policies = details_response["body"]["resources"]
                logger.info(f"Found {len(firewall_policies)} firewall policies")

        # Format and analyze policies
        formatted_prevention = []
        prevention_issues = []

        for policy in prevention_policies:
            analysis = analyze_prevention_settings(policy, logger, coverage_data)
            formatted_policy = {
                "id": policy.get("id"),
                "name": policy.get("name"),
                "platform": policy.get("platform_name"),
                "enabled": policy.get("enabled", False),
                "description": policy.get("description", ""),
                "analysis": analysis
            }
            formatted_prevention.append(formatted_policy)

            if analysis["risk_level"] != "LOW":
                prevention_issues.extend(analysis["issues"])

        formatted_response = []
        for policy in response_policies:
            formatted_response.append({
                "id": policy.get("id"),
                "name": policy.get("name"),
                "platform": policy.get("platform_name"),
                "enabled": policy.get("enabled", False),
                "description": policy.get("description", "")
            })

        formatted_firewall = []
        for policy in firewall_policies:
            formatted_firewall.append({
                "id": policy.get("id"),
                "name": policy.get("name"),
                "platform": policy.get("platform_name"),
                "enabled": policy.get("enabled", False),
                "description": policy.get("description", "")
            })

        # Calculate health scores for each category
        prevention_health = calculate_policy_health_score(formatted_prevention)
        response_health = calculate_policy_health_score(formatted_response)
        firewall_health = calculate_policy_health_score(formatted_firewall)

        total_policies = len(formatted_prevention) + len(formatted_response) + len(formatted_firewall)

        # --- 4-factor overall score ---
        # Factor 1 (40%): Average prevention policy compliance
        compliance_scores = [
            p["analysis"]["compliance_percentage"]
            for p in formatted_prevention if p.get("analysis")
        ]
        avg_compliance = sum(compliance_scores) / len(compliance_scores) if compliance_scores else 0

        # Factor 2 (25%): Sensor coverage — how many sensors have a prevention policy
        total_sensors = coverage_data.get("total_sensors", 0)
        covered_sensors = sum(coverage_data.get("policy_sensor_count", {}).values())
        sensor_coverage = (covered_sensors / total_sensors * 100) if total_sensors > 0 else 0

        # Factor 3 (20%): No sensors in Reduced Functionality Mode
        rfm_sensors = coverage_data.get("rfm_sensors", 0)
        rfm_free_pct = ((total_sensors - rfm_sensors) / total_sensors * 100) if total_sensors > 0 else 100

        # Factor 4 (15%): No critical/high compliance issues
        total_critical = sum(p["analysis"].get("critical_issues", 0) for p in formatted_prevention if p.get("analysis"))
        total_high = sum(p["analysis"].get("high_issues", 0) for p in formatted_prevention if p.get("analysis"))
        issues_score = max(0.0, 100 - (total_critical * 15) - (total_high * 5))

        overall_score = (
            avg_compliance * 0.40 +
            sensor_coverage * 0.25 +
            rfm_free_pct * 0.20 +
            issues_score * 0.15
        ) if total_policies > 0 else 0

        # Determine overall status
        if overall_score >= 90:
            overall_status = "Excellent"
        elif overall_score >= 80:
            overall_status = "Good"
        elif overall_score >= 70:
            overall_status = "Fair"
        elif overall_score >= 60:
            overall_status = "Needs Attention"
        else:
            overall_status = "Critical"

        # Build comprehensive response
        result = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "overall_score": round(overall_score, 2),
            "overall_status": overall_status,
            "total_policies": total_policies,
            "score_breakdown": {
                "prevention_compliance": round(avg_compliance, 1),
                "sensor_coverage": round(sensor_coverage, 1),
                "rfm_free": round(rfm_free_pct, 1),
                "issues_score": round(issues_score, 1),
            },
            "prevention": {
                "health": prevention_health,
                "policies": formatted_prevention,
                "issues": prevention_issues
            },
            "response": {
                "health": response_health,
                "policies": formatted_response
            },
            "firewall": {
                "health": firewall_health,
                "policies": formatted_firewall
            },
            "summary": {
                "critical_issues": len(prevention_issues),
                "total_enabled": (
                    prevention_health["enabled_count"] +
                    response_health["enabled_count"] +
                    firewall_health["enabled_count"]
                ),
                "total_sensors": total_sensors,
                "rfm_sensors": rfm_sensors,
                "covered_sensors": covered_sensors,
                "platform_breakdown": coverage_data.get("platform_totals", {})
            },
            "message": f"Health check completed. Overall status: {overall_status}"
        }

        logger.info(f"Health check complete. Score: {overall_score:.2f}")
        return Response(body=result, code=200)

    except Exception as e:
        return Response(
            code=500,
            errors=[APIError(code=500, message=f"Error performing health check: {str(e)}")]
        )


@func.handler(method='POST', path='/api/policy/apply-best-practices')
def apply_best_practices(request: Request, _config: Optional[Dict], logger: Logger) -> Response:
    """
    Apply CrowdStrike best practice recommendations to a prevention policy.

    Request body:
    {
        "policy_id": "abc123...",
        "dry_run": false,  // Optional: if true, returns changes without applying
        "settings_to_apply": ["all"]  // Optional: specific categories or "all"
    }

    Returns:
    {
        "success": true,
        "policy_id": "abc123...",
        "policy_name": "Windows Production",
        "changes_made": 45,
        "changes": [
            {
                "category": "execution_blocking",
                "setting": "suspicious_process_prevention",
                "old_value": false,
                "new_value": true,
                "severity": "CRITICAL"
            }
        ],
        "compliance_before": 65.5,
        "compliance_after": 98.2
    }
    """
    try:
        body = request.body or {}
        policy_id = body.get('policy_id')
        dry_run = body.get('dry_run', False)
        settings_to_apply = body.get('settings_to_apply', ['all'])

        if not policy_id:
            return Response(
                code=400,
                errors=[APIError(code=400, message="policy_id is required")]
            )

        logger.info(f"Applying best practices to policy {policy_id} (dry_run={dry_run})")

        # Initialize FalconPy client
        prevention_falcon = PreventionPolicies()

        # Get current policy details
        policy_response = prevention_falcon.get_policies(ids=[policy_id])

        if policy_response["status_code"] != 200 or not policy_response["body"]["resources"]:
            return Response(
                code=404,
                errors=[APIError(code=404, message=f"Policy {policy_id} not found")]
            )

        current_policy = policy_response["body"]["resources"][0]
        platform = current_policy.get("platform_name", "Windows")
        policy_name = current_policy.get("name", "Unknown")
        prevention_settings = current_policy.get("prevention_settings", [])

        logger.info(f"Policy: {policy_name}, Platform: {platform}")

        # Extract current settings as flat dict
        current_settings = extract_settings_from_policy_as_dict(current_policy, logger)

        if not current_settings:
            return Response(
                code=400,
                errors=[APIError(code=400, message="Unable to parse policy settings")]
            )

        logger.info(f"Extracted {len(current_settings)} settings from policy")

        # Calculate compliance before changes
        compliance_before = calculate_compliance_score(current_settings, platform)

        # Get best practices for this platform
        platform_best_practices = BEST_PRACTICES.get("platforms", {}).get(platform, {})

        if not platform_best_practices:
            return Response(
                code=400,
                errors=[APIError(code=400, message=f"No best practices defined for platform: {platform}")]
            )

        # Build updated prevention_settings by applying best practices
        updated_prevention_settings = prevention_settings  # Work with original list structure
        changes = []

        # Iterate through best practices and apply changes
        for setting_id, setting_info in platform_best_practices.items():
            if not isinstance(setting_info, dict):
                continue

            severity = setting_info.get("severity", "MEDIUM")

            # Skip if user requested specific settings and this isn't one
            if 'all' not in settings_to_apply and setting_id not in settings_to_apply:
                continue

            # Get current value from flat dict
            current_value = current_settings.get(setting_id)

            # Determine if this is a split mlslider or a simple setting
            is_mlslider_split = "detection_recommendation" in setting_info

            if is_mlslider_split:
                from best_practices import _check_mlslider_compliance
                detection_rec = setting_info["detection_recommendation"]
                prevention_rec = setting_info["prevention_recommendation"]
                is_compliant = _check_mlslider_compliance(current_value, detection_rec, prevention_rec)
                display_rec = f"Detection:{detection_rec} Prevention:{prevention_rec}"
            else:
                recommendation = setting_info.get("recommendation")
                setting_type = "ml_level" if recommendation in BEST_PRACTICES.get("ml_levels", {}) else "boolean"
                is_compliant = compare_setting(current_value, recommendation, setting_type)
                display_rec = recommendation

            if not is_compliant:
                # Record the change
                changes.append({
                    "setting_id": setting_id,
                    "old_value": current_value,
                    "new_value": display_rec,
                    "severity": severity,
                    "description": setting_info.get("description", "")
                })

                # Apply the change to the prevention_settings list structure
                for category in updated_prevention_settings:
                    if not isinstance(category, dict):
                        continue

                    category_settings = category.get('settings', [])
                    for setting in category_settings:
                        if setting.get('id') == setting_id:
                            setting_type_field = setting.get('type')

                            if setting_type_field == 'toggle':
                                # For toggles: update 'enabled' field
                                if is_mlslider_split:
                                    pass  # toggles don't have split detection/prevention
                                else:
                                    rec = setting_info.get("recommendation")
                                    if rec == "Enabled":
                                        setting['value']['enabled'] = True
                                    elif rec == "Disabled":
                                        setting['value']['enabled'] = False

                            elif setting_type_field == 'mlslider':
                                # Valid Falcon API sensitivity strings:
                                # DISABLED, CAUTIOUS, MODERATE, AGGRESSIVE, EXTRA_AGGRESSIVE
                                # "MODERATE+" is a docs concept — the API doesn't accept it.
                                def _to_api_level(level: str) -> str:
                                    return {"MODERATE+": "MODERATE", "Moderate+": "MODERATE"}.get(level, level.upper())

                                if is_mlslider_split:
                                    setting['value']['detection'] = _to_api_level(detection_rec)
                                    setting['value']['prevention'] = _to_api_level(prevention_rec)
                                else:
                                    rec_level = _to_api_level(setting_info.get("recommendation", ""))
                                    setting['value']['detection'] = rec_level
                                    setting['value']['prevention'] = rec_level

                            logger.info(f"Updated {setting_id}: {current_value} -> {display_rec}")
                            break

        logger.info(f"Identified {len(changes)} changes needed")

        # Recalculate compliance after changes
        updated_flat = extract_settings_from_policy_as_dict(
            {"prevention_settings": updated_prevention_settings},
            logger
        )
        compliance_after = calculate_compliance_score(updated_flat, platform)

        result = {
            "success": True,
            "policy_id": policy_id,
            "policy_name": policy_name,
            "platform": platform,
            "dry_run": dry_run,
            "changes_made": len(changes),
            "changes": changes,
            "compliance_before": compliance_before.get("compliance_percentage", 0),
            "compliance_after": compliance_after.get("compliance_percentage", 0),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

        # Apply changes if not dry_run
        if not dry_run and changes:
            logger.info(f"Applying {len(changes)} changes to policy {policy_id}...")

            # Build a settings payload with ONLY the changed settings
            # This is what FalconPy expects - not the entire prevention_settings list
            settings_payload = []

            for change in changes:
                setting_id = change['setting_id']

                # Find the setting in the prevention_settings to get its current structure
                for category in updated_prevention_settings:
                    if not isinstance(category, dict):
                        continue

                    for setting in category.get('settings', []):
                        if setting.get('id') == setting_id:
                            # Add just this setting to the payload
                            settings_payload.append({
                                "id": setting_id,
                                "value": setting['value']
                            })
                            break

            logger.info(f"Settings payload: {settings_payload}")

            # Update the policy using FalconPy - send ONLY changed settings
            update_response = prevention_falcon.update_policies(
                id=policy_id,
                settings=settings_payload
            )

            if update_response["status_code"] != 200:
                logger.error(f"Failed to update policy: {update_response}")
                return Response(
                    code=500,
                    errors=[APIError(
                        code=500,
                        message=f"Failed to apply changes: {update_response.get('body', {}).get('errors', [])}"
                    )]
                )

            logger.info(f"Successfully applied best practices to policy {policy_id}")
            result["applied"] = True
        else:
            result["applied"] = False
            if dry_run:
                result["message"] = "Dry run - no changes applied"

        return Response(code=200, body=result)

    except Exception as e:
        logger.error(f"Error applying best practices: {str(e)}")
        return Response(
            code=500,
            errors=[APIError(code=500, message=f"Error applying best practices: {str(e)}")]
        )


@func.handler(method='POST', path='/api/policy/test-change')
def test_policy_change(request: Request, _config: Optional[Dict], logger: Logger) -> Response:
    """
    Simple test function to verify we can make policy changes.
    Makes ONE simple change: enables "EndUserNotifications" setting.

    Request body:
    {
        "policy_id": "abc123..."
    }

    Returns:
    {
        "success": true,
        "message": "Successfully enabled EndUserNotifications",
        "policy_id": "abc123...",
        "policy_name": "Windows Production",
        "setting_changed": "EndUserNotifications",
        "old_value": false,
        "new_value": true
    }
    """
    try:
        body = request.body or {}
        policy_id = body.get('policy_id')

        if not policy_id:
            return Response(
                code=400,
                errors=[APIError(code=400, message="policy_id is required")]
            )

        logger.info(f"TEST: Attempting to modify policy {policy_id}")

        # Initialize FalconPy client
        prevention_falcon = PreventionPolicies()

        # Get current policy
        policy_response = prevention_falcon.get_policies(ids=[policy_id])

        if policy_response["status_code"] != 200 or not policy_response["body"]["resources"]:
            return Response(
                code=404,
                errors=[APIError(code=404, message=f"Policy {policy_id} not found")]
            )

        current_policy = policy_response["body"]["resources"][0]
        policy_name = current_policy.get("name", "Unknown")
        prevention_settings = current_policy.get("prevention_settings", [])

        logger.info(f"TEST: Found policy '{policy_name}'")
        logger.info(f"TEST: Prevention settings type: {type(prevention_settings)}")

        # Find and enable EndUserNotifications
        setting_found = False
        old_value = None

        for category in prevention_settings:
            if not isinstance(category, dict):
                continue

            category_name = category.get('name', '')
            settings = category.get('settings', [])

            for setting in settings:
                if setting.get('id') == 'EndUserNotifications':
                    old_value = setting.get('value', {}).get('enabled', False)
                    # Enable it
                    setting['value']['enabled'] = True
                    setting_found = True
                    logger.info(f"TEST: Found EndUserNotifications in category '{category_name}'")
                    logger.info(f"TEST: Old value: {old_value}, New value: True")
                    break

            if setting_found:
                break

        if not setting_found:
            return Response(
                code=404,
                errors=[APIError(code=404, message="EndUserNotifications setting not found in policy")]
            )

        # Update the policy
        logger.info(f"TEST: Calling update_policies API...")
        logger.info(f"TEST: Policy ID: {policy_id}")
        logger.info(f"TEST: Prevention settings type: {type(prevention_settings)}")

        update_response = prevention_falcon.update_policies(
            body={
                "resources": [{
                    "id": policy_id,
                    "prevention_settings": prevention_settings
                }]
            }
        )

        logger.info(f"TEST: Update response status: {update_response.get('status_code')}")
        logger.info(f"TEST: Update response body: {update_response.get('body')}")
        logger.info(f"TEST: Update response errors: {update_response.get('errors')}")

        if update_response["status_code"] != 200:
            error_msg = update_response.get('body', {})
            errors = update_response.get('errors', [])
            logger.error(f"TEST: Failed to update policy. Status: {update_response['status_code']}")
            logger.error(f"TEST: Error body: {error_msg}")
            logger.error(f"TEST: Errors: {errors}")
            return Response(
                code=500,
                errors=[APIError(
                    code=500,
                    message=f"Failed to update policy (status {update_response['status_code']}): {error_msg} | {errors}"
                )]
            )

        logger.info(f"TEST: Successfully updated policy {policy_id}")

        return Response(
            code=200,
            body={
                "success": True,
                "message": "Successfully enabled EndUserNotifications",
                "policy_id": policy_id,
                "policy_name": policy_name,
                "setting_changed": "EndUserNotifications",
                "old_value": old_value,
                "new_value": True,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        )

    except Exception as e:
        logger.error(f"TEST: Error in test_policy_change: {str(e)}")
        return Response(
            code=500,
            errors=[APIError(code=500, message=f"Error: {str(e)}")]
        )


if __name__ == '__main__':
    func.run()
