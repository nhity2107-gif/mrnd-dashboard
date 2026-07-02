"""Build research-model tables from imported Amazon Brand Analytics keywords."""

from __future__ import annotations

import argparse
import logging
import re
from pathlib import Path

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "data" / "output"
LOG_DIR = PROJECT_ROOT / "logs"
DUCKDB_PATH = OUTPUT_DIR / "aba.duckdb"
LOG_PATH = LOG_DIR / "build_research_model.log"

RAW_KEYWORDS_TABLE = "raw_keywords"
NORMALIZED_KEYWORDS_TABLE = "normalized_keywords"
KEYWORD_METRICS_TABLE = "keyword_metrics_monthly"
KEYWORD_TREND_TABLE = "keyword_trend"

NON_ALNUM_PATTERN = re.compile(r"[^a-z0-9]+")
UNDERSCORE_PATTERN = re.compile(r"_+")

REQUIRED_RAW_COLUMNS = {
    "search_frequency_rank": "Search frequency rank",
    "search_term": "Search term",
    "reporting_date": "Reporting date",
    "month": "Month",
    "source_file": "Source file",
    "imported_at": "Imported timestamp",
}

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build research-model tables from raw Amazon Brand Analytics imports."
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Drop derived research tables before rebuilding them.",
    )
    return parser.parse_args()


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


def connect_db() -> duckdb.DuckDBPyConnection:
    if not DUCKDB_PATH.exists():
        raise FileNotFoundError(f"DuckDB database not found: {DUCKDB_PATH}")

    logger.info("Connecting to %s", DUCKDB_PATH.relative_to(PROJECT_ROOT))
    return duckdb.connect(str(DUCKDB_PATH))


def normalize_column_name(column_name: str) -> str:
    normalized = column_name.strip().lower()
    normalized = re.sub(r"#\s*(\d+)", r" \1", normalized)
    normalized = NON_ALNUM_PATTERN.sub("_", normalized)
    normalized = UNDERSCORE_PATTERN.sub("_", normalized).strip("_")
    return normalized or "column"


def quote_identifier(identifier: str) -> str:
    return f'"{identifier.replace("\"", "\"\"")}"'


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


def raw_column_lookup(connection: duckdb.DuckDBPyConnection) -> dict[str, str]:
    if not table_exists(connection, RAW_KEYWORDS_TABLE):
        raise RuntimeError(f"Required table not found: {RAW_KEYWORDS_TABLE}")

    rows = connection.execute(f"PRAGMA table_info({RAW_KEYWORDS_TABLE})").fetchall()
    lookup: dict[str, str] = {}

    for row in rows:
        original_name = row[1]
        normalized_name = normalize_column_name(original_name)
        lookup.setdefault(normalized_name, original_name)

    missing_columns = [
        label
        for normalized_name, label in REQUIRED_RAW_COLUMNS.items()
        if normalized_name not in lookup
    ]
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise RuntimeError(f"raw_keywords is missing required columns: {missing}")

    return lookup


def raw_column_expression(lookup: dict[str, str], normalized_name: str) -> str:
    return quote_identifier(lookup[normalized_name])


def normalize_expression(raw_term_expression: str) -> str:
    expression = f"lower(trim(coalesce(cast({raw_term_expression} AS VARCHAR), '')))"

    replacements = [
        (r"\bt[- ]?shirts?\b", "shirt"),
        (r"\btshirt\b", "shirt"),
        (r"\btee\b", "shirt"),
        (r"\bpersonalised\b", "personalized"),
        (r"\bcustomised\b", "customized"),
    ]

    for pattern, replacement in replacements:
        expression = f"regexp_replace({expression}, '{pattern}', '{replacement}', 'g')"

    expression = f"regexp_replace({expression}, '[^a-z0-9\\s'']+', ' ', 'g')"

    singular_replacements = [
        (r"\bgifts\b", "gift"),
        (r"\bshirts\b", "shirt"),
        (r"\bmugs\b", "mug"),
        (r"\btumblers\b", "tumbler"),
        (r"\bornaments\b", "ornament"),
        (r"\bblankets\b", "blanket"),
    ]

    for pattern, replacement in singular_replacements:
        expression = f"regexp_replace({expression}, '{pattern}', '{replacement}', 'g')"

    return f"nullif(trim(regexp_replace({expression}, '\\s+', ' ', 'g')), '')"


def normalize_terms(raw_term_expression: str) -> str:
    return normalize_expression(raw_term_expression)


def drop_research_tables(connection: duckdb.DuckDBPyConnection) -> None:
    for table_name in [
        KEYWORD_TREND_TABLE,
        KEYWORD_METRICS_TABLE,
        NORMALIZED_KEYWORDS_TABLE,
    ]:
        logger.info("Dropping %s if it exists", table_name)
        connection.execute(f"DROP TABLE IF EXISTS {table_name}")


def build_normalized_keywords(connection: duckdb.DuckDBPyConnection) -> int:
    logger.info("Building %s from %s", NORMALIZED_KEYWORDS_TABLE, RAW_KEYWORDS_TABLE)
    lookup = raw_column_lookup(connection)

    rank_expr = raw_column_expression(lookup, "search_frequency_rank")
    term_expr = raw_column_expression(lookup, "search_term")
    reporting_date_expr = raw_column_expression(lookup, "reporting_date")
    month_expr = raw_column_expression(lookup, "month")
    source_file_expr = raw_column_expression(lookup, "source_file")
    imported_at_expr = raw_column_expression(lookup, "imported_at")

    normalized_term_expr = normalize_terms(term_expr)

    connection.execute(
        f"""
        CREATE OR REPLACE TABLE {NORMALIZED_KEYWORDS_TABLE} AS
        SELECT
            try_cast({rank_expr} AS BIGINT) AS search_frequency_rank,
            cast({term_expr} AS VARCHAR) AS raw_search_term,
            {normalized_term_expr} AS normalized_search_term,
            try_cast({reporting_date_expr} AS DATE) AS reporting_date,
            cast({month_expr} AS VARCHAR) AS month,
            cast({source_file_expr} AS VARCHAR) AS source_file,
            try_cast({imported_at_expr} AS TIMESTAMP) AS imported_at
        FROM {RAW_KEYWORDS_TABLE}
        """
    )

    row_count = connection.execute(
        f"SELECT count(*) FROM {NORMALIZED_KEYWORDS_TABLE}"
    ).fetchone()[0]
    logger.info("Built %s with %s rows", NORMALIZED_KEYWORDS_TABLE, f"{row_count:,}")
    return int(row_count)


def build_keyword_metrics_monthly(connection: duckdb.DuckDBPyConnection) -> int:
    logger.info("Building %s", KEYWORD_METRICS_TABLE)
    connection.execute(
        f"""
        CREATE OR REPLACE TABLE {KEYWORD_METRICS_TABLE} AS
        WITH base AS (
            SELECT
                normalized_search_term,
                month,
                search_frequency_rank,
                raw_search_term
            FROM {NORMALIZED_KEYWORDS_TABLE}
            WHERE normalized_search_term IS NOT NULL
              AND month IS NOT NULL
        ),
        metrics AS (
            SELECT
                normalized_search_term,
                month,
                min(search_frequency_rank) AS min_search_frequency_rank,
                avg(search_frequency_rank) AS avg_search_frequency_rank,
                count(*) AS keyword_count
            FROM base
            GROUP BY normalized_search_term, month
        ),
        ranked_examples AS (
            SELECT
                normalized_search_term,
                month,
                raw_search_term,
                row_number() OVER (
                    PARTITION BY normalized_search_term, month
                    ORDER BY min(search_frequency_rank), raw_search_term
                ) AS example_rank
            FROM base
            WHERE raw_search_term IS NOT NULL
            GROUP BY normalized_search_term, month, raw_search_term
        ),
        examples AS (
            SELECT
                normalized_search_term,
                month,
                string_agg(raw_search_term, ' | ' ORDER BY example_rank) AS raw_keyword_examples
            FROM ranked_examples
            WHERE example_rank <= 5
            GROUP BY normalized_search_term, month
        )
        SELECT
            metrics.normalized_search_term,
            metrics.month,
            metrics.min_search_frequency_rank,
            metrics.avg_search_frequency_rank,
            metrics.keyword_count,
            examples.raw_keyword_examples
        FROM metrics
        LEFT JOIN examples
          ON metrics.normalized_search_term = examples.normalized_search_term
         AND metrics.month = examples.month
        """
    )

    row_count = connection.execute(f"SELECT count(*) FROM {KEYWORD_METRICS_TABLE}").fetchone()[0]
    logger.info("Built %s with %s rows", KEYWORD_METRICS_TABLE, f"{row_count:,}")
    return int(row_count)


def build_keyword_trend(connection: duckdb.DuckDBPyConnection) -> int:
    logger.info("Building %s", KEYWORD_TREND_TABLE)
    connection.execute(
        f"""
        CREATE OR REPLACE TABLE {KEYWORD_TREND_TABLE} AS
        WITH monthly AS (
            SELECT
                normalized_search_term,
                month,
                min_search_frequency_rank
            FROM {KEYWORD_METRICS_TABLE}
            WHERE normalized_search_term IS NOT NULL
              AND month IS NOT NULL
              AND min_search_frequency_rank IS NOT NULL
        ),
        month_bounds AS (
            SELECT
                min(month) AS first_available_month,
                max(month) AS last_available_month
            FROM monthly
        ),
        ranked AS (
            SELECT
                normalized_search_term,
                month,
                min_search_frequency_rank,
                row_number() OVER (
                    PARTITION BY normalized_search_term
                    ORDER BY month
                ) AS first_rank_order,
                row_number() OVER (
                    PARTITION BY normalized_search_term
                    ORDER BY month DESC
                ) AS last_rank_order,
                lag(min_search_frequency_rank) OVER (
                    PARTITION BY normalized_search_term
                    ORDER BY month
                ) AS previous_rank
            FROM monthly
        ),
        summary AS (
            SELECT
                normalized_search_term,
                count(*) AS months_present,
                min(month) AS first_month,
                max(month) AS last_month,
                min(min_search_frequency_rank) AS best_rank,
                max(min_search_frequency_rank) AS worst_rank,
                max(CASE WHEN first_rank_order = 1 THEN min_search_frequency_rank END) AS first_rank,
                max(CASE WHEN last_rank_order = 1 THEN min_search_frequency_rank END) AS last_rank,
                sum(CASE WHEN previous_rank IS NOT NULL THEN 1 ELSE 0 END) AS comparisons,
                sum(
                    CASE
                        WHEN previous_rank IS NOT NULL
                         AND min_search_frequency_rank < previous_rank
                        THEN 1
                        ELSE 0
                    END
                ) AS improving_steps,
                sum(
                    CASE
                        WHEN previous_rank IS NOT NULL
                         AND min_search_frequency_rank > previous_rank
                        THEN 1
                        ELSE 0
                    END
                ) AS worsening_steps
            FROM ranked
            GROUP BY normalized_search_term
        )
        SELECT
            summary.normalized_search_term,
            summary.months_present,
            summary.first_month,
            summary.last_month,
            summary.best_rank,
            summary.worst_rank,
            summary.last_rank - summary.first_rank AS rank_change,
            CASE
                WHEN summary.first_month > month_bounds.first_available_month
                 AND summary.last_month = month_bounds.last_available_month
                THEN 'emerging'
                WHEN summary.comparisons > 0
                 AND summary.improving_steps = summary.comparisons
                THEN 'growing'
                WHEN summary.comparisons > 0
                 AND summary.worsening_steps = summary.comparisons
                THEN 'declining'
                ELSE 'stable'
            END AS trend_label
        FROM summary
        CROSS JOIN month_bounds
        """
    )

    row_count = connection.execute(f"SELECT count(*) FROM {KEYWORD_TREND_TABLE}").fetchone()[0]
    logger.info("Built %s with %s rows", KEYWORD_TREND_TABLE, f"{row_count:,}")
    return int(row_count)


def main() -> None:
    configure_logging()
    args = parse_args()

    logger.info("Starting research data model build")
    with connect_db() as connection:
        if args.rebuild:
            drop_research_tables(connection)

        build_normalized_keywords(connection)
        build_keyword_metrics_monthly(connection)
        build_keyword_trend(connection)

    logger.info("Research data model build complete")
    logger.info("Build log: %s", LOG_PATH.relative_to(PROJECT_ROOT))


if __name__ == "__main__":
    main()
