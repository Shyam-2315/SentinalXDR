import json

from sentinelxdr_linux_agent.agent import AgentRunner
from sentinelxdr_linux_agent.config import AgentConfig
from sentinelxdr_linux_agent.events import make_event


class FakeCollector:
    def collect(self):
        return [
            make_event(
                event_type="system_metadata",
                severity="info",
                title="Linux system metadata",
                description="test metadata",
                raw_event={"hostname": "host1"},
            )
        ]


class FakeClient:
    def __init__(self):
        self.heartbeats = []
        self.event_batches = []

    def send_heartbeat(self, *, agent_version, ip_address):
        self.heartbeats.append({"agent_version": agent_version, "ip_address": ip_address})
        return {"status": "ok"}

    def send_events(self, events):
        self.event_batches.append(events)
        return {"accepted": len(events)}


def test_dry_run_prints_events_without_network(capsys, tmp_path):
    client = FakeClient()
    config = AgentConfig(
        dry_run=True,
        once=True,
        state_path=str(tmp_path / "state.json"),
    )
    runner = AgentRunner(config, collector=FakeCollector(), client=client)

    runner.run_once()

    printed = json.loads(capsys.readouterr().out)
    assert printed["events"][0]["event_type"] == "system_metadata"
    assert client.heartbeats == []
    assert client.event_batches == []


def test_run_once_sends_heartbeat_and_batches(tmp_path):
    client = FakeClient()
    config = AgentConfig(
        agent_api_key="sxag_test",
        once=True,
        batch_size=1,
        state_path=str(tmp_path / "state.json"),
    )
    runner = AgentRunner(config, collector=FakeCollector(), client=client)

    runner.run_once()

    assert len(client.heartbeats) == 1
    assert len(client.event_batches) == 1
    assert client.event_batches[0][0]["event_type"] == "system_metadata"
