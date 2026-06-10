from __future__ import annotations

import logging
import os
import platform
import re
import socket
from pathlib import Path
from typing import Any

try:
    import psutil
except ImportError:  # pragma: no cover - exercised only without installed requirements
    psutil = None  # type: ignore[assignment]

from sentinelxdr_linux_agent.config import AgentConfig
from sentinelxdr_linux_agent.events import Event, make_event
from sentinelxdr_linux_agent.state import StateStore

LOGGER = logging.getLogger(__name__)

FAILED_PASSWORD_RE = re.compile(
    r"Failed password for (?:invalid user )?(?P<user>\S+) from "
    r"(?P<src_ip>[0-9a-fA-F:\.]+) port (?P<src_port>\d+)"
)
INVALID_USER_RE = re.compile(
    r"Invalid user (?P<user>\S+) from (?P<src_ip>[0-9a-fA-F:\.]+)(?: port (?P<src_port>\d+))?"
)
PAM_AUTH_FAILURE_RE = re.compile(r"authentication failure;.*rhost=(?P<src_ip>\S+).*user=(?P<user>\S*)")
SUDO_RE = re.compile(r"sudo:\s+(?P<user>\S+)\s*:\s*(?P<details>.*)")
DETAIL_RE = re.compile(r"(?P<key>[A-Z_]+)=(?P<value>.*?)(?=\s*;\s*[A-Z_]+=|$)")


class LinuxTelemetryCollector:
    def __init__(self, config: AgentConfig, state: StateStore) -> None:
        self.config = config
        self.state = state

    def collect(self) -> list[Event]:
        events: list[Event] = []
        events.append(collect_system_metadata())
        events.append(collect_process_snapshot(self.config.process_limit))
        events.extend(self.collect_auth_log_events())
        events.extend(self.collect_cron_events())
        return events

    def collect_auth_log_events(self) -> list[Event]:
        events: list[Event] = []
        for path in self.config.auth_log_paths:
            for line in self._read_new_lines(path):
                ssh_event = parse_ssh_failed_login(line, path)
                if ssh_event is not None:
                    events.append(ssh_event)
                    continue
                sudo_event = parse_sudo_usage(line, path)
                if sudo_event is not None:
                    events.append(sudo_event)
        return events

    def collect_cron_events(self) -> list[Event]:
        events: list[Event] = []
        for cron_file in self._iter_cron_files():
            try:
                stat_result = cron_file.stat()
            except OSError as exc:
                LOGGER.debug("Unable to stat cron file %s: %s", cron_file, exc)
                continue

            path = str(cron_file)
            previous_mtime = self.state.get_cron_mtime(path)
            current_mtime = stat_result.st_mtime
            self.state.set_cron_mtime(path, current_mtime)
            if previous_mtime is None or previous_mtime == current_mtime:
                continue

            events.append(
                make_event(
                    event_type="cron_modified",
                    severity="medium",
                    title="Cron schedule modified",
                    description=f"Cron configuration changed: {path}",
                    raw_event={
                        "path": path,
                        "mtime": current_mtime,
                        "previous_mtime": previous_mtime,
                        "size": stat_result.st_size,
                    },
                    normalized_fields={
                        "file.path": path,
                        "file.size": stat_result.st_size,
                        "file.mtime": current_mtime,
                    },
                    tags=["cron", "persistence", "file"],
                )
            )
        return events

    def _read_new_lines(self, path: str) -> list[str]:
        try:
            stat_result = os.stat(path)
        except FileNotFoundError:
            LOGGER.debug("Log path does not exist: %s", path)
            return []
        except PermissionError:
            LOGGER.warning("Permission denied reading log path: %s", path)
            return []
        except OSError as exc:
            LOGGER.warning("Unable to stat log path %s: %s", path, exc)
            return []

        offset_state = self.state.get_log_offset(path)
        if offset_state is None or offset_state["inode"] != stat_result.st_ino:
            offset = max(stat_result.st_size - self.config.initial_log_tail_bytes, 0)
        else:
            offset = min(offset_state["offset"], stat_result.st_size)

        try:
            with open(path, "r", encoding="utf-8", errors="replace") as log_file:
                log_file.seek(offset)
                lines = log_file.readlines()
                new_offset = log_file.tell()
        except PermissionError:
            LOGGER.warning("Permission denied reading log path: %s", path)
            return []
        except OSError as exc:
            LOGGER.warning("Unable to read log path %s: %s", path, exc)
            return []

        self.state.set_log_offset(path, stat_result.st_ino, new_offset)
        return [line.strip() for line in lines if line.strip()]

    def _iter_cron_files(self) -> list[Path]:
        cron_files: list[Path] = []
        for raw_path in self.config.cron_paths:
            path = Path(raw_path)
            if not path.exists():
                LOGGER.debug("Cron path does not exist: %s", path)
                continue
            if path.is_file():
                cron_files.append(path)
            elif path.is_dir():
                for child in path.rglob("*"):
                    if child.is_file():
                        cron_files.append(child)
        return cron_files


def parse_ssh_failed_login(line: str, path: str) -> Event | None:
    if "sshd" not in line:
        return None
    if "Failed password" not in line and "Invalid user" not in line and "authentication failure" not in line:
        return None

    match = FAILED_PASSWORD_RE.search(line) or INVALID_USER_RE.search(line) or PAM_AUTH_FAILURE_RE.search(line)
    user = match.groupdict().get("user") if match else None
    src_ip = match.groupdict().get("src_ip") if match else None
    src_port = match.groupdict().get("src_port") if match and "src_port" in match.groupdict() else None

    return make_event(
        event_type="auth_failure",
        severity="medium",
        title="SSH failed login",
        description=_compact_description("Failed SSH authentication", user, src_ip),
        raw_event={"message": line, "log_path": path},
        normalized_fields={
            "auth.user": user,
            "source.ip": src_ip,
            "source.port": int(src_port) if src_port else None,
            "auth.service": "ssh",
            "auth.outcome": "failure",
        },
        tags=["auth", "ssh", "linux"],
    )


def parse_sudo_usage(line: str, path: str) -> Event | None:
    if "sudo:" not in line or "COMMAND=" not in line:
        return None

    match = SUDO_RE.search(line)
    user = match.group("user") if match else None
    details = match.group("details") if match else line
    parsed_details = _parse_details(details)
    command = parsed_details.get("COMMAND")

    return make_event(
        event_type="privilege_use",
        severity="low",
        title="sudo command executed",
        description=_compact_description("sudo command observed", user, command),
        raw_event={"message": line, "log_path": path, "sudo": parsed_details},
        normalized_fields={
            "user.name": user,
            "process.command_line": command,
            "target.user": parsed_details.get("USER"),
            "process.working_directory": parsed_details.get("PWD"),
            "terminal.tty": parsed_details.get("TTY"),
        },
        tags=["auth", "sudo", "privilege"],
    )


def collect_process_snapshot(process_limit: int) -> Event:
    processes: list[dict[str, Any]] = []
    if psutil is None:
        return make_event(
            event_type="process_snapshot",
            severity="info",
            title="Linux process snapshot",
            description="psutil is not installed; process snapshot unavailable",
            raw_event={"processes": [], "truncated": False, "error": "psutil not installed"},
            normalized_fields={"process.count": 0},
            tags=["process", "snapshot"],
        )

    for process in psutil.process_iter(["pid", "ppid", "name", "username", "cmdline", "create_time", "status"]):
        if len(processes) >= process_limit:
            break
        try:
            info = process.info
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        processes.append(
            {
                "pid": info.get("pid"),
                "ppid": info.get("ppid"),
                "name": info.get("name"),
                "username": info.get("username"),
                "cmdline": _join_cmdline(info.get("cmdline")),
                "create_time": info.get("create_time"),
                "status": info.get("status"),
            }
        )

    return make_event(
        event_type="process_snapshot",
        severity="info",
        title="Linux process snapshot",
        description=f"Collected {len(processes)} running processes",
        raw_event={"processes": processes, "truncated": len(processes) >= process_limit},
        normalized_fields={"process.count": len(processes)},
        tags=["process", "snapshot"],
    )


def collect_system_metadata() -> Event:
    hostname = socket.gethostname()
    os_release = _os_release()
    ip_addresses = _ip_addresses()
    return make_event(
        event_type="system_metadata",
        severity="info",
        title="Linux system metadata",
        description=f"Collected metadata for {hostname}",
        raw_event={
            "hostname": hostname,
            "platform": platform.platform(),
            "os_release": os_release,
            "ip_addresses": ip_addresses,
        },
        normalized_fields={
            "host.name": hostname,
            "os.type": "linux",
            "os.name": os_release.get("NAME") or platform.system(),
            "os.version": os_release.get("VERSION_ID") or platform.release(),
            "host.ip": ip_addresses,
        },
        tags=["host", "metadata"],
    )


def primary_ip_address() -> str | None:
    addresses = _ip_addresses()
    return addresses[0] if addresses else None


def _ip_addresses() -> list[str]:
    if psutil is None:
        return []

    addresses: list[str] = []
    for interface_addresses in psutil.net_if_addrs().values():
        for address in interface_addresses:
            if address.family not in (socket.AF_INET, socket.AF_INET6):
                continue
            value = address.address.split("%", 1)[0]
            if value.startswith("127.") or value == "::1":
                continue
            if value not in addresses:
                addresses.append(value)
    return addresses


def _os_release() -> dict[str, str]:
    try:
        return dict(platform.freedesktop_os_release())
    except OSError:
        return {}


def _parse_details(details: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for match in DETAIL_RE.finditer(details):
        parsed[match.group("key")] = match.group("value").strip()
    return parsed


def _join_cmdline(cmdline: Any) -> str | None:
    if isinstance(cmdline, list):
        return " ".join(str(part) for part in cmdline)
    if cmdline is None:
        return None
    return str(cmdline)


def _compact_description(prefix: str, first: str | None, second: str | None) -> str:
    parts = [prefix]
    if first:
        parts.append(str(first))
    if second:
        parts.append(str(second))
    return prefix if len(parts) == 1 else " - ".join(parts)
