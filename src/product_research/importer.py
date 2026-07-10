"""Import monthly product research SQP exports into merged parquet and CSV outputs."""

from __future__ import annotations

import csv
import logging
import re
from pathlib import Path
from typing import Iterable

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_ROOT = PROJECT_ROOT / "data" / "product_research" / "raw"
OUTPUT_ROOT = PROJECT_ROOT / "data" / "product_research" / "output"
LOG_DIR = PROJECT_ROOT / "logs"

MONTH_PATTERN = re.compile(r"(?P<year>\d{4})-(?P<month>\d{2})")
NON_ALNUM_PATTERN = re.compile(r"[^a-z0-9]+")
UNDERSCORE_PATTERN = re.compile(r"_+")
HEADER_MARKER = "Search Frequency Rank"
TEMP_FILE_PREFIX = "~$"
SUPPORTED_SUFFIXES = {".csv", ".xlsx", ".xlsm"}

logger = logging.getLogger(__name__)


def normalize_column_name(column_name: object) -> str:
    text = str(column_name).strip().lower()
    text = re.sub(r"#\s*(\d+)", r" \1", text)
    text = NON_ALNUM_PATTERN.sub("_", text)
    text = UNDERSCORE_PATTERN.sub("_", text).strip("_")
    return text or "column"


def normalize_column_names(column_names: Iterable[object]) -> list[str]:
    normalized_names: list[str] = []
    seen: dict[str, int] = {}

    for column_name in column_names:
        base_name = normalize_column_name(column_name)
        seen[base_name] = seen.get(base_name, 0) + 1

        if seen[base_name] == 1:
            normalized_names.append(base_name)
        else:
            normalized_names.append(f"{base_name}_{seen[base_name]}")

    return normalized_names


def detect_month(file_path: Path) -> str:
    match = MONTH_PATTERN.search(file_path.stem)
    if match is None:
        raise ValueError(f"Could not detect month from filename: {file_path.name}")

    year = match.group("year")
    month = int(match.group("month"))
    if month < 1 or month > 12:
        raise ValueError(f"Invalid month in filename: {file_path.name}")

    return f"{year}-{month:02d}"


def list_monthly_files(product: str) -> list[Path]:
    raw_dir = RAW_ROOT / product
    if not raw_dir.exists():
        return []

    files = [
        path
        for path in raw_dir.iterdir()
        if path.is_file()
        and not path.name.startswith(TEMP_FILE_PREFIX)
        and path.suffix.lower() in SUPPORTED_SUFFIXES
    ]
    return sorted(files, key=lambda path: (detect_month(path), path.name.lower()))


def find_header_row(file_path: Path) -> int:
    suffix = file_path.suffix.lower()

    if suffix == ".csv":
        with file_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle)
            for row_index, row in enumerate(reader):
                values = [value.strip().lower() for value in row if value.strip()]
                if any(HEADER_MARKER.lower() == value for value in values) and any(
                    "search term" == value for value in values
                ):
                    return row_index
                if row_index >= 24:
                    break
    else:
        preview = pd.read_excel(file_path, header=None, nrows=25, dtype=object)

        for row_index, row in preview.iterrows():
            values = [str(value).strip().lower() for value in row.tolist() if pd.notna(value)]
            if any(HEADER_MARKER.lower() == value for value in values) and any(
                "search term" == value for value in values
            ):
                return int(row_index)

    return 0


def read_source_frame(file_path: Path) -> pd.DataFrame:
    header_row = find_header_row(file_path)
    suffix = file_path.suffix.lower()

    if suffix == ".csv":
        frame = pd.read_csv(
            file_path,
            header=0,
            skiprows=header_row,
            encoding="utf-8-sig",
        )
    else:
        frame = pd.read_excel(file_path, header=0, skiprows=header_row)

    frame.columns = normalize_column_names(frame.columns)
    return frame


def build_historical_search_terms(product: str) -> pd.DataFrame:
    files = list_monthly_files(product)
    if not files:
        raise FileNotFoundError(f"No monthly SQP files found in {RAW_ROOT / product}")

    month_order = {detect_month(path): index for index, path in enumerate(files, start=1)}

    frames: list[pd.DataFrame] = []
    for file_path in files:
        month = detect_month(file_path)
        logger.info("Reading %s for month %s", file_path.name, month)
        frame = read_source_frame(file_path)
        frame["product"] = product
        frame["month"] = month
        frame["month_index"] = month_order[month]
        frames.append(frame)

    merged = pd.concat(frames, ignore_index=True, sort=False)

    ordered_columns = [column for column in frames[0].columns if column in merged.columns]
    extra_columns = [column for column in merged.columns if column not in ordered_columns]
    merged = merged.loc[:, ordered_columns + extra_columns]
    return merged


def export_historical_search_terms(product: str) -> tuple[Path, Path, int]:
    output_dir = OUTPUT_ROOT / product
    output_dir.mkdir(parents=True, exist_ok=True)

    merged = build_historical_search_terms(product)

    parquet_path = output_dir / "historical_search_terms.parquet"
    csv_path = output_dir / "historical_search_terms.csv"

    merged.to_parquet(parquet_path, index=False)
    merged.to_csv(csv_path, index=False, encoding="utf-8")

    return parquet_path, csv_path, len(merged)
