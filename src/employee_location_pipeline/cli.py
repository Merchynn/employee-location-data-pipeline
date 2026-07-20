from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import load_config
from .pipeline import run_pipeline
from .sample import ensure_sample_excel


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Employee location analytics ETL")
    parser.add_argument(
        "command",
        choices=["demo", "validate", "run"],
        nargs="?",
        default="demo",
    )
    parser.add_argument("--config", default="config.example.yaml")
    parser.add_argument(
        "--postgres",
        action="store_true",
        help="Load PostgreSQL instead of SQLite",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = load_config(Path(args.config))
    if args.command == "demo" and config.source.mode == "local":
        ensure_sample_excel(config.source.local_file)
    result = run_pipeline(
        config,
        dry_run=args.command == "validate",
        use_postgres=args.postgres,
    )
    print(json.dumps(result.__dict__, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
