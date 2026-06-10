import json
from pathlib import Path


LAB_ROOT = Path(__file__).resolve().parents[1]


def test_all_scenario_metadata_scripts_exist_and_are_safe_marked():
    metadata = json.loads((LAB_ROOT / "scenario_metadata.json").read_text(encoding="utf-8"))

    assert len(metadata["scenarios"]) == 6
    for scenario in metadata["scenarios"]:
        script_path = LAB_ROOT / scenario["script"]
        script_text = script_path.read_text(encoding="utf-8")
        assert script_path.exists()
        assert "owned local lab systems only" in script_text
        assert "simulation" in script_text.lower()
        assert scenario["expected_rules"]
        assert scenario["expected_mitre_techniques"]
        assert scenario["expected_tactics"]


def test_full_chain_metadata_includes_required_mitre_coverage():
    metadata = json.loads((LAB_ROOT / "scenario_metadata.json").read_text(encoding="utf-8"))
    full_chain = next(
        scenario
        for scenario in metadata["scenarios"]
        if scenario["id"] == "scenario_06_full_attack_chain"
    )

    assert set(full_chain["expected_mitre_techniques"]) == {
        "T1595",
        "T1110",
        "T1059.001",
        "T1027",
        "T1053.003",
        "T1041",
    }
