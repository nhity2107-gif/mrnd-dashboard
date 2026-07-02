"""Import Amazon Brand Analytics CSV exports into Parquet and DuckDB."""

from __future__ import annotations

import argparse
import logging
import re
from datetime import UTC, datetime
from pathlib import Path

import duckdb
import polars as pl


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUT_DIR = PROJECT_ROOT / "data" / "output"
LOG_DIR = PROJECT_ROOT / "logs"
LOG_PATH = LOG_DIR / "import_aba.log"
DUCKDB_PATH = OUTPUT_DIR / "aba.duckdb"
TABLE_NAME = "raw_keywords"
IMPORT_HISTORY_TABLE = "import_history"
HEADER_MARKER = "Search Frequency Rank"

MONTH_PATTERN = re.compile(r"(?P<year>\d{4})_(?P<month>\d{2})_(?P<day>\d{2})")
NON_ALNUM_PATTERN = re.compile(r"[^a-z0-9]+")
UNDERSCORE_PATTERN = re.compile(r"_+")

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import raw Amazon Brand Analytics CSV files into Parquet and DuckDB."
    )
    parser.add_argument(
        "--sample",
        type=positive_int,
        default=None,
        metavar="N",
        help="Import only the first N data rows from each CSV.",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Drop the DuckDB raw_keywords table and remove generated Parquet files first.",
    )
    return parser.parse_args()


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("--sample must be a positive integer")
    return parsed


def configure_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(LOG_PATH, encoding="utf-8"),
        ],
        force=True,
    )


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def normalize_column_name(column_name: str) -> str:
    normalized = column_name.strip().lower()
    normalized = re.sub(r"#\s*(\d+)", r" \1", normalized)
    normalized = NON_ALNUM_PATTERN.sub("_", normalized)
    normalized = UNDERSCORE_PATTERN.sub("_", normalized).strip("_")
    return normalized or "column"


def normalize_column_names(column_names: list[str]) -> list[str]:
    normalized_names = []
    seen: dict[str, int] = {}

    for column_name in column_names:
        base_name = normalize_column_name(column_name)
        seen[base_name] = seen.get(base_name, 0) + 1

        if seen[base_name] == 1:
            normalized_names.append(base_name)
        else:
            normalized_names.append(f"{base_name}_{seen[base_name]}")

    return normalized_names


def detect_month(csv_path: Path) -> str:
    match = MONTH_PATTERN.search(csv_path.name)
    if match is None:
        raise ValueError(f"Could not detect month from filename: {csv_path.name}")

    year = match.group("year")
    month = int(match.group("month"))
    if month < 1 or month > 12:
        raise ValueError(f"Invalid month in filename: {csv_path.name}")

    return f"{year}-{month:02d}"


def find_header_skip_rows(csv_path: Path) -> int:
    """Return the number of leading CSV rows before the ABA header."""
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row_index, line in enumerate(handle):
            if HEADER_MARKER in line:
                return row_index
            if row_index >= 25:
                break

    return 0


def raw_csv_files() -> list[Path]:
    return sorted(RAW_DIR.glob("*.csv"))


def prepare_output_dirs() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def rebuild_outputs(connection: duckdb.DuckDBPyConnection) -> None:
    logger.info("Rebuild requested; dropping %s if it exists", TABLE_NAME)
    connection.execute(f"DROP TABLE IF EXISTS {TABLE_NAME}")

    generated_files = sorted(PROCESSED_DIR.glob("*.parquet"))
    for parquet_path in generated_files:
        logger.info("Removing generated Parquet file %s", parquet_path.relative_to(PROJECT_ROOT))
        parquet_path.unlink()


def table_exists(connection: duckdb.DuckDBPyConnection, table_name: str) -> bool:
    result = connection.execute(
        """
        SELECT count(*)
        FROM information_schema.tables
        WHERE table_schema = current_schema()
          AND table_name = ?
        """,
        [table_name],
    ).fetchone()
    return bool(result and result[0])


def ensure_import_history_table(connection: duckdb.DuckDBPyConnection) -> None:
    connection.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {IMPORT_HISTORY_TABLE} (
            file_name VARCHAR,
            month VARCHAR,
            rows BIGINT,
            started_at TIMESTAMP,
            finished_at TIMESTAMP,
            duration_seconds DOUBLE,
            status VARCHAR
        )
        """
    )


def record_import_history(
    connection: duckdb.DuckDBPyConnection,
    file_name: str,
    month: str | None,
    rows: int,
    started_at: datetime,
    finished_at: datetime,
    status: str,
) -> None:
    duration_seconds = (finished_at - started_at).total_seconds()
    connection.execute(
        f"""
        INSERT INTO {IMPORT_HISTORY_TABLE}
        (file_name, month, rows, started_at, finished_at, duration_seconds, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [file_name, month, rows, started_at, finished_at, duration_seconds, status],
    )


def cast_expressions(column_names: list[str]) -> list[pl.Expr]:
    expressions: list[pl.Expr] = []
    column_set = set(column_names)

    if "search_frequency_rank" in column_set:
        expressions.append(pl.col("search_frequency_rank").cast(pl.Int64, strict=False))

    for column_name in column_names:
        if column_name.endswith("click_share"):
            expressions.append(pl.col(column_name).cast(pl.Float64, strict=False))
        elif column_name.endswith("conversion_share"):
            expressions.append(pl.col(column_name).cast(pl.Float64, strict=False))

    if "reporting_date" in column_set:
        expressions.append(
            pl.col("reporting_date").str.strptime(pl.Date, "%Y-%m-%d", strict=False)
        )

    if "source_file" in column_set:
        expressions.append(pl.col("source_file").cast(pl.Utf8))
    if "month" in column_set:
        expressions.append(pl.col("month").cast(pl.Utf8))
    if "imported_at" in column_set:
        expressions.append(pl.col("imported_at").cast(pl.Datetime("us")))

    return expressions


def write_parquet(csv_path: Path, parquet_path: Path, month: str, sample: int | None) -> None:
    skip_rows = find_header_skip_rows(csv_path)
    imported_at = utc_now()

    if parquet_path.exists():
        parquet_path.unlink()

    lazy_frame = (
        pl.scan_csv(
            csv_path,
            has_header=True,
            skip_rows=skip_rows,
            infer_schema=False,
            n_rows=sample,
            with_column_names=normalize_column_names,
        )
        .with_columns(
            [
                pl.lit(csv_path.name).alias("source_file"),
                pl.lit(month).alias("month"),
                pl.lit(imported_at).alias("imported_at"),
            ]
        )
    )

    expressions = cast_expressions(lazy_frame.collect_schema().names())
    if expressions:
        lazy_frame = lazy_frame.with_columns(expressions)

    lazy_frame.sink_parquet(parquet_path, compression="zstd", mkdir=True)


def load_parquet_into_duckdb(
    connection: duckdb.DuckDBPyConnection,
    parquet_path: Path,
    source_file: str,
    month: str,
) -> int:
    row_count = connection.execute(
        "SELECT count(*) FROM read_parquet(?)",
        [str(parquet_path)],
    ).fetchone()[0]

    if table_exists(connection, TABLE_NAME):
        connection.execute(
            f"DELETE FROM {TABLE_NAME} WHERE source_file = ? AND month = ?",
            [source_file, month],
        )
        connection.execute(
            f"INSERT INTO {TABLE_NAME} BY NAME SELECT * FROM read_parquet(?)",
            [str(parquet_path)],
        )
    else:
        connection.execute(
            f"CREATE TABLE {TABLE_NAME} AS SELECT * FROM read_parquet(?)",
            [str(parquet_path)],
        )

    return int(row_count)


def import_file(
    connection: duckdb.DuckDBPyConnection,
    csv_path: Path,
    sample: int | None,
) -> int:
    started_at = utc_now()
    month: str | None = None
    row_count = 0

    try:
        month = detect_month(csv_path)
        parquet_path = PROCESSED_DIR / csv_path.with_suffix(".parquet").name

        logger.info("Converting %s to %s", csv_path.name, parquet_path.name)
        write_parquet(csv_path, parquet_path, month, sample)

        logger.info("Loading %s into DuckDB table %s", parquet_path.name, TABLE_NAME)
        row_count = load_parquet_into_duckdb(connection, parquet_path, csv_path.name, month)

        finished_at = utc_now()
        record_import_history(
            connection,
            csv_path.name,
            month,
            row_count,
            started_at,
            finished_at,
            "success",
        )
        logger.info("Imported %s rows from %s for month %s", f"{row_count:,}", csv_path.name, month)
        return row_count
    except Exception:
        finished_at = utc_now()
        record_import_history(
            connection,
            csv_path.name,
            month,
            row_count,
            started_at,
            finished_at,
            "failed",
        )
        logger.exception("Failed to import %s", csv_path.name)
        raise


def run_import(sample: int | None, rebuild: bool) -> int:
    prepare_output_dirs()

    files = raw_csv_files()
    if not files:
        logger.warning("No CSV files found in %s", RAW_DIR.relative_to(PROJECT_ROOT))
        return 0

    logger.info("Found %s CSV file(s) in %s", len(files), RAW_DIR.relative_to(PROJECT_ROOT))
    if sample is not None:
        logger.info("Sample mode enabled; importing first %s rows per CSV", f"{sample:,}")

    total_rows = 0
    with duckdb.connect(str(DUCKDB_PATH)) as connection:
        if rebuild:
            rebuild_outputs(connection)
        ensure_import_history_table(connection)

        for index, csv_path in enumerate(files, start=1):
            logger.info("[%s/%s] Processing %s", index, len(files), csv_path.name)
            total_rows += import_file(connection, csv_path, sample)

    logger.info("Import complete; total rows imported: %s", f"{total_rows:,}")
    logger.info("DuckDB database: %s", DUCKDB_PATH.relative_to(PROJECT_ROOT))
    logger.info("Import log: %s", LOG_PATH.relative_to(PROJECT_ROOT))
    return total_rows


def main() -> None:
    configure_logging()
    args = parse_args()
    run_import(sample=args.sample, rebuild=args.rebuild)


if __name__ == "__main__":
    main()
