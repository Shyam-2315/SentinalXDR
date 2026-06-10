from sentinelxdr_linux_agent.collectors import parse_ssh_failed_login, parse_sudo_usage


def test_parse_ssh_failed_login_event():
    event = parse_ssh_failed_login(
        "Jun 10 12:00:01 host sshd[123]: Failed password for invalid user admin "
        "from 203.0.113.10 port 5555 ssh2",
        "/tmp/auth.log",
    )

    assert event is not None
    assert event["event_type"] == "auth_failure"
    assert event["severity"] == "medium"
    assert event["normalized_fields"]["auth.user"] == "admin"
    assert event["normalized_fields"]["source.ip"] == "203.0.113.10"
    assert event["normalized_fields"]["source.port"] == 5555
    assert event["raw_event"]["log_path"] == "/tmp/auth.log"


def test_parse_sudo_usage_event():
    event = parse_sudo_usage(
        "Jun 10 12:01:01 host sudo: alice : TTY=pts/0 ; PWD=/home/alice ; "
        "USER=root ; COMMAND=/usr/bin/id",
        "/tmp/auth.log",
    )

    assert event is not None
    assert event["event_type"] == "privilege_use"
    assert event["severity"] == "low"
    assert event["normalized_fields"]["user.name"] == "alice"
    assert event["normalized_fields"]["target.user"] == "root"
    assert event["normalized_fields"]["process.command_line"] == "/usr/bin/id"


def test_ignores_non_ssh_auth_failure():
    event = parse_ssh_failed_login(
        "Jun 10 12:01:01 host sudo: pam_unix(sudo:auth): authentication failure; "
        "user=alice",
        "/tmp/auth.log",
    )

    assert event is None


def test_ignores_sudo_session_lines_without_command():
    event = parse_sudo_usage(
        "Jun 10 12:01:01 host sudo: pam_unix(sudo:session): session opened for user root",
        "/tmp/auth.log",
    )

    assert event is None
