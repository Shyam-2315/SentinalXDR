from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEMO_TAG = "sentinelxdr-demo"
DEMO_EMAIL = os.environ.get("SENTINELXDR_DEMO_EMAIL", "demo@sentinelxdrdemo.com")
DEMO_PASSWORD = os.environ.get("SENTINELXDR_DEMO_PASSWORD", "SentinelXDR-Demo-2026!")
DEMO_DISPLAY_NAME = "SentinelXDR Demo Analyst"
DEMO_ORGANIZATION = "SentinelXDR Demo Organization"
DEMO_AGENT_NAME = "sentinelxdr-demo-linux-agent"
DEMO_AGENT_HOSTNAME = "demo-linux-target"
DEFAULT_API_BASE_URL = os.environ.get("SENTINELXDR_API_BASE_URL", "http://localhost:8000")


class DemoError(RuntimeError):
    pass


def utc_timestamp() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def request_json(
    api_base_url: str,
    method: str,
    path: str,
    *,
    payload: dict[str, Any] | None = None,
    token: str | None = None,
    agent_key: str | None = None,
) -> dict[str, Any]:
    headers = {"Accept": "application/json"}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if agent_key:
        headers["X-Agent-Key"] = agent_key

    request = Request(
        f"{api_base_url.rstrip('/')}{path}",
        data=data,
        headers=headers,
        method=method,
    )
    try:
        with urlopen(request, timeout=20) as response:
            raw = response.read().decode("utf-8")
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise DemoError(f"HTTP {exc.code} {method} {path}: {body}") from exc
    except URLError as exc:
        raise DemoError(f"Unable to reach backend at {api_base_url}: {exc.reason}") from exc
    return json.loads(raw) if raw else {}


def login(api_base_url: str, email: str = DEMO_EMAIL, password: str = DEMO_PASSWORD) -> dict[str, Any]:
    return request_json(
        api_base_url,
        "POST",
        "/api/auth/login",
        payload={"email": email, "password": password},
    )


def register_demo_user(api_base_url: str) -> dict[str, Any]:
    return request_json(
        api_base_url,
        "POST",
        "/api/auth/register",
        payload={
            "email": DEMO_EMAIL,
            "password": DEMO_PASSWORD,
            "display_name": DEMO_DISPLAY_NAME,
            "organization_name": DEMO_ORGANIZATION,
        },
    )


def get_or_create_demo_auth(api_base_url: str) -> dict[str, Any]:
    try:
        return login(api_base_url)
    except DemoError as login_error:
        if "401" not in str(login_error):
            raise
    try:
        return register_demo_user(api_base_url)
    except DemoError as register_error:
        if "409" not in str(register_error):
            raise
        return login(api_base_url)


def demo_event_batch() -> list[dict[str, Any]]:
    timestamp = utc_timestamp()
    common_tags = [DEMO_TAG, "lab", "simulation", "showcase"]
    return [
        {
            "event_type": "network_scan",
            "severity": "medium",
            "source": "network",
            "title": "Demo reconnaissance scan signal",
            "description": "Safe demo telemetry: nmap-like reconnaissance signal.",
            "raw_event": {
                "tool": "nmap-demo-simulation",
                "simulation": True,
                "demo": True,
                "marker": DEMO_TAG,
            },
            "normalized_fields": {
                "source.ip": "192.0.2.10",
                "destination.ip": "192.0.2.20",
            },
            "tags": common_tags + ["recon"],
            "timestamp": timestamp,
        },
        {
            "event_type": "auth_failure",
            "severity": "medium",
            "source": "linux",
            "title": "Demo SSH brute force signal",
            "description": "Safe demo telemetry: repeated failed SSH authentication.",
            "raw_event": {
                "message": "Failed password for invalid user demo from 192.0.2.10 port 50221 ssh2 [DEMO ONLY]",
                "simulation": True,
                "demo": True,
                "marker": DEMO_TAG,
            },
            "normalized_fields": {
                "auth.user": "demo",
                "auth.service": "ssh",
                "auth.outcome": "failure",
                "source.ip": "192.0.2.10",
            },
            "tags": common_tags + ["credential-access"],
            "timestamp": timestamp,
        },
        {
            "event_type": "process_start",
            "severity": "info",
            "source": "windows",
            "title": "Demo encoded PowerShell signal",
            "description": "Safe demo telemetry: encoded PowerShell command marker only.",
            "raw_event": {
                "process_name": "powershell.exe",
                "simulation": True,
                "demo": True,
                "marker": DEMO_TAG,
            },
            "normalized_fields": {
                "command_line": "powershell.exe -NoProfile -enc DEMO_ONLY_NO_PAYLOAD",
                "process.command_line": "powershell.exe -NoProfile -enc DEMO_ONLY_NO_PAYLOAD",
            },
            "tags": common_tags + ["execution", "powershell"],
            "timestamp": timestamp,
        },
        {
            "event_type": "process_start",
            "severity": "info",
            "source": "linux",
            "title": "Demo base64 command signal",
            "description": "Safe demo telemetry: base64 decode pattern marker only.",
            "raw_event": {
                "process_name": "bash",
                "simulation": True,
                "demo": True,
                "marker": DEMO_TAG,
            },
            "normalized_fields": {
                "command_line": "echo DEMO_ONLY | base64 -d",
                "process.command_line": "echo DEMO_ONLY | base64 -d",
            },
            "tags": common_tags + ["execution", "base64"],
            "timestamp": timestamp,
        },
        {
            "event_type": "file_write",
            "severity": "high",
            "source": "linux",
            "title": "Demo cron persistence signal",
            "description": "Safe demo telemetry: cron write indicator without modifying files.",
            "raw_event": {
                "path": "/etc/cron.d/sentinelxdr-demo",
                "operation": "write",
                "simulation": True,
                "demo": True,
                "marker": DEMO_TAG,
            },
            "normalized_fields": {
                "file_path": "/etc/cron.d/sentinelxdr-demo",
                "file.path": "/etc/cron.d/sentinelxdr-demo",
                "operation": "write",
            },
            "tags": common_tags + ["persistence", "cron"],
            "timestamp": timestamp,
        },
        {
            "event_type": "network_connection",
            "severity": "high",
            "source": "network",
            "title": "Demo large outbound transfer signal",
            "description": "Safe demo telemetry: no data transfer occurred.",
            "raw_event": {
                "destination_ip": "198.51.100.25",
                "bytes_sent": 250000000,
                "simulation": True,
                "demo": True,
                "marker": DEMO_TAG,
            },
            "normalized_fields": {
                "direction": "outbound",
                "bytes_sent": 250000000,
                "destination.ip": "198.51.100.25",
            },
            "tags": common_tags + ["exfiltration"],
            "timestamp": timestamp,
        },
    ]


def count_items(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key)
    return len(value) if isinstance(value, list) else 0
