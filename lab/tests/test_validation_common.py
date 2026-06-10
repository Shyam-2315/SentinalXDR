from validation.common import collect_field_values, missing_values, scenario_expectations
from validation.verify_dashboard import changed_metrics, mitre_techniques_from_summary


def test_missing_values_preserves_expected_order():
    assert missing_values(["T1110", "T1595"], ["T1595", "T1110", "T1041"]) == ["T1041"]


def test_collect_field_values_handles_lists_and_strings():
    items = [
        {"title": "Nmap Scan Detected", "mitre_techniques": ["T1595"]},
        {"title": "SSH Brute Force Signal", "mitre_techniques": ["T1110", "T1595"]},
    ]

    assert collect_field_values(items, "title") == [
        "Nmap Scan Detected",
        "SSH Brute Force Signal",
    ]
    assert collect_field_values(items, "mitre_techniques") == ["T1595", "T1110"]


def test_dashboard_changed_metrics():
    before = {"total_events": 1, "total_alerts": 1, "total_incidents": 0}
    after = {"total_events": 2, "total_alerts": 1, "total_incidents": 1}

    assert changed_metrics(before, after) == ["total_events", "total_incidents"]


def test_mitre_techniques_from_summary():
    summary = {
        "tactics": [
            {"tactic": "Reconnaissance", "techniques": [{"technique": "T1595", "count": 1}]},
            {"tactic": "Execution", "techniques": [{"technique": "T1059.001", "count": 1}]},
        ]
    }

    assert mitre_techniques_from_summary(summary) == ["T1595", "T1059.001"]


def test_scenario_expectations_for_full_chain():
    expectations = scenario_expectations("scenario_06_full_attack_chain")

    assert "Nmap Scan Detected" in expectations["expected_rules"]
    assert "T1041" in expectations["expected_mitre_techniques"]
