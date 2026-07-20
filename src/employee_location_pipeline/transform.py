from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone

import pandas as pd

from .config import AppConfig, BranchLocation

PUBLIC_COLUMNS = [
    "employee_id", "employee_code", "full_name", "branch", "department",
    "cost_center", "admission_date", "postal_code", "street", "street_number",
    "address_complement", "neighborhood", "city", "state", "declared_commute_time",
    "latitude", "longitude", "full_address", "route_distance_km", "route_duration_text",
    "uses_train", "uses_walking", "uses_subway", "uses_bus", "uses_car",
    "straight_line_distance_km", "source_updated_at", "loaded_at_utc",
]

ALIASES = {
    "id": "employee_id",
    "matricula": "employee_code",
    "nome_complet": "full_name",
    "nome_completo": "full_name",
    "filial": "branch",
    "desc_depto": "department",
    "descricao_departamento": "department",
    "centro_custo": "cost_center",
    "data_admis": "admission_date",
    "cep": "postal_code",
    "endereco": "street",
    "num_endereco": "street_number",
    "compl_ender": "address_complement",
    "bairro": "neighborhood",
    "municipio": "city",
    "estado": "state",
    "tempo": "declared_commute_time",
    "latitude": "latitude",
    "longitude": "longitude",
    "endereco_completo": "full_address",
    "dist_google_maps": "route_distance_km",
    "tempo_google_maps": "route_duration_text",
    "trem": "uses_train",
    "a_pe": "uses_walking",
    "metro": "uses_subway",
    "onibus": "uses_bus",
    "automovel": "uses_car",
    "distancia": "straight_line_distance_km",
    "source_updated_at": "source_updated_at",
}

REQUIRED = [
    "employee_id", "full_name", "branch", "postal_code", "street", "city", "state",
    "declared_commute_time",
]


@dataclass(frozen=True)
class TransformResult:
    dataframe: pd.DataFrame
    warning_count: int


def _key(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def _text(value: object) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    return str(value).strip()


def _postal_code(value: object) -> str:
    digits = re.sub(r"\D", "", _text(value))
    if not digits:
        return ""
    if len(digits) != 8:
        raise ValueError(f"Invalid Brazilian postal code: {value!r}")
    return f"{digits[:5]}-{digits[5:]}"


def _commute_time(value: object) -> str:
    text = _text(value).lower()
    if not text:
        return ""
    match = re.fullmatch(r"(\d{1,2}):([0-5]\d)", text)
    if match:
        return f"{int(match.group(1))}:{match.group(2)}"
    hours = re.search(r"(\d+)\s*h", text)
    minutes = re.search(r"(\d+)\s*(?:min|m)", text)
    if hours or minutes:
        total = int(hours.group(1)) * 60 if hours else 0
        total += int(minutes.group(1)) if minutes else 0
        return f"{total // 60}:{total % 60:02d}"
    if text.isdigit():
        total = int(text)
        return f"{total // 60}:{total % 60:02d}"
    raise ValueError(f"Invalid commute time: {value!r}")


def _float_or_none(value: object) -> float | None:
    text = _text(value).replace(" ", "")
    if not text:
        return None
    if "," in text and "." not in text:
        text = text.replace(",", ".")
    return float(text)


def _indicator(value: object) -> int:
    text = _text(value).lower()
    if not text:
        return 0
    if text in {"sim", "yes", "true", "x"}:
        return 1
    if text in {"nao", "não", "no", "false"}:
        return 0
    number = int(float(text.replace(",", ".")))
    if number < 0:
        raise ValueError("Transport indicators cannot be negative.")
    return number


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0088
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _full_address(row: pd.Series) -> str:
    street_line = " ".join(part for part in [row["street"], row["street_number"]] if part)
    locality = ", ".join(part for part in [row["neighborhood"], row["city"], row["state"]] if part)
    return ", ".join(part for part in [street_line, row["address_complement"], locality, row["postal_code"]] if part)


def _distance(row: pd.Series, branch: BranchLocation | None) -> float | None:
    if branch is None or row["latitude"] is None or row["longitude"] is None:
        return None
    return round(haversine_km(row["latitude"], row["longitude"], branch.latitude, branch.longitude), 3)


def transform_dataframe(source: pd.DataFrame, config: AppConfig) -> TransformResult:
    renamed = source.rename(columns={column: ALIASES.get(_key(column), _key(column)) for column in source.columns}).copy()
    missing = [column for column in REQUIRED if column not in renamed.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")

    for column in PUBLIC_COLUMNS:
        if column not in renamed.columns:
            renamed[column] = None

    data = renamed[PUBLIC_COLUMNS].copy()
    text_columns = [
        "employee_id", "employee_code", "full_name", "branch", "department", "cost_center",
        "street", "street_number", "address_complement", "neighborhood", "city", "state",
        "route_duration_text", "source_updated_at",
    ]
    for column in text_columns:
        data[column] = data[column].map(_text)

    data["branch"] = data["branch"].str.upper()
    data["state"] = data["state"].str.upper()
    data["postal_code"] = data["postal_code"].map(_postal_code)
    data["declared_commute_time"] = data["declared_commute_time"].map(_commute_time)
    data["admission_date"] = pd.to_datetime(data["admission_date"], errors="coerce").dt.date.astype("string").fillna("")

    for column in ["latitude", "longitude", "route_distance_km", "straight_line_distance_km"]:
        data[column] = data[column].map(_float_or_none)
    for column in ["uses_train", "uses_walking", "uses_subway", "uses_bus", "uses_car"]:
        data[column] = data[column].map(_indicator)

    if data["employee_id"].eq("").any():
        raise ValueError("employee_id cannot be blank.")
    duplicated_ids = data.loc[data["employee_id"].duplicated(keep=False), "employee_id"].unique().tolist()
    if duplicated_ids:
        raise ValueError(f"Duplicated employee_id values: {duplicated_ids}")
    nonblank_codes = data.loc[data["employee_code"].ne(""), "employee_code"]
    if nonblank_codes.duplicated().any():
        raise ValueError("employee_code must be unique when populated.")

    data["full_address"] = data.apply(_full_address, axis=1)
    computed = []
    warning_count = 0
    for _, row in data.iterrows():
        branch = config.branches.get(row["branch"])
        distance = _distance(row, branch)
        if distance is None:
            warning_count += 1
            if config.pipeline.fail_on_missing_coordinates:
                raise ValueError(f"Unable to calculate distance for employee_id={row['employee_id']}")
            distance = row["straight_line_distance_km"]
        computed.append(distance)
    data["straight_line_distance_km"] = computed
    data["loaded_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    data = data.sort_values("employee_id").reset_index(drop=True)
    return TransformResult(data, warning_count)
