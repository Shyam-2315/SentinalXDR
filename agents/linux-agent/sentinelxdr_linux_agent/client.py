from __future__ import annotations

import logging
import time
from typing import Any

import requests

LOGGER = logging.getLogger(__name__)


class AgentClientError(RuntimeError):
    pass


class AgentClient:
    def __init__(
        self,
        *,
        api_base_url: str,
        agent_api_key: str,
        timeout_seconds: float,
        max_retries: int,
        backoff_seconds: float,
    ) -> None:
        self.api_base_url = api_base_url.rstrip("/")
        self.agent_api_key = agent_api_key
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self.session = requests.Session()

    def send_heartbeat(self, *, agent_version: str, ip_address: str | None) -> dict[str, Any]:
        return self._post(
            "/api/agents/heartbeat",
            {"agent_version": agent_version, "ip_address": ip_address},
        )

    def send_events(self, events: list[dict[str, Any]]) -> dict[str, Any]:
        return self._post("/api/events/ingest", {"events": events})

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.api_base_url}{path}"
        headers = {
            "X-Agent-Key": self.agent_api_key,
            "Content-Type": "application/json",
            "User-Agent": "sentinelxdr-linux-agent/0.1.0",
        }
        attempts = self.max_retries + 1
        last_error: Exception | None = None

        for attempt in range(1, attempts + 1):
            try:
                response = self.session.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=self.timeout_seconds,
                )
                if 500 <= response.status_code < 600:
                    raise AgentClientError(f"server error {response.status_code}: {response.text}")
                if response.status_code >= 400:
                    raise AgentClientError(f"request failed {response.status_code}: {response.text}")
                if not response.content:
                    return {}
                return response.json()
            except (requests.RequestException, AgentClientError) as exc:
                last_error = exc
                if isinstance(exc, AgentClientError) and "request failed" in str(exc):
                    raise
                if attempt >= attempts:
                    break
                sleep_for = self.backoff_seconds * (2 ** (attempt - 1))
                LOGGER.warning(
                    "POST %s failed on attempt %s/%s: %s; retrying in %.1fs",
                    path,
                    attempt,
                    attempts,
                    exc,
                    sleep_for,
                )
                time.sleep(sleep_for)

        raise AgentClientError(f"POST {path} failed after {attempts} attempts: {last_error}")
