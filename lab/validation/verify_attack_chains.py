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
    parser = argparse.ArgumentParser(description="Verify SentinelXDR lab attack chains.")
    add_common_args(parser)
    parser.add_argument(
        "--allow-empty-story",
        action="store_true",
        help="Do not fail if attack-chain story text is missing.",
    )
    args = parser.parse_args()

    token = resolve_token(args)
    expectations = scenario_expectations(args.scenario)
    response = get_json(args.api_base_url, f"/api/attack-chains?limit={args.limit}", token)
    chains = response.get("attack_chains", [])
    if not isinstance(chains, list):
        fail("Unexpected /api/attack-chains response shape.")
    if not chains:
        fail("No attack chains found.")

    techniques = collect_field_values(chains, "mitre_techniques")
    tactics = collect_field_values(chains, "mitre_tactics")
    missing_techniques = missing_values(techniques, expectations["expected_mitre_techniques"])
    missing_tactics = missing_values(tactics, expectations["expected_tactics"])
    empty_story_ids = [
        str(chain.get("id")) for chain in chains if not str(chain.get("story", "")).strip()
    ]
    if missing_techniques or missing_tactics or (empty_story_ids and not args.allow_empty_story):
        fail(
            "Attack-chain validation failed. "
            f"missing_techniques={missing_techniques}, missing_tactics={missing_tactics}, "
            f"empty_story_ids={empty_story_ids}"
        )

    pass_message(
        f"Verified attack chains include {len(expectations['expected_mitre_techniques'])} "
        "expected MITRE technique(s) and threat-story text."
    )


if __name__ == "__main__":
    main()
