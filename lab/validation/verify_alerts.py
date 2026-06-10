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
    parser = argparse.ArgumentParser(description="Verify SentinelXDR lab alerts.")
    add_common_args(parser)
    args = parser.parse_args()

    token = resolve_token(args)
    expectations = scenario_expectations(args.scenario)
    response = get_json(args.api_base_url, f"/api/alerts?limit={args.limit}", token)
    alerts = response.get("alerts", [])
    if not isinstance(alerts, list):
        fail("Unexpected /api/alerts response shape.")

    titles = collect_field_values(alerts, "title")
    techniques = collect_field_values(alerts, "mitre_techniques")
    missing_rules = missing_values(titles, expectations["expected_rules"])
    missing_techniques = missing_values(techniques, expectations["expected_mitre_techniques"])
    if missing_rules or missing_techniques:
        fail(
            "Missing alerts or MITRE techniques. "
            f"missing_rules={missing_rules}, missing_techniques={missing_techniques}"
        )

    pass_message(
        f"Verified {len(expectations['expected_rules'])} expected alert rule(s) "
        f"and {len(expectations['expected_mitre_techniques'])} MITRE technique(s)."
    )


if __name__ == "__main__":
    main()
