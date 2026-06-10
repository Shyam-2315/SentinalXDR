from __future__ import annotations

import argparse

from sentinelxdr_linux_agent.agent import AgentRunner, configure_logging
from sentinelxdr_linux_agent.config import apply_overrides, load_config


def main() -> None:
    parser = argparse.ArgumentParser(description="SentinelXDR Linux Agent MVP")
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    parser.add_argument("--dry-run", action="store_true", help="Print events without sending")
    parser.add_argument("--once", action="store_true", help="Run one collection cycle and exit")
    parser.add_argument("--interval-seconds", type=int, help="Loop interval in seconds")
    parser.add_argument("--batch-size", type=int, help="Maximum events per ingest request")
    args = parser.parse_args()

    config = load_config(args.config, validate=False)
    config = apply_overrides(
        config,
        dry_run=True if args.dry_run else None,
        once=True if args.once else None,
        interval_seconds=args.interval_seconds,
        batch_size=args.batch_size,
    )
    configure_logging(config.log_level)
    AgentRunner(config).run()


if __name__ == "__main__":
    main()
