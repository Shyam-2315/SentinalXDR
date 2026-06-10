#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections.abc import Callable

try:
    from .demo_common import DEFAULT_API_BASE_URL, DemoError, get_or_create_demo_auth, request_json
except ImportError:
    from demo_common import DEFAULT_API_BASE_URL, DemoError, get_or_create_demo_auth, request_json


Check = tuple[str, Callable[[], None]]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run SentinelXDR demo smoke checks.")
    parser.add_argument("--api-base-url", default=DEFAULT_API_BASE_URL)
    args = parser.parse_args()

    token_holder: dict[str, str] = {}

    def backend_live() -> None:
        request_json(args.api_base_url, "GET", "/health/live")

    def backend_ready() -> None:
        request_json(args.api_base_url, "GET", "/health/ready")

    def auth_works() -> None:
        auth = get_or_create_demo_auth(args.api_base_url)
        token_holder["token"] = auth["access_token"]

    def authed_get(path: str) -> None:
        token = token_holder.get("token")
        if not token:
            raise DemoError("Auth token unavailable.")
        request_json(args.api_base_url, "GET", path, token=token)

    checks: list[Check] = [
        ("backend live", backend_live),
        ("backend ready", backend_ready),
        ("auth works", auth_works),
        ("dashboard summary works", lambda: authed_get("/api/dashboard/summary")),
        ("recent alerts works", lambda: authed_get("/api/dashboard/recent-alerts?limit=5")),
        ("recent incidents works", lambda: authed_get("/api/dashboard/recent-incidents?limit=5")),
        ("attack chains works", lambda: authed_get("/api/attack-chains?limit=5")),
    ]

    failed = False
    for label, check in checks:
        try:
            check()
        except DemoError as exc:
            failed = True
            print(f"FAIL {label}: {exc}")
        else:
            print(f"PASS {label}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
