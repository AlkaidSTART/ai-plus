"""Worker process CLI entrypoint."""

import argparse
import logging

from insightx.config import get_settings
from insightx.database import build_database
from insightx.services.worker import run_worker


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    parser = argparse.ArgumentParser(description="InsightX background task worker")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Process one pending batch and exit",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=1.0,
        help="Polling interval in seconds",
    )
    args = parser.parse_args()

    settings = get_settings()
    _, session_factory = build_database(settings)
    run_worker(session_factory, poll_interval=args.poll_interval, run_once=args.once)


if __name__ == "__main__":
    main()
