from pathlib import Path

import pandas as pd
import pytest

from employee_location_pipeline.config import (
    AppConfig,
    BranchLocation,
    PipelineSettings,
    SourceSettings,
    StorageSettings,
)
from employee_location_pipeline.transform import haversine_km, transform_dataframe


def config(tmp_path: Path) -> AppConfig:
    return AppConfig(
        source=SourceSettings(),
        storage=StorageSettings(sqlite_file=tmp_path / "test.db"),
        pipeline=PipelineSettings(
            output_directory=tmp_path,
            lock_file=tmp_path / "test.lock",
        ),
        branches={"HEADQUARTERS": BranchLocation(-23.5505, -46.6333)},
        base_directory=tmp_path,
    )


def valid_data() -> pd.DataFrame:
    return pd.DataFrame([
        {
            "ID": "1",
            "Matricula": "A001",
            "Nome_complet": "Ana Example",
            "Filial": "Headquarters",
            "Desc__Depto": "Analytics",
            "Centro_Custo": "CC100",
            "Data_Admis_": "2024-02-01",
            "Cep": "01310100",
            "Endereco": "Avenida Example",
            "Num_Endereco": "100",
            "Compl_Ender_": "Apto 10",
            "Bairro": "Centro",
            "Municipio": "São Paulo",
            "Estado": "sp",
            "Tempo": "1h 25 min",
            "Latitude": "-23.5614",
            "Longitude": "-46.6560",
            "Dist__Google_Maps": "8,2",
            "Tempo_Google_Maps": "35 minutos",
            "Trem": "0",
            "A_pe": "1",
            "Metro": "1",
            "Onibus": "0",
            "Automovel": "0",
        }
    ])


def test_normalizes_legacy_headers_and_calculates_distance(tmp_path):
    result = transform_dataframe(valid_data(), config(tmp_path))
    row = result.dataframe.iloc[0]
    assert row["postal_code"] == "01310-100"
    assert row["declared_commute_time"] == "1:25"
    assert row["branch"] == "HEADQUARTERS"
    assert row["route_distance_km"] == 8.2
    assert row["straight_line_distance_km"] > 0
    assert "Avenida Example 100" in row["full_address"]


def test_duplicate_employee_id_is_rejected(tmp_path):
    source = pd.concat([valid_data(), valid_data()], ignore_index=True)
    with pytest.raises(ValueError, match="Duplicated employee_id"):
        transform_dataframe(source, config(tmp_path))


def test_haversine_zero_distance():
    assert haversine_km(-23.5, -46.6, -23.5, -46.6) == 0
