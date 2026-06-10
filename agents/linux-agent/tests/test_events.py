import pytest

from sentinelxdr_linux_agent.events import batch_events, make_event


def test_make_event_matches_backend_ingest_shape():
    event = make_event(
        event_type="auth_failure",
        severity="medium",
        title="SSH failed login",
        description="Failed login for root",
        raw_event={"message": "Failed password for root"},
        normalized_fields={"auth.user": "root"},
        tags=["auth", "ssh"],
    )

    assert event["event_type"] == "auth_failure"
    assert event["severity"] == "medium"
    assert event["source"] == "linux"
    assert event["title"] == "SSH failed login"
    assert event["description"] == "Failed login for root"
    assert event["raw_event"] == {"message": "Failed password for root"}
    assert event["normalized_fields"] == {"auth.user": "root"}
    assert event["tags"] == ["auth", "ssh"]
    assert event["timestamp"].endswith("Z")


def test_batch_events_splits_by_batch_size():
    events = [
        make_event(
            event_type="system_metadata",
            severity="info",
            title=f"event {index}",
            description="test",
            raw_event={"index": index},
        )
        for index in range(5)
    ]

    batches = batch_events(events, 2)

    assert [len(batch) for batch in batches] == [2, 2, 1]


def test_batch_events_rejects_invalid_size():
    with pytest.raises(ValueError, match="batch_size"):
        batch_events([], 0)
