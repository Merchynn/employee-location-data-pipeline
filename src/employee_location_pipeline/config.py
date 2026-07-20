from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


@dataclass(frozen=True)
class SharePointSettings:
    tenant_id_env: str = "SHAREPOINT_TENANT_ID"
    client_id_env: str = "SHAREPOINT_CLIENT_ID"
    client_secret_env: str = "SHAREPOINT_CLIENT_SECRET"
    site_hostname: str = ""
    site_path: str = ""
    site_id_env: str = "SHAREPOINT_SITE_ID"
    drive_id_env: str = "SHAREPOINT_DRIVE_ID"
    file_path: str = ""
    share_url: str = ""


@dataclass(frozen=True)
class SourceSettings:
    mode: str = "local"
    local_file: Path = Path("sample_data/employee_locations_sample.xlsx")
    worksheet: str = "Employees"
    sharepoint: SharePointSettings = field(default_factory=SharePointSettings)


@dataclass(frozen=True)
class StorageSettings:
    database_url_env: str = "DATABASE_URL"
    sqlite_file: Path = Path("output/employee_locations.db")
    schema: str = "analytics"
    target_table: str = "employee_location_snapshot"
    staging_table: str = "employee_location_staging"
    audit_table: str = "employee_location_load_audit"

    @property
    def database_url(self) -> str | None:
        value = os.getenv(self.database_url_env, "").strip()
        return value or None


@dataclass(frozen=True)
class PipelineSettings:
    output_directory: Path = Path("output")
    lock_file: Path = Path("output/employee_location_pipeline.lock")
    fail_on_missing_coordinates: bool = False


@dataclass(frozen=True)
class BranchLocation:
    latitude: float
    longitude: float


@dataclass(frozen=True)
class AppConfig:
    source: SourceSettings
    storage: StorageSettings
    pipeline: PipelineSettings
    branches: dict[str, BranchLocation]
    base_directory: Path


def _resolve(base: Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (base / path).resolve()


def load_config(path: str | Path) -> AppConfig:
    load_dotenv()
    config_path = Path(path).resolve()
    raw: dict[str, Any] = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    base = config_path.parent

    source_raw = raw.get("source", {})
    sp_raw = source_raw.get("sharepoint", {})
    source = SourceSettings(
        mode=str(source_raw.get("mode", "local")).strip().lower(),
        local_file=_resolve(base, source_raw.get("local_file", "sample_data/employee_locations_sample.xlsx")),
        worksheet=str(source_raw.get("worksheet", "Employees")),
        sharepoint=SharePointSettings(**sp_raw),
    )

    storage_raw = raw.get("storage", {})
    storage = StorageSettings(
        database_url_env=str(storage_raw.get("database_url_env", "DATABASE_URL")),
        sqlite_file=_resolve(base, storage_raw.get("sqlite_file", "output/employee_locations.db")),
        schema=str(storage_raw.get("schema", "analytics")),
        target_table=str(storage_raw.get("target_table", "employee_location_snapshot")),
        staging_table=str(storage_raw.get("staging_table", "employee_location_staging")),
        audit_table=str(storage_raw.get("audit_table", "employee_location_load_audit")),
    )

    pipeline_raw = raw.get("pipeline", {})
    pipeline = PipelineSettings(
        output_directory=_resolve(base, pipeline_raw.get("output_directory", "output")),
        lock_file=_resolve(base, pipeline_raw.get("lock_file", "output/employee_location_pipeline.lock")),
        fail_on_missing_coordinates=bool(pipeline_raw.get("fail_on_missing_coordinates", False)),
    )

    branches = {
        str(name).strip().upper(): BranchLocation(
            latitude=float(values["latitude"]), longitude=float(values["longitude"])
        )
        for name, values in (raw.get("branches", {}) or {}).items()
    }

    if source.mode not in {"local", "sharepoint"}:
        raise ValueError("source.mode must be 'local' or 'sharepoint'.")

    return AppConfig(source, storage, pipeline, branches, base)
