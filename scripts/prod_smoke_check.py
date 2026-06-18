#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen


class SmokeError(RuntimeError):
    pass


@dataclass(frozen=True)
class HttpResult:
    status: int
    body: str
    content_type: str


Check = tuple[str, Callable[[], None]]


def normalize_base_url(base_url: str) -> str:
    parsed = urlsplit(base_url.rstrip("/"))
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", "")).rstrip("/")


def request(base_url: str, path: str, *, method: str = "GET") -> HttpResult:
    normalized_path = path if path.startswith("/") else f"/{path}"
    req = Request(f"{normalize_base_url(base_url)}{normalized_path}", method=method)
    req.add_header("Accept", "application/json,text/html;q=0.9,*/*;q=0.8")
    try:
        with urlopen(req, timeout=20) as response:
            body = response.read().decode("utf-8", errors="replace")
            return HttpResult(response.status, body, response.headers.get("content-type", ""))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return HttpResult(exc.code, body, exc.headers.get("content-type", ""))
    except URLError as exc:
        raise SmokeError(f"Unable to reach {normalize_base_url(base_url)}: {exc.reason}") from exc


def require_status(result: HttpResult, expected: set[int], label: str) -> None:
    if result.status not in expected:
        body = result.body[:300].replace("\n", " ")
        raise SmokeError(f"{label} returned HTTP {result.status}: {body}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run SentinelXDR production smoke checks.")
    parser.add_argument("--base-url", default="http://localhost", help="Public nginx URL.")
    parser.add_argument(
        "--openapi",
        choices=("auto", "enabled", "disabled"),
        default="auto",
        help="Whether /openapi.json is expected to be available.",
    )
    args = parser.parse_args()

    base_url = normalize_base_url(args.base_url)

    def frontend_reachable() -> None:
        result = request(base_url, "/")
        require_status(result, {200}, "frontend")
        if "text/html" not in result.content_type:
            raise SmokeError(f"frontend returned unexpected content type: {result.content_type}")

    def backend_live() -> None:
        result = request(base_url, "/health/live")
        require_status(result, {200}, "backend live")

    def backend_ready() -> None:
        result = request(base_url, "/health/ready")
        require_status(result, {200}, "backend ready")

    def auth_route_exists() -> None:
        result = request(base_url, "/api/auth/login", method="POST")
        require_status(result, {400, 422}, "auth route")

    def dashboard_requires_auth() -> None:
        result = request(base_url, "/api/dashboard/summary")
        require_status(result, {401, 403}, "dashboard route")

    def openapi_availability() -> None:
        result = request(base_url, "/openapi.json")
        if args.openapi == "enabled":
            require_status(result, {200}, "OpenAPI")
        elif args.openapi == "disabled":
            require_status(result, {404}, "OpenAPI")
        else:
            require_status(result, {200, 404}, "OpenAPI")

    checks: list[Check] = [
        ("frontend reachable", frontend_reachable),
        ("backend live", backend_live),
        ("backend ready", backend_ready),
        ("auth route exists", auth_route_exists),
        ("dashboard requires auth", dashboard_requires_auth),
        ("OpenAPI availability", openapi_availability),
    ]

    failed = False
    for label, check in checks:
        try:
            check()
        except SmokeError as exc:
            failed = True
            print(f"FAIL {label}: {exc}")
        else:
            print(f"PASS {label}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
