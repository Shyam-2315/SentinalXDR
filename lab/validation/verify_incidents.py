#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from validation.common import (
    add_common_args,
    collect_field_values,
    fail,
    get_json,
    missing_values,
    pass_message,
    resolve_token,
    scenario_expectations,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify SentinelXDR lab incidents.")
    add_common_args(parser)
    args = parser.parse_args()

    token = resolve_token(args)
    expectations = scenario_expectations(args.scenario)
    response = get_json(args.api_base_url, f"/api/incidents?limit={args.limit}", token)
    incidents = response.get("incidents", [])
    if not isinstance(incidents, list):
        fail("Unexpected /api/incidents response shape.")
    if not incidents:
        fail("No incidents found.")

    techniques = collect_field_values(incidents, "mitre_techniques")
    tactics = collect_field_values(incidents, "mitre_tactics")
    missing_techniques = missing_values(techniques, expectations["expected_mitre_techniques"])
    missing_tactics = missing_values(tactics, expectations["expected_tactics"])
    if missing_techniques or missing_tactics:
        fail(
            "Missing incident MITRE coverage. "
            f"missing_techniques={missing_techniques}, missing_tactics={missing_tactics}"
        )

    pass_message(
        f"Verified incidents include {len(expectations['expected_mitre_techniques'])} "
        "expected MITRE technique(s)."
    )


if __name__ == "__main__":
    main()
