#!/usr/bin/env python3
"""Sequential OpenAQ ingestion using the /days endpoint with BigQuery upsert."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from google.api_core.exceptions import NotFound
from google.cloud import bigquery

BASE_URL = "https://api.openaq.org/v3/sensors/{sensor_id}/days"
DEFAULT_DATE_FROM = "2022-01-01"
DEFAULT_LIMIT = 1000
DEFAULT_TIMEOUT_SECONDS = 40
DEFAULT_MAX_RETRIES = 6
DEFAULT_SLEEP_BETWEEN_PAGES = 0.4
DEFAULT_SLEEP_BETWEEN_SENSORS = 1.5


@dataclass
class Config:
    project: str
    dataset: str
    table: str
    location: str
    date_from: str
    date_to: str
    parameter_id: Optional[int]
    sensor_ids: List[int]
    limit: int
    timeout_seconds: int
    max_retries: int
    sleep_between_pages: float
    sleep_between_sensors: float
    api_key: str

    @property
    def table_fqn(self) -> str:
        return f"{self.project}.{self.dataset}.{self.table}"

    @property
    def staging_table_fqn(self) -> str:
        return f"{self.project}.{self.dataset}.{self.table}_staging"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch OpenAQ /days data and upsert into BigQuery.")
    parser.add_argument("--project", help="Google Cloud project ID")
    parser.add_argument("--bq-dataset", help="BigQuery dataset name")
    parser.add_argument("--bq-table", help="BigQuery table name")
    parser.add_argument("--bq-location", help="BigQuery dataset location")
    parser.add_argument("--date-from", help="ISO date to start fetching from (inclusive)")
    parser.add_argument("--date-to", help="ISO date to stop fetching at (inclusive)")
    parser.add_argument("--parameter-id", type=int, help="OpenAQ parameterId (2 = PM2.5)")
    parser.add_argument("--sensor-ids", help="Space or comma separated sensor IDs")
    parser.add_argument("--sensor-ids-file", help="Path to file containing sensor IDs")
    parser.add_argument("--limit", type=int, help="Page size to request from the API")
    parser.add_argument("--timeout", type=int, help="HTTP timeout in seconds")
    parser.add_argument("--max-retries", type=int, help="Maximum HTTP retries")
    parser.add_argument("--sleep-between-pages", type=float, help="Sleep between paginated requests in seconds")
    parser.add_argument("--sleep-between-sensors", type=float, help="Sleep between sensor fetches in seconds")
    parser.add_argument("--api-key", help="OpenAQ API key")
    return parser.parse_args()


def _first_nonempty(*values: Optional[str]) -> Optional[str]:
    for value in values:
        if value and value.strip():
            return value.strip()
    return None


def _parse_ids_from_text(text: str) -> List[int]:
    candidates = re.findall(r"\b\d+\b", text)
    seen: set[int] = set()
    ordered: List[int] = []
    for token in candidates:
        sensor_id = int(token)
        if sensor_id not in seen:
            seen.add(sensor_id)
            ordered.append(sensor_id)
    return ordered


def _parse_ids_from_file(path: str) -> List[int]:
    file_path = Path(path)
    if not file_path.exists():
        return []
    try:
        content = file_path.read_text(encoding="utf-8")
    except OSError:
        return []
    return _parse_ids_from_text(content)


def resolve_config(args: argparse.Namespace) -> Config:
    env = os.getenv

    project = _first_nonempty(env("GOOGLE_CLOUD_PROJECT"), env("PROJECT_ID"), args.project)
    if not project:
        raise SystemExit("GOOGLE_CLOUD_PROJECT is required")

    dataset = _first_nonempty(env("BQ_DATASET_RAW"), env("BQ_DATASET"), args.bq_dataset) or "raw"
    table = _first_nonempty(env("BQ_TABLE_RAW"), env("BQ_TABLE"), args.bq_table) or "openaq_pm25_days_raw"
    location = _first_nonempty(env("BQ_LOCATION"), args.bq_location) or "europe-north2"

    date_from = _first_nonempty(env("DATE_FROM"), args.date_from) or DEFAULT_DATE_FROM
    date_to = _first_nonempty(env("DATE_TO"), args.date_to)
    if not date_to:
        date_to = datetime.now(timezone.utc).date().isoformat()
    if date_to < date_from:
        date_to = date_from

    parameter_id_env = _first_nonempty(env("PARAMETER_ID"), args.parameter_id and str(args.parameter_id))
    parameter_id = int(parameter_id_env) if parameter_id_env not in (None, "", "-1") else None

    sensor_file = _first_nonempty(env("IDS_FILE"), env("SENSOR_IDS_FILE"), args.sensor_ids_file)
    sensor_ids = _parse_ids_from_file(sensor_file) if sensor_file else []
    if not sensor_ids:
        sensor_ids_text = _first_nonempty(env("IDS"), env("SENSOR_IDS"), args.sensor_ids)
        sensor_ids = _parse_ids_from_text(sensor_ids_text or "") if sensor_ids_text else []
    if not sensor_ids:
        raise SystemExit("No sensor IDs provided via IDS/IDS_FILE or CLI arguments")

    limit_raw = _first_nonempty(env("LIMIT_PER_PAGE"), env("LIMIT"), args.limit and str(args.limit))
    limit = int(limit_raw) if limit_raw else DEFAULT_LIMIT

    timeout_raw = _first_nonempty(env("TIMEOUT_SEC"), env("TIMEOUT"), args.timeout and str(args.timeout))
    timeout_seconds = int(timeout_raw) if timeout_raw else DEFAULT_TIMEOUT_SECONDS

    retries_raw = _first_nonempty(env("MAX_RETRIES"), args.max_retries and str(args.max_retries))
    max_retries = int(retries_raw) if retries_raw else DEFAULT_MAX_RETRIES

    sleep_pages_raw = _first_nonempty(env("SLEEP_BETWEEN_PAGES"), args.sleep_between_pages and str(args.sleep_between_pages))
    sleep_between_pages = float(sleep_pages_raw) if sleep_pages_raw else DEFAULT_SLEEP_BETWEEN_PAGES

    sleep_sensors_raw = _first_nonempty(env("SLEEP_BETWEEN_SENSORS"), args.sleep_between_sensors and str(args.sleep_between_sensors))
    sleep_between_sensors = float(sleep_sensors_raw) if sleep_sensors_raw else DEFAULT_SLEEP_BETWEEN_SENSORS

    api_key = _first_nonempty(env("OPENAQ_API_KEY"), args.api_key)
    if not api_key:
        raise SystemExit("OPENAQ_API_KEY must be provided")

    return Config(
        project=project,
        dataset=dataset,
        table=table,
        location=location,
        date_from=date_from,
        date_to=date_to,
        parameter_id=parameter_id,
        sensor_ids=sensor_ids,
        limit=max(1, limit),
        timeout_seconds=max(5, timeout_seconds),
        max_retries=max(1, max_retries),
        sleep_between_pages=max(0.0, sleep_between_pages),
        sleep_between_sensors=max(0.0, sleep_between_sensors),
        api_key=api_key,
    )


def get_with_retries(
    url: str,
    headers: Dict[str, str],
    params: Dict[str, Any],
    *,
    timeout_seconds: int,
    max_retries: int,
) -> Optional[Dict[str, Any]]:
    backoff = 1.0
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(url, headers=headers, params=params, timeout=timeout_seconds)
            if response.status_code == 200:
                return response.json()

            if response.status_code == 429:
                reset_header = response.headers.get("X-RateLimit-Reset") or response.headers.get("x-ratelimit-reset")
                try:
                    wait_seconds = float(reset_header)
                except (TypeError, ValueError):
                    wait_seconds = backoff
                wait_seconds = max(wait_seconds, backoff)
                print(f"[429] rate limited, sleeping {wait_seconds:.2f}s (attempt {attempt}/{max_retries})")
                time.sleep(wait_seconds)
            elif response.status_code in {500, 502, 503, 504}:
                print(f"[{response.status_code}] server error, sleeping {backoff:.2f}s (attempt {attempt}/{max_retries})")
                time.sleep(backoff)
            elif response.status_code == 404:
                return None
            else:
                print(f"[error] HTTP {response.status_code}: {response.text[:200]}")
                return None
        except requests.RequestException as exc:
            print(f"[warn] RequestException: {exc}; sleeping {backoff:.2f}s (attempt {attempt}/{max_retries})")
            time.sleep(backoff)

        backoff = min(backoff * 2, 10)

    print("[error] exhausted HTTP retries")
    return None


def _extract_units(row: Dict[str, Any]) -> Optional[str]:
    units = row.get("units")
    if isinstance(units, str) and units:
        return units

    parameter = row.get("parameter")
    if isinstance(parameter, dict):
        nested_units = parameter.get("units") or parameter.get("unit")
        if isinstance(nested_units, str) and nested_units:
            return nested_units

    return None


def _normalize_timestamp(value: str) -> Optional[str]:
    value = value.strip()
    if not value:
        return None
    if value.endswith("Z"):
        return value
    if "T" not in value:
        return f"{value}T00:00:00Z"
    if re.search(r"[+-]\d{2}:?\d{2}$", value):
        return value if "+" in value or "-" in value else f"{value}Z"
    return f"{value}Z"


def _extract_date_utc(row: Dict[str, Any]) -> Optional[str]:
    def _from_dict(container: Dict[str, Any], keys: List[str]) -> Optional[str]:
        for key in keys:
            candidate = container.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate
        return None

    date_obj = row.get("date")
    if isinstance(date_obj, dict):
        candidate = _from_dict(date_obj, ["utc", "UTC", "iso", "dateUtc", "dateUTC"])
        if candidate:
            return _normalize_timestamp(candidate)
        candidate = _from_dict(date_obj, ["local", "LOCAL", "dateLocal", "date"])
        if candidate:
            return _normalize_timestamp(candidate)
    elif isinstance(date_obj, str):
        normalized = _normalize_timestamp(date_obj)
        if normalized:
            return normalized

    direct_keys = [
        "date_utc",
        "dateUtc",
        "datetime",
        "datetimeUtc",
        "datetime_utc",
        "utc",
    ]
    for key in direct_keys:
        candidate = row.get(key)
        if isinstance(candidate, str):
            normalized = _normalize_timestamp(candidate)
            if normalized:
                return normalized

    period = row.get("period")
    if isinstance(period, dict):
        nested_candidates = [
            period.get("datetimeTo"),
            period.get("dateTimeTo"),
            period.get("datetimeFrom"),
            period.get("dateTimeFrom"),
            period.get("utc"),
            period.get("UTC"),
            period.get("to"),
            period.get("from"),
            period.get("end"),
            period.get("start"),
        ]
        for candidate in nested_candidates:
            if isinstance(candidate, dict):
                nested = _from_dict(candidate, ["utc", "UTC", "iso", "local"])
                if nested:
                    normalized = _normalize_timestamp(nested)
                    if normalized:
                        return normalized
            elif isinstance(candidate, str):
                normalized = _normalize_timestamp(candidate)
                if normalized:
                    return normalized

    window = row.get("window")
    if isinstance(window, dict):
        candidate = _from_dict(window, ["start", "end"])
        if candidate:
            normalized = _normalize_timestamp(candidate)
            if normalized:
                return normalized

    return None


def _to_optional_int(value: Any) -> Optional[int]:
    try:
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _to_optional_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_days_row(sensor_id: int, row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    date_utc = _extract_date_utc(row)

    if not date_utc:
        return None

    value = None
    for key in ("average", "valueAvg", "value_mean", "value", "avg"):
        candidate = row.get(key)
        if isinstance(candidate, (int, float)):
            value = float(candidate)
            break

    if value is None and isinstance(row.get("statistics"), dict):
        stats = row["statistics"]
        for key in ("mean", "avg"):
            candidate = stats.get(key)
            if isinstance(candidate, (int, float)):
                value = float(candidate)
                break

    parameter = row.get("parameter")
    if isinstance(parameter, dict):
        parameter_value: Optional[str] = parameter.get("name") or parameter.get("code") or parameter.get("id")
    else:
        parameter_value = parameter if isinstance(parameter, str) else None

    location_id = _to_optional_int(row.get("location_id") or row.get("locationId"))
    longitude = _to_optional_float(row.get("longitude"))
    latitude = _to_optional_float(row.get("latitude"))
    coordinates = row.get("coordinates")
    if isinstance(coordinates, dict):
        longitude = longitude if longitude is not None else _to_optional_float(coordinates.get("longitude"))
        latitude = latitude if latitude is not None else _to_optional_float(coordinates.get("latitude"))

    return {
        "sensor_id": sensor_id,
        "date_utc": date_utc,
        "value": value,
        "units": _extract_units(row),
        "parameter": parameter_value,
        "location_id": location_id,
        "longitude": longitude,
        "latitude": latitude,
        "raw_json": json.dumps(row, ensure_ascii=False),
    }


def fetch_days_for_sensor(config: Config, sensor_id: int, headers: Dict[str, str]) -> List[Dict[str, Any]]:
    url = BASE_URL.format(sensor_id=sensor_id)
    page = 1
    collected: List[Dict[str, Any]] = []

    while True:
        params: Dict[str, Any] = {
            "date_from": config.date_from,
            "date_to": config.date_to,
            "limit": config.limit,
            "page": page,
        }
        if config.parameter_id is not None and config.parameter_id >= 0:
            params["parameterId"] = config.parameter_id

        payload = get_with_retries(
            url,
            headers,
            params,
            timeout_seconds=config.timeout_seconds,
            max_retries=config.max_retries,
        )
        if not payload:
            print(f"[sensor {sensor_id}] empty payload or request failed (page {page})")
            break

        results = payload.get("results") or payload.get("data") or []
        if not results:
            meta_info = payload.get("meta") or {}
            print(f"[sensor {sensor_id}] no results (page {page}) meta={json.dumps(meta_info)[:256]}")
            break

        normalized = [normalize_days_row(sensor_id, row) for row in results]
        valid_rows = [row for row in normalized if row is not None]
        if results and not valid_rows:
            sample = json.dumps(results[0], ensure_ascii=False)
            print(f"[sensor {sensor_id}] dropped rows after normalization sample={sample[:512]}")
        collected.extend(valid_rows)

        meta = payload.get("meta") or {}
        found = meta.get("found")
        limit_used = meta.get("limit")
        current_page = meta.get("page")

        if isinstance(found, (int, float)) and isinstance(limit_used, (int, float)):
            total_pages = math.ceil(found / max(1, int(limit_used)))
            if isinstance(current_page, (int, float)) and int(current_page) >= total_pages:
                break
        if len(results) < config.limit:
            break

        page += 1
        if config.sleep_between_pages > 0:
            time.sleep(config.sleep_between_pages)

    print(f"[sensor {sensor_id}] rows fetched: {len(collected)}")
    return collected


def ensure_tables(client: bigquery.Client, config: Config) -> None:
    dataset_ref = bigquery.Dataset(f"{config.project}.{config.dataset}")
    dataset: Optional[bigquery.Dataset] = None
    try:
        dataset = client.get_dataset(dataset_ref)
    except NotFound:
        dataset_ref.location = config.location
        dataset = client.create_dataset(dataset_ref, exists_ok=True)

    actual_location = (dataset.location if dataset and dataset.location else None) or config.location
    if actual_location != config.location:
        # Keep BigQuery jobs aligned with the dataset location after recreating tables.
        config.location = actual_location

    raw_schema = [
        bigquery.SchemaField("sensor_id", "INT64", mode="REQUIRED"),
        bigquery.SchemaField("date_utc", "TIMESTAMP", mode="REQUIRED"),
        bigquery.SchemaField("value", "FLOAT64"),
        bigquery.SchemaField("units", "STRING"),
        bigquery.SchemaField("parameter", "STRING"),
        bigquery.SchemaField("location_id", "INT64"),
        bigquery.SchemaField("longitude", "FLOAT64"),
        bigquery.SchemaField("latitude", "FLOAT64"),
        bigquery.SchemaField("raw_json", "STRING"),
    ]

    try:
        client.get_table(config.table_fqn)
    except NotFound:
        table_ref = bigquery.Table(config.table_fqn, schema=raw_schema)
        table_ref.time_partitioning = bigquery.TimePartitioning(field="date_utc")
        table_ref.clustering_fields = ["sensor_id", "location_id"]
        client.create_table(table_ref)
        print(f"[bq] created table {config.table_fqn}")

    staging_schema = [
        bigquery.SchemaField("sensor_id", "INT64"),
        bigquery.SchemaField("date_utc", "STRING"),
        bigquery.SchemaField("value", "FLOAT64"),
        bigquery.SchemaField("units", "STRING"),
        bigquery.SchemaField("parameter", "STRING"),
        bigquery.SchemaField("location_id", "INT64"),
        bigquery.SchemaField("longitude", "FLOAT64"),
        bigquery.SchemaField("latitude", "FLOAT64"),
        bigquery.SchemaField("raw_json", "STRING"),
    ]

    try:
        client.get_table(config.staging_table_fqn)
    except NotFound:
        staging_ref = bigquery.Table(config.staging_table_fqn, schema=staging_schema)
        client.create_table(staging_ref)
        print(f"[bq] created staging table {config.staging_table_fqn}")


def load_json_to_staging(client: bigquery.Client, config: Config, rows: List[Dict[str, Any]]) -> int:
    job_config = bigquery.LoadJobConfig(write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE)
    job = client.load_table_from_json(rows, config.staging_table_fqn, job_config=job_config, location=config.location)
    job.result()
    loaded_rows = job.output_rows or 0
    print(f"[bq] loaded {loaded_rows} rows into {config.staging_table_fqn}")
    return loaded_rows


def merge_staging_into_target(client: bigquery.Client, config: Config) -> None:
    target = f"`{config.table_fqn}`"
    staging = f"`{config.staging_table_fqn}`"
    sql = f"""
    MERGE {target} T
    USING (
      SELECT
        sensor_id,
        CAST(date_utc AS TIMESTAMP) AS date_utc,
        value,
        units,
        parameter,
        CAST(NULLIF(location_id, '') AS INT64) AS location_id,
        CAST(NULLIF(longitude, '') AS FLOAT64) AS longitude,
        CAST(NULLIF(latitude, '') AS FLOAT64) AS latitude,
        raw_json
      FROM {staging}
      WHERE date_utc IS NOT NULL
    ) S
    ON T.sensor_id = S.sensor_id AND T.date_utc = S.date_utc
    WHEN MATCHED THEN UPDATE SET
      value = S.value,
      units = S.units,
      parameter = S.parameter,
      location_id = S.location_id,
      longitude = S.longitude,
      latitude = S.latitude,
      raw_json = S.raw_json
    WHEN NOT MATCHED THEN INSERT (
      sensor_id,
      date_utc,
      value,
      units,
      parameter,
      location_id,
      longitude,
      latitude,
      raw_json
    ) VALUES (
      S.sensor_id,
      S.date_utc,
      S.value,
      S.units,
      S.parameter,
      S.location_id,
      S.longitude,
      S.latitude,
      S.raw_json
    )
    """
    job = client.query(sql, location=config.location)
    job.result()
    print(f"[bq] merge complete into {config.table_fqn}")


def run(config: Config) -> None:
    headers = {"accept": "application/json", "X-API-Key": config.api_key}

    print(
        "Starting OpenAQ ingestion",
        {
            "project": config.project,
            "dataset": config.dataset,
            "table": config.table,
            "date_from": config.date_from,
            "date_to": config.date_to,
            "sensors": len(config.sensor_ids),
            "parameter_id": config.parameter_id,
        },
    )

    all_rows: List[Dict[str, Any]] = []
    for index, sensor_id in enumerate(config.sensor_ids):
        rows = fetch_days_for_sensor(config, sensor_id, headers)
        all_rows.extend(rows)
        if index < len(config.sensor_ids) - 1 and config.sleep_between_sensors > 0:
            time.sleep(config.sleep_between_sensors)

    if not all_rows:
        print("No rows fetched; skipping BigQuery load")
        return

    client = bigquery.Client(project=config.project)
    ensure_tables(client, config)
    loaded = load_json_to_staging(client, config, all_rows)
    if loaded == 0:
        print("Staging load produced zero rows; aborting merge")
        return

    merge_staging_into_target(client, config)
    print("Ingestion finished")


def main() -> None:
    print("[DEBUG] main() called", flush=True)
    args = parse_args()
    print(f"[DEBUG] args parsed: {args}", flush=True)
    config = resolve_config(args)
    print(f"[DEBUG] config resolved: {config.project}", flush=True)
    run(config)
    print("[DEBUG] run() completed", flush=True)


if __name__ == "__main__":
    print("[DEBUG] Script started", flush=True)
    main()
    print("[DEBUG] Script finished", flush=True)
