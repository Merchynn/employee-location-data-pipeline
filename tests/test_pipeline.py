import sqlite3
from pathlib import Path

from employee_location_pipeline.config import load_config
from employee_location_pipeline.pipeline import run_pipeline
from employee_location_pipeline.sample import ensure_sample_excel


def test_demo_pipeline_is_repeatable(tmp_path: Path):
    sample = ensure_sample_excel(tmp_path / "employee_locations_sample.xlsx")
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        f'''source:\n  mode: local\n  local_file: "{sample.as_posix()}"\n  worksheet: Employees\nstorage:\n  sqlite_file: output/demo.db\n  target_table: employee_location_snapshot\n  staging_table: employee_location_staging\n  audit_table: employee_location_load_audit\npipeline:\n  output_directory: output\n  lock_file: output/demo.lock\nbranches:\n  HEADQUARTERS:\n    latitude: -23.5505\n    longitude: -46.6333\n  REGIONAL_OFFICE:\n    latitude: -15.6014\n    longitude: -56.0979\n''',
        encoding="utf-8",
    )
    config = load_config(config_file)
    first = run_pipeline(config)
    second = run_pipeline(config)
    assert first.rows_loaded == second.rows_loaded == 8
    with sqlite3.connect(config.storage.sqlite_file) as connection:
        rows = connection.execute(
            'SELECT COUNT(*) FROM "employee_location_snapshot"'
        ).fetchone()[0]
        audits = connection.execute(
            'SELECT COUNT(*) FROM "employee_location_load_audit"'
        ).fetchone()[0]
    assert rows == 8
    assert audits == 2
