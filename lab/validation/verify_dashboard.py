#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from validation.common import (
    add_common_args,
    fail,
    get_json,
    missing_values,
    pass_message,
    resolve_token,
    scenario_expectations,
)

METRIC_FIELDS = [
    "total_events",
    "total_alerts",
    "open_alerts",
    "total_incidents",
    "open_incidents",
    "total_attack_chains",
    "active_attack_chains",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify SentinelXDR lab dashboard metrics.")
    add_common_args(parser)
    parser.add_argument("--baseline", help="Path to a previous dashboard summary JSON file.")
    parser.add_argument(
        "--write-baseline",
        help="Write the current dashboard summary to this path and exit.",
    )
    args = parser.parse_args()

    token = resolve_token(args)
    summary = get_json(args.api_base_url, "/api/dashboard/summary", token)
    mitre_summary = get_json(args.api_base_url, "/api/dashboard/mitre-summary", token)
    get_json(args.api_base_url, "/api/dashboard/recent-alerts?limit=5", token)
    get_json(args.api_base_url, "/api/dashboard/recent-incidents?limit=5", token)
    get_json(args.api_base_url, "/api/dashboard/recent-attack-chains?limit=5", token)

    if args.write_baseline:
        write_json(Path(args.write_baseline), summary)
        pass_message(f"Wrote dashboard baseline to {args.write_baseline}.")
        return

    if args.baseline:
        baseline = read_json(Path(args.baseline))
        changed = changed_metrics(baseline, summary)
        if not changed:
            fail(f"No dashboard metric changed across {METRIC_FIELDS}.")
        print(f"Changed dashboard metrics: {', '.join(changed)}")

    expectations = scenario_expectations(args.scenario)
    techniques = mitre_techniques_from_summary(mitre_summary)
    missing_techniques = missing_values(techniques, expectations["expected_mitre_techniques"])
    if missing_techniques:
        fail(f"Missing MITRE techniques in dashboard summary: {missing_techniques}")

    pass_message("Verified dashboard summary, recent views, and MITRE coverage.")


def changed_metrics(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    changed: list[str] = []
    for field in METRIC_FIELDS:
        if before.get(field) != after.get(field):
            changed.append(field)
    return changed


def mitre_techniques_from_summary(mitre_summary: dict[str, Any]) -> list[str]:
    techniques: list[str] = []
    for tactic in mitre_summary.get("tactics", []):
        if not isinstance(tactic, dict):
            continue
        for technique in tactic.get("techniques", []):
            if isinstance(technique, dict) and technique.get("technique"):
                techniques.append(str(technique["technique"]))
    return techniques


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as json_file:
        return json.load(json_file)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as json_file:
        json.dump(payload, json_file, indent=2, sort_keys=True)
        json_file.write("\n")


if __name__ == "__main__":
    main()
