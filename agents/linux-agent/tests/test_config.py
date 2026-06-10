from sentinelxdr_linux_agent.config import load_config


def test_load_config_from_yaml_and_environment(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
api:
  base_url: http://backend:8000
agent:
  api_key: sxag_from_yaml
  interval_seconds: 30
  batch_size: 25
collection:
  auth_log_paths:
    - /tmp/auth.log
""",
        encoding="utf-8",
    )

    config = load_config(
        config_path,
        environ={
            "SENTINELXDR_AGENT_API_KEY": "sxag_from_env",
            "SENTINELXDR_DRY_RUN": "true",
            "SENTINELXDR_BATCH_SIZE": "10",
        },
    )

    assert config.api_base_url == "http://backend:8000"
    assert config.agent_api_key == "sxag_from_env"
    assert config.dry_run is True
    assert config.interval_seconds == 30
    assert config.batch_size == 10
    assert config.auth_log_paths == ["/tmp/auth.log"]


def test_config_requires_api_key_unless_dry_run(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text("agent:\n  dry_run: true\n", encoding="utf-8")

    config = load_config(config_path, environ={})

    assert config.dry_run is True
    assert config.agent_api_key == ""
