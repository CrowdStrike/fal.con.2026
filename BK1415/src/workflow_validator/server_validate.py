"""Server-side validation via Falcon Fusion validate_only=true endpoint.

This is an opt-in second gate on top of the local rule-based validator.
It catches trigger-type-specific variable references and other errors
that only the server can see (e.g. ${Trigger.CompositeID} on an NG-SIEM
Detection trigger, where the valid reference is ${Trigger.Detection.DetectionID}).

Usage pattern:
    ok, errors, summary = server_validate_only(yaml_text)
    if not ok:
        for e in errors: print(e['code'], e['message'])

Requires env: FALCON_CLIENT_ID, FALCON_CLIENT_SECRET, FALCON_BASE_URL.
"""
from __future__ import annotations

import os
from typing import Tuple, List, Dict, Any


def _require_env() -> Tuple[str, str, str]:
    cid = os.environ.get('FALCON_CLIENT_ID')
    sec = os.environ.get('FALCON_CLIENT_SECRET')
    url = os.environ.get('FALCON_BASE_URL')
    missing = [k for k, v in (('FALCON_CLIENT_ID', cid),
                              ('FALCON_CLIENT_SECRET', sec),
                              ('FALCON_BASE_URL', url)) if not v]
    if missing:
        raise RuntimeError(
            f"--server-validate requires env vars: {', '.join(missing)}. "
            "Load from .env (dotenv) or export them, then re-run."
        )
    return cid, sec, url.rstrip('/')


def _get_bearer_token(cid: str, sec: str, base_url: str) -> str:
    from falconpy import OAuth2
    auth = OAuth2(client_id=cid, client_secret=sec, base_url=base_url)
    tok_resp = auth.token()
    if tok_resp.get('status_code') != 201:
        raise RuntimeError(
            f"OAuth2 token request failed: {tok_resp.get('status_code')} {tok_resp.get('body')}"
        )
    return tok_resp['body']['access_token']


def server_validate_only(yaml_text: str, timeout: int = 30
                         ) -> Tuple[bool, List[Dict[str, Any]], str]:
    """POST raw YAML to validate_only=true.

    Returns (ok, errors, http_summary). `ok` is True only if HTTP 200 and
    the response `errors` array is empty.
    """
    try:
        import requests
    except ImportError as e:
        raise RuntimeError("'requests' package is required for --server-validate") from e

    cid, sec, base_url = _require_env()
    token = _get_bearer_token(cid, sec, base_url)
    url = f"{base_url}/workflows/entities/definitions/v1?validate_only=true"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/yaml",
        "Accept": "application/json",
    }
    resp = requests.post(url, headers=headers, data=yaml_text.encode('utf-8'), timeout=timeout)
    summary = f"HTTP {resp.status_code}"
    try:
        body = resp.json()
    except Exception:
        return False, [{"code": resp.status_code,
                        "message": f"Non-JSON response: {resp.text[:400]}"}], summary

    errors = body.get('errors') or []
    if resp.status_code == 200 and not errors:
        return True, [], summary
    return False, errors, summary
