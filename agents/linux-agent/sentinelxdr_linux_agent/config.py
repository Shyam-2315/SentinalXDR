from __future__ import annotations

import os
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Mapping

import yaml


DEFAULT_AUTH_LOG_PATHS = ["/var/log/auth.log", "/var/log/secure"]
DEFAULT_CRON_PATHS = [
    "/etc/crontab",
    "/etc/cron.d",
    "/var/spool/cron",
    "/var/spool/cron/crontabs",
]


@dataclass(frozen=True)
class AgentConfig:
    api_base_url: str = "http://localhost:8000"
    agent_api_key: str = ""
    agent_version: str = "0.1.0"
    interval_seconds: int = 60
    batch_size: int = 100
    dry_run: bool = False
    once: bool = False
    timeout_seconds: float = 10.0
    max_retries: int = 3
    backoff_seconds: float = 1.0
    state_path: str = "/tmp/sentinelxdr-linux-agent-state.json"
    log_level: str = "INFO"
    auth_log_paths: list[str] = field(default_factory=lambda: DEFAULT_AUTH_LOG_PATHS.copy())
    cron_paths: list[str] = field(default_factory=lambda: DEFAULT_CRON_PATHS.copy())
    process_limit: int = 500
    initial_log_tail_bytes: int = 65536

    def validate(self) -> None:
        if not self.dry_run and not self.agent_api_key:
            raise ValueError("agent_api_key is required unless dry_run is enabled")
        if self.interval_seconds <= 0:
            raise ValueError("interval_seconds must be greater than zero")
        if self.batch_size <= 0:
            raise ValueError("batch_size must be greater than zero")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero")
        if self.max_retries < 0:
            raise ValueError("max_retries cannot be negative")
        if self.backoff_seconds < 0:
            raise ValueError("backoff_seconds cannot be negative")
        if self.process_limit <= 0:
            raise ValueError("process_limit must be greater than zero")
        if self.initial_log_tail_bytes < 0:
            raise ValueError("initial_log_tail_bytes cannot be negative")


ENV_MAP = {
    "SENTINELXDR_API_BASE_URL": ("api_base_url", str),
    "SENTINELXDR_AGENT_API_KEY": ("agent_api_key", str),
    "SENTINELXDR_AGENT_VERSION": ("agent_version", str),
    "SENTINELXDR_INTERVAL_SECONDS": ("interval_seconds", int),
    "SENTINELXDR_BATCH_SIZE": ("batch_size", int),
    "SENTINELXDR_DRY_RUN": ("dry_run", "bool"),
    "SENTINELXDR_ONCE": ("once", "bool"),
    "SENTINELXDR_TIMEOUT_SECONDS": ("timeout_seconds", float),
    "SENTINELXDR_MAX_RETRIES": ("max_retries", int),
    "SENTINELXDR_BACKOFF_SECONDS": ("backoff_seconds", float),
    "SENTINELXDR_STATE_PATH": ("state_path", str),
    "SENTINELXDR_LOG_LEVEL": ("log_level", str),
    "SENTINELXDR_AUTH_LOG_PATHS": ("auth_log_paths", "csv"),
    "SENTINELXDR_CRON_PATHS": ("cron_paths", "csv"),
    "SENTINELXDR_PROCESS_LIMIT": ("process_limit", int),
    "SENTINELXDR_INITIAL_LOG_TAIL_BYTES": ("initial_log_tail_bytes", int),
}


def load_config(
    path: str | Path = "config.yaml",
    environ: Mapping[str, str] | None = None,
    validate: bool = True,
) -> AgentConfig:
    env = environ if environ is not None else os.environ
    values = _read_yaml_config(Path(path))
    values.update(_read_env_config(env))
    config = AgentConfig(**values)
    if validate:
        config.validate()
    return config


def apply_overrides(config: AgentConfig, **overrides: Any) -> AgentConfig:
    clean_overrides = {key: value for key, value in overrides.items() if value is not None}
    updated = replace(config, **clean_overrides)
    updated.validate()
    return updated


def _read_yaml_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8") as config_file:
        loaded = yaml.safe_load(config_file) or {}
    if not isinstance(loaded, dict):
        raise ValueError(f"{path} must contain a YAML mapping")

    values: dict[str, Any] = {}
    values.update(_copy_known_keys(loaded))
    for section in ("api", "agent", "collection"):
        section_value = loaded.get(section, {})
        if section_value is None:
            continue
        if not isinstance(section_value, dict):
            raise ValueError(f"{section} must be a YAML mapping")
        values.update(_copy_known_keys(section_value))

    if "api_key" in loaded.get("agent", {}):
        values["agent_api_key"] = loaded["agent"]["api_key"]
    if "base_url" in loaded.get("api", {}):
        values["api_base_url"] = loaded["api"]["base_url"]
    if "key" in loaded.get("api", {}):
        values["agent_api_key"] = loaded["api"]["key"]

    return values


def _copy_known_keys(mapping: Mapping[str, Any]) -> dict[str, Any]:
    allowed = set(AgentConfig.__dataclass_fields__)
    aliases = {
        "api_key": "agent_api_key",
        "base_url": "api_base_url",
        "version": "agent_version",
    }
    copied: dict[str, Any] = {}
    for key, value in mapping.items():
        normalized_key = aliases.get(key, key)
        if normalized_key in allowed:
            copied[normalized_key] = value
    return copied


def _read_env_config(env: Mapping[str, str]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for env_key, (config_key, parser) in ENV_MAP.items():
        if env_key not in env:
            continue
        raw_value = env[env_key]
        if parser == "bool":
            values[config_key] = _parse_bool(raw_value)
        elif parser == "csv":
            values[config_key] = [item.strip() for item in raw_value.split(",") if item.strip()]
        else:
            values[config_key] = parser(raw_value)  # type: ignore[misc]
    return values


def _parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    raise ValueError(f"invalid boolean value: {value!r}")
