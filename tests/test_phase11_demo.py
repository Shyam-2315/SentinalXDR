from __future__ import annotations

from pathlib import Path

from scripts.demo_common import DEMO_TAG, demo_event_batch
from scripts.export_lovable_context import build_lovable_context

ROOT = Path(__file__).resolve().parents[1]


def test_lovable_context_export_shape() -> None:
    context = build_lovable_context("http://localhost:8000")

    assert context["api_base_url"] == "http://localhost:8000"
    assert "auth_flow" in context
    assert "GET /api/dashboard/summary" in context["endpoints"]
    assert "/attack-chains/:id" in context["recommended_frontend_routes"]
    assert "risk_score_average" in context["dashboard_card_fields"]
    assert "graph.edges[].relationship" in context["attack_chain_graph_fields"]


def test_demo_event_batch_is_tagged_and_safe() -> None:
    events = demo_event_batch()

    assert len(events) >= 6
    for event in events:
        assert DEMO_TAG in event["tags"]
        assert event["raw_event"]["marker"] == DEMO_TAG
        assert event["raw_event"]["simulation"] is True
        assert event["raw_event"]["demo"] is True
        assert "sentinelxdr-demo" in event["tags"]


def test_required_phase11_docs_exist() -> None:
    required_docs = [
        "DEMO_SCRIPT.md",
        "JUDGE_WALKTHROUGH.md",
        "HACKATHON_PITCH.md",
        "LOVABLE_FRONTEND_PROMPT.md",
        "FRONTEND_API_EXAMPLES.md",
        "LOCAL_DEMO_CHECKLIST.md",
        "PROJECT_STATUS.md",
        "lovable_context.json",
    ]

    for doc_name in required_docs:
        path = ROOT / "docs" / doc_name
        assert path.exists(), doc_name
        assert path.read_text(encoding="utf-8").strip()


def test_required_phase11_scripts_exist() -> None:
    for script_name in [
        "demo_seed.py",
        "demo_reset.py",
        "demo_smoke_check.py",
        "export_lovable_context.py",
    ]:
        path = ROOT / "scripts" / script_name
        assert path.exists(), script_name
        assert path.read_text(encoding="utf-8").startswith("#!/usr/bin/env python3")
