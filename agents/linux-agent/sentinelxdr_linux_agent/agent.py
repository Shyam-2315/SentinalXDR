from __future__ import annotations

import json
import logging
import sys
import time
from typing import Protocol

from sentinelxdr_linux_agent.client import AgentClient
from sentinelxdr_linux_agent.collectors import LinuxTelemetryCollector, primary_ip_address
from sentinelxdr_linux_agent.config import AgentConfig
from sentinelxdr_linux_agent.events import Event, batch_events
from sentinelxdr_linux_agent.state import StateStore

LOGGER = logging.getLogger(__name__)


class Collector(Protocol):
    def collect(self) -> list[Event]:
        pass


class Client(Protocol):
    def send_heartbeat(self, *, agent_version: str, ip_address: str | None) -> dict[str, object]:
        pass

    def send_events(self, events: list[Event]) -> dict[str, object]:
        pass


class AgentRunner:
    def __init__(
        self,
        config: AgentConfig,
        *,
        collector: Collector | None = None,
        client: Client | None = None,
        state: StateStore | None = None,
    ) -> None:
        self.config = config
        self.state = state or StateStore(config.state_path)
        self.collector = collector or LinuxTelemetryCollector(config, self.state)
        self.client = client or AgentClient(
            api_base_url=config.api_base_url,
            agent_api_key=config.agent_api_key,
            timeout_seconds=config.timeout_seconds,
            max_retries=config.max_retries,
            backoff_seconds=config.backoff_seconds,
        )

    def run(self) -> None:
        self.state.load()
        if self.config.once:
            self.run_once()
            return

        LOGGER.info("Starting loop mode with interval=%ss", self.config.interval_seconds)
        while True:
            self.run_once()
            time.sleep(self.config.interval_seconds)

    def run_once(self) -> None:
        LOGGER.info("Collecting Linux telemetry")
        events = self.collector.collect()
        LOGGER.info("Collected %s events", len(events))

        if self.config.dry_run:
            self._print_dry_run(events)
            return

        self.client.send_heartbeat(
            agent_version=self.config.agent_version,
            ip_address=primary_ip_address(),
        )
        LOGGER.info("Heartbeat sent")

        for batch in batch_events(events, self.config.batch_size):
            response = self.client.send_events(batch)
            LOGGER.info("Sent event batch size=%s response=%s", len(batch), response)

        self.state.save()

    def _print_dry_run(self, events: list[Event]) -> None:
        payload = {"events": events}
        json.dump(payload, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        LOGGER.info("Dry-run mode: printed %s events and skipped network sends", len(events))


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
