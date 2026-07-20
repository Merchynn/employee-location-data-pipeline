from __future__ import annotations

from dataclasses import dataclass

from filelock import FileLock

from .config import AppConfig
from .extract import extract_dataframe
from .load import load_dataframe
from .transform import transform_dataframe


@dataclass(frozen=True)
class PipelineResult:
    rows_extracted: int
    rows_loaded: int
    warning_count: int
    destination: str
    load_id: str


def run_pipeline(
    config: AppConfig,
    *,
    dry_run: bool = False,
    use_postgres: bool = False,
) -> PipelineResult:
    config.pipeline.output_directory.mkdir(parents=True, exist_ok=True)
    config.pipeline.lock_file.parent.mkdir(parents=True, exist_ok=True)
    with FileLock(str(config.pipeline.lock_file), timeout=1):
        source = extract_dataframe(config.source)
        transformed = transform_dataframe(source, config)
        preview = config.pipeline.output_directory / "employee_locations_clean.csv"
        transformed.dataframe.to_csv(preview, index=False, encoding="utf-8")
        if dry_run:
            return PipelineResult(
                len(source), 0, transformed.warning_count, str(preview), "dry-run"
            )
        loaded = load_dataframe(
            transformed.dataframe,
            config.storage,
            use_postgres=use_postgres,
        )
        return PipelineResult(
            len(source),
            loaded.rows_loaded,
            transformed.warning_count,
            loaded.destination,
            loaded.load_id,
        )
