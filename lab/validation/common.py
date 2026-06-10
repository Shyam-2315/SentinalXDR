from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

LAB_ROOT = Path(__file__).resolve().parents[1]
METADATA_PATH = LAB_ROOT / "scenario_metadata.json"


class ValidationError(RuntimeError):
    pass


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--api-base-url",
        default=os.environ.get("SENTINELXDR_API_BASE_URL", "http://localhost:8000"),
        help="SentinelXDR backend URL. Defaults to SENTINELXDR_API_BASE_URL or localhost.",
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("SENTINELXDR_TOKEN"),
        help="Bearer token. Defaults to SENTINELXDR_TOKEN.",
    )
    parser.add_argument(
        "--email",
        default=os.environ.get("SENTINELXDR_EMAIL"),
        help="Login email. Defaults to SENTINELXDR_EMAIL.",
    )
    parser.add_argument(
        "--password",
        default=os.environ.get("SENTINELXDR_PASSWORD"),
        help="Login password. Defaults to SENTINELXDR_PASSWORD.",
    )
    parser.add_argument(
        "--scenario",
        choices=[item["id"] for item in load_metadata()["scenarios"]],
        help="Scenario metadata to validate against.",
    )
    parser.add_argument("--limit", type=int, default=100, help="Maximum API items to inspect.")


def load_metadata(path: Path = METADATA_PATH) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as metadata_file:
        return json.load(metadata_file)


def scenario_expectations(scenario_id: str | None) -> dict[str, list[str]]:
    metadata = load_metadata()
    if scenario_id is None:
        scenarios = metadata["scenarios"]
        return {
            "expected_rules": unique(
                rule for scenario in scenarios for rule in scenario["expected_rules"]
            ),
            "expected_mitre_techniques": unique(
                technique
                for scenario in scenarios
                for technique in scenario["expected_mitre_techniques"]
            ),
            "expected_tactics": unique(
                tactic for scenario in scenarios for tactic in scenario["expected_tactics"]
            ),
        }

    for scenario in metadata["scenarios"]:
        if scenario["id"] == scenario_id:
            return {
                "expected_rules": scenario["expected_rules"],
                "expected_mitre_techniques": scenario["expected_mitre_techniques"],
                "expected_tactics": scenario["expected_tactics"],
            }
    raise ValidationError(f"Unknown scenario: {scenario_id}")


def get_token(api_base_url: str, token: str | None, email: str | None, password: str | None) -> str:
    if token:
        return token
    if not email or not password:
        raise ValidationError(
            "Provide SENTINELXDR_TOKEN or both SENTINELXDR_EMAIL and SENTINELXDR_PASSWORD."
        )
    payload = {"email": email, "password": password}
    response = post_json(api_base_url, "/api/auth/login", payload, token=None)
    access_token = response.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise ValidationError("Login response did not include access_token.")
    return access_token


def get_json(api_base_url: str, path: str, token: str) -> dict[str, Any]:
    request = Request(
        f"{api_base_url.rstrip('/')}{path}",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        method="GET",
    )
    return _send_json_request(request)


def post_json(
    api_base_url: str,
    path: str,
    payload: dict[str, Any],
    token: str | None,
) -> dict[str, Any]:
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(
        f"{api_base_url.rstrip('/')}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    return _send_json_request(request)


def _send_json_request(request: Request) -> dict[str, Any]:
    try:
        with urlopen(request, timeout=15) as response:
            raw = response.read().decode("utf-8")
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise ValidationError(f"HTTP {exc.code} from {request.full_url}: {body}") from exc
    except URLError as exc:
        raise ValidationError(f"Unable to reach {request.full_url}: {exc.reason}") from exc
    if not raw:
        return {}
    return json.loads(raw)


def missing_values(actual: list[str], expected: list[str]) -> list[str]:
    actual_set = set(actual)
    return [item for item in expected if item not in actual_set]


def collect_field_values(items: list[dict[str, Any]], field: str) -> list[str]:
    values: list[str] = []
    for item in items:
        value = item.get(field)
        if isinstance(value, str):
            values.append(value)
        elif isinstance(value, list):
            values.extend(str(entry) for entry in value)
    return unique(values)


def unique(values: Any) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value)
        if text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def pass_message(message: str) -> None:
    print(f"PASS: {message}")


def resolve_token(args: argparse.Namespace) -> str:
    return get_token(args.api_base_url, args.token, args.email, args.password)
