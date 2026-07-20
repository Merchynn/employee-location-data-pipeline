from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import create_engine, text

from .config import StorageSettings


@dataclass(frozen=True)
class LoadResult:
    rows_loaded: int
    destination: str
    load_id: str


def _load_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def load_sqlite(dataframe: pd.DataFrame, settings: StorageSettings) -> LoadResult:
    settings.sqlite_file.parent.mkdir(parents=True, exist_ok=True)
    load_id = _load_id()
    with sqlite3.connect(settings.sqlite_file) as connection:
        connection.execute("BEGIN")
        dataframe.to_sql(settings.staging_table, connection, if_exists="replace", index=False)
        connection.execute(f'DROP TABLE IF EXISTS "{settings.target_table}"')
        connection.execute(f'ALTER TABLE "{settings.staging_table}" RENAME TO "{settings.target_table}"')
        connection.execute(
            f'''CREATE TABLE IF NOT EXISTS "{settings.audit_table}" (
                load_id TEXT PRIMARY KEY,
                loaded_at_utc TEXT NOT NULL,
                rows_loaded INTEGER NOT NULL,
                destination TEXT NOT NULL,
                metadata_json TEXT
            )'''
        )
        connection.execute(
            f'INSERT INTO "{settings.audit_table}" VALUES (?, ?, ?, ?, ?)',
            (
                load_id,
                datetime.now(timezone.utc).isoformat(),
                len(dataframe),
                str(settings.sqlite_file),
                json.dumps({"mode": "snapshot"}),
            ),
        )
        connection.commit()
    return LoadResult(len(dataframe), str(settings.sqlite_file), load_id)


def load_postgres(dataframe: pd.DataFrame, settings: StorageSettings, database_url: str) -> LoadResult:
    load_id = _load_id()
    engine = create_engine(database_url, future=True)
    with engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{settings.schema}"'))
        dataframe.to_sql(
            settings.staging_table,
            connection,
            schema=settings.schema,
            if_exists="replace",
            index=False,
            method="multi",
            chunksize=1000,
        )
        qualified_target = f'"{settings.schema}"."{settings.target_table}"'
        qualified_staging = f'"{settings.schema}"."{settings.staging_table}"'
        connection.execute(text(f'CREATE TABLE IF NOT EXISTS {qualified_target} (LIKE {qualified_staging} INCLUDING ALL)'))
        connection.execute(text(f'LOCK TABLE {qualified_target} IN ACCESS EXCLUSIVE MODE'))
        connection.execute(text(f'TRUNCATE TABLE {qualified_target}'))
        connection.execute(text(f'INSERT INTO {qualified_target} SELECT * FROM {qualified_staging}'))
        connection.execute(text(f'''CREATE TABLE IF NOT EXISTS "{settings.schema}"."{settings.audit_table}" (
            load_id text PRIMARY KEY,
            loaded_at_utc timestamptz NOT NULL,
            rows_loaded integer NOT NULL,
            destination text NOT NULL,
            metadata_json jsonb
        )'''))
        connection.execute(
            text(f'''INSERT INTO "{settings.schema}"."{settings.audit_table}"
                (load_id, loaded_at_utc, rows_loaded, destination, metadata_json)
                VALUES (:load_id, now(), :rows, :destination, CAST(:metadata AS jsonb))'''),
            {
                "load_id": load_id,
                "rows": len(dataframe),
                "destination": qualified_target,
                "metadata": json.dumps({"mode": "snapshot"}),
            },
        )
    return LoadResult(len(dataframe), f"{settings.schema}.{settings.target_table}", load_id)


def load_dataframe(dataframe: pd.DataFrame, settings: StorageSettings, use_postgres: bool = False) -> LoadResult:
    if use_postgres:
        database_url = settings.database_url
        if not database_url:
            raise RuntimeError(f"Set {settings.database_url_env} before using PostgreSQL.")
        return load_postgres(dataframe, settings, database_url)
    return load_sqlite(dataframe, settings)
