"""Build deterministic demand-centric tables from interpreted ABA keyword data."""

from __future__ import annotations

import argparse
import logging
import re
import string
from pathlib import Path

import duckdb
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DUCKDB_PATH = PROJECT_ROOT / "data" / "output" / "aba.duckdb"
OUTPUT_DIR = PROJECT_ROOT / "data" / "output" / "demand"
LOG_DIR = PROJECT_ROOT / "logs"
LOG_PATH = LOG_DIR / "build_demand_engine.log"

NORMALIZED_TABLE = "normalized_keywords"
KEYWORD_METRICS_TABLE = "keyword_metrics_monthly"
KEYWORD_TREND_TABLE = "keyword_trend"
DEMAND_OBJECTS_TABLE = "demand_objects"

DEMAND_MASTER_TABLE = "demand_master"
DEMAND_KEYWORDS_TABLE = "demand_keywords"
DEMAND_MONTHLY_TABLE = "demand_monthly"

GIFT_PATTERN = r"(^|[^a-z0-9])(gift|gifts|present|presents)($|[^a-z0-9])"
PERSONALIZED_PATTERN = (
    r"(^|[^a-z0-9])"
    r"(personalized|personalised|custom|customized|customised|name|photo|picture|portrait|"
    r"engraved|engraving|monogram|monogrammed)"
    r"($|[^a-z0-9])"
)

INPUT_TABLES = [
    NORMALIZED_TABLE,
    KEYWORD_METRICS_TABLE,
    KEYWORD_TREND_TABLE,
    DEMAND_OBJECTS_TABLE,
]
OUTPUT_TABLES = [
    DEMAND_MONTHLY_TABLE,
    DEMAND_KEYWORDS_TABLE,
    DEMAND_MASTER_TABLE,
]
DEMAND_OBJECT_COLUMNS = {
    "demand_id",
    "raw_keyword",
    "normalized_keyword",
    "recipient",
    "profession",
    "interest",
    "pet",
    "occasion",
    "holiday",
    "theme",
    "lifestyle",
    "age_group",
    "gender",
    "month",
    "search_frequency_rank",
}

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build demand-centric tables from normalized keywords and demand objects."
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Drop existing demand engine tables before rebuilding.",
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=DUCKDB_PATH,
        help="Path to data/output/aba.duckdb.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help="Folder for demand CSV reports.",
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


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


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


def validate_inputs(connection: duckdb.DuckDBPyConnection) -> None:
    missing_tables = [table_name for table_name in INPUT_TABLES if not table_exists(connection, table_name)]
    if missing_tables:
        raise RuntimeError(f"Missing required input table(s): {', '.join(missing_tables)}")

    demand_columns = {
        row[1]
        for row in connection.execute(f"PRAGMA table_info({DEMAND_OBJECTS_TABLE})").fetchall()
    }
    missing_columns = sorted(DEMAND_OBJECT_COLUMNS - demand_columns)
    if missing_columns:
        raise RuntimeError(
            f"{DEMAND_OBJECTS_TABLE} is missing required columns: {', '.join(missing_columns)}"
        )


def ensure_rebuild_allowed(connection: duckdb.DuckDBPyConnection, rebuild: bool) -> None:
    existing_tables = [table_name for table_name in OUTPUT_TABLES if table_exists(connection, table_name)]
    if existing_tables and not rebuild:
        raise RuntimeError(
            "Demand engine tables already exist. Rerun with --rebuild to replace only "
            f"these tables: {', '.join(existing_tables)}"
        )


def drop_output_tables(connection: duckdb.DuckDBPyConnection) -> None:
    for table_name in OUTPUT_TABLES:
        logger.info("Dropping %s if it exists", table_name)
        connection.execute(f"DROP TABLE IF EXISTS {table_name}")


def title_case(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value or "").strip()
    if not text:
        return ""
    return string.capwords(text)


def clean_value(value: object, fallback: str = "") -> str:
    if pd.isna(value):
        return fallback
    text = str(value or "").strip()
    return text or fallback


def demand_name(row: pd.Series) -> str:
    primary_value = clean_value(row["primary_entity_value"], "unclassified")
    qualifier_value = clean_value(row["demand_qualifier_value"])

    if primary_value == "unclassified":
        base_name = "Unclassified"
    elif qualifier_value:
        base_name = title_case(f"{qualifier_value} {primary_value}")
    else:
        base_name = title_case(primary_value)

    primary_intent = str(row["primary_intent"])
    if primary_intent == "gift":
        return f"{base_name} Gift"
    if primary_intent == "personalized":
        return f"Personalized {base_name}"
    return f"{base_name} Demand"


def create_stage_tables(connection: duckdb.DuckDBPyConnection) -> None:
    logger.info("Creating demand keyword stage")
    connection.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE demand_keyword_stage AS
        WITH base AS (
            SELECT
                demand_id AS source_demand_id,
                raw_keyword,
                normalized_keyword,
                month,
                search_frequency_rank,
                CASE
                    WHEN regexp_matches(lower(coalesce(normalized_keyword, '')), {sql_literal(GIFT_PATTERN)})
                     AND regexp_matches(
                        lower(coalesce(normalized_keyword, '')),
                        '(^|[^a-z0-9])dog\\s+(mom|moms|mama|mother)($|[^a-z0-9])'
                     )
                    THEN 'dog mom'
                    WHEN regexp_matches(lower(coalesce(normalized_keyword, '')), {sql_literal(GIFT_PATTERN)})
                     AND regexp_matches(
                        lower(coalesce(normalized_keyword, '')),
                        '(^|[^a-z0-9])cat\\s+(mom|moms|mama|mother)($|[^a-z0-9])'
                     )
                    THEN 'cat mom'
                    WHEN recipient = 'mom' AND pet = 'dog' THEN 'dog mom'
                    WHEN recipient = 'mom' AND pet = 'cat' THEN 'cat mom'
                    WHEN pet = 'dog'
                     AND regexp_matches(lower(coalesce(normalized_keyword, '')), {sql_literal(GIFT_PATTERN)})
                     AND regexp_matches(
                        lower(coalesce(normalized_keyword, '')),
                        '(^|[^a-z0-9])(mom|moms|mother|mothers|mama|mommy)($|[^a-z0-9])'
                     )
                    THEN 'dog mom'
                    WHEN pet = 'cat'
                     AND regexp_matches(lower(coalesce(normalized_keyword, '')), {sql_literal(GIFT_PATTERN)})
                     AND regexp_matches(
                        lower(coalesce(normalized_keyword, '')),
                        '(^|[^a-z0-9])(mom|moms|mother|mothers|mama|mommy)($|[^a-z0-9])'
                     )
                    THEN 'cat mom'
                    WHEN recipient IS NOT NULL THEN recipient
                    WHEN regexp_matches(lower(coalesce(normalized_keyword, '')), {sql_literal(GIFT_PATTERN)})
                     AND regexp_matches(
                        lower(coalesce(normalized_keyword, '')),
                        '(^|[^a-z0-9])(grandma|grandmas|grandmother|grandmothers|nana|granny|grammy)($|[^a-z0-9])'
                     )
                    THEN 'grandma'
                    WHEN regexp_matches(lower(coalesce(normalized_keyword, '')), {sql_literal(GIFT_PATTERN)})
                     AND regexp_matches(
                        lower(coalesce(normalized_keyword, '')),
                        '(^|[^a-z0-9])(grandpa|grandpas|grandfather|grandfathers|papa|gramps)($|[^a-z0-9])'
                     )
                    THEN 'grandpa'
                    WHEN regexp_matches(lower(coalesce(normalized_keyword, '')), {sql_literal(GIFT_PATTERN)})
                     AND regexp_matches(
                        lower(coalesce(normalized_keyword, '')),
                        '(^|[^a-z0-9])(mom|moms|mother|mothers|mama|mommy)($|[^a-z0-9])'
                     )
                    THEN 'mom'
                    WHEN regexp_matches(lower(coalesce(normalized_keyword, '')), {sql_literal(GIFT_PATTERN)})
                     AND regexp_matches(
                        lower(coalesce(normalized_keyword, '')),
                        '(^|[^a-z0-9])(dad|dads|father|fathers|daddy)($|[^a-z0-9])'
                     )
                    THEN 'dad'
                    WHEN regexp_matches(lower(coalesce(normalized_keyword, '')), {sql_literal(GIFT_PATTERN)})
                     AND regexp_matches(
                        lower(coalesce(normalized_keyword, '')),
                        '(^|[^a-z0-9])best\\s+friends?($|[^a-z0-9])'
                     )
                    THEN 'best friend'
                    ELSE NULL
                END AS recipient,
                CASE
                    WHEN profession IS NOT NULL THEN profession
                    WHEN recipient IN ('teacher', 'nurse') THEN recipient
                    WHEN regexp_matches(lower(coalesce(normalized_keyword, '')), {sql_literal(GIFT_PATTERN)})
                     AND regexp_matches(
                        lower(coalesce(normalized_keyword, '')),
                        '(^|[^a-z0-9])(teacher|teachers|educator|educators)($|[^a-z0-9])'
                     )
                    THEN 'teacher'
                    WHEN regexp_matches(lower(coalesce(normalized_keyword, '')), {sql_literal(GIFT_PATTERN)})
                     AND regexp_matches(
                        lower(coalesce(normalized_keyword, '')),
                        '(^|[^a-z0-9])(nurse|nurses|rn)($|[^a-z0-9])'
                     )
                    THEN 'nurse'
                    ELSE NULL
                END AS profession,
                CASE
                    WHEN interest IS NOT NULL THEN interest
                    WHEN regexp_matches(lower(coalesce(normalized_keyword, '')), {sql_literal(GIFT_PATTERN)})
                     AND regexp_matches(
                        lower(coalesce(normalized_keyword, '')),
                        '(^|[^a-z0-9])(fishing|angler|anglers)($|[^a-z0-9])'
                     )
                    THEN 'fishing'
                    WHEN regexp_matches(lower(coalesce(normalized_keyword, '')), {sql_literal(GIFT_PATTERN)})
                     AND regexp_matches(
                        lower(coalesce(normalized_keyword, '')),
                        '(^|[^a-z0-9])(gardening|garden|gardener|gardeners)($|[^a-z0-9])'
                     )
                    THEN 'gardening'
                    ELSE NULL
                END AS interest,
                pet,
                occasion,
                holiday,
                theme,
                lifestyle,
                age_group,
                gender,
                CASE
                    WHEN regexp_matches(lower(coalesce(normalized_keyword, '')), {sql_literal(GIFT_PATTERN)})
                    THEN 'gift'
                    WHEN regexp_matches(lower(coalesce(normalized_keyword, '')), {sql_literal(PERSONALIZED_PATTERN)})
                    THEN 'personalized'
                    ELSE 'general'
                END AS primary_intent
            FROM {DEMAND_OBJECTS_TABLE}
        ),
        classified AS (
            SELECT
                *,
                CASE
                    WHEN recipient IS NOT NULL
                     AND NOT (recipient IN ('teacher', 'nurse') AND profession IS NOT NULL)
                    THEN 'recipient'
                    WHEN profession IS NOT NULL THEN 'profession'
                    WHEN recipient IS NOT NULL THEN 'recipient'
                    WHEN pet IS NOT NULL THEN 'pet'
                    WHEN interest IS NOT NULL THEN 'interest'
                    ELSE 'unclassified'
                END AS primary_entity_type,
                CASE
                    WHEN recipient IS NOT NULL
                     AND NOT (recipient IN ('teacher', 'nurse') AND profession IS NOT NULL)
                    THEN recipient
                    WHEN profession IS NOT NULL THEN profession
                    WHEN recipient IS NOT NULL THEN recipient
                    WHEN pet IS NOT NULL THEN pet
                    WHEN interest IS NOT NULL THEN interest
                    ELSE 'unclassified'
                END AS primary_entity_value
            FROM base
        ),
        qualified AS (
            SELECT
                *,
                CASE
                    WHEN primary_entity_type = 'recipient'
                     AND interest IS NOT NULL
                     AND position(interest IN primary_entity_value) = 0
                    THEN 'interest'
                    WHEN primary_entity_type = 'recipient'
                     AND pet IS NOT NULL
                     AND position(pet IN primary_entity_value) = 0
                    THEN 'pet'
                    ELSE NULL
                END AS demand_qualifier_type,
                CASE
                    WHEN primary_entity_type = 'recipient'
                     AND interest IS NOT NULL
                     AND position(interest IN primary_entity_value) = 0
                    THEN interest
                    WHEN primary_entity_type = 'recipient'
                     AND pet IS NOT NULL
                     AND position(pet IN primary_entity_value) = 0
                    THEN pet
                    ELSE NULL
                END AS demand_qualifier_value
            FROM classified
        )
        SELECT
            concat(
                primary_intent,
                '|',
                primary_entity_type,
                '|',
                coalesce(demand_qualifier_type, ''),
                '|',
                coalesce(demand_qualifier_value, ''),
                '|',
                primary_entity_value
            ) AS demand_key,
            *
        FROM qualified
        """
    )

    logger.info("Creating demand monthly stage")
    connection.execute(
        """
        CREATE OR REPLACE TEMP TABLE demand_monthly_stage AS
        SELECT
            demand_key,
            month,
            count(*) AS keyword_count,
            min(search_frequency_rank) AS best_rank,
            avg(search_frequency_rank) AS avg_rank
        FROM demand_keyword_stage
        GROUP BY demand_key, month
        """
    )


def mode_expression(column_name: str) -> str:
    return f"""
        (
            SELECT value
            FROM (
                SELECT
                    {column_name} AS value,
                    count(*) AS value_count,
                    min(search_frequency_rank) AS best_rank
                FROM demand_keyword_stage AS mode_source
                WHERE mode_source.demand_key = metrics.demand_key
                  AND {column_name} IS NOT NULL
                GROUP BY {column_name}
                ORDER BY value_count DESC, best_rank NULLS LAST, value
                LIMIT 1
            )
        ) AS {column_name}
    """


def create_master_stage(connection: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    logger.info("Aggregating demand master stage")
    mode_columns = [
        "recipient",
        "profession",
        "interest",
        "pet",
        "occasion",
        "holiday",
        "theme",
        "lifestyle",
        "age_group",
        "gender",
    ]
    modes = ",\n            ".join(mode_expression(column_name) for column_name in mode_columns)

    return connection.execute(
        f"""
        WITH metrics AS (
            SELECT
                demand_key,
                min(primary_intent) AS primary_intent,
                min(primary_entity_type) AS primary_entity_type,
                min(primary_entity_value) AS primary_entity_value,
                min(demand_qualifier_type) AS demand_qualifier_type,
                min(demand_qualifier_value) AS demand_qualifier_value,
                count(*) AS keyword_count,
                min(search_frequency_rank) AS best_search_rank,
                avg(search_frequency_rank) AS avg_search_rank,
                min(month) AS first_month,
                max(month) AS last_month,
                count(DISTINCT month) AS active_months
            FROM demand_keyword_stage
            GROUP BY demand_key
        ),
        first_last AS (
            SELECT
                metrics.demand_key,
                first_month.keyword_count AS first_month_keyword_count,
                last_month.keyword_count AS last_month_keyword_count
            FROM metrics
            LEFT JOIN demand_monthly_stage AS first_month
              ON metrics.demand_key = first_month.demand_key
             AND metrics.first_month = first_month.month
            LEFT JOIN demand_monthly_stage AS last_month
              ON metrics.demand_key = last_month.demand_key
             AND metrics.last_month = last_month.month
        ),
        keyword_trends AS (
            SELECT
                stage.demand_key,
                sum(CASE WHEN trend.trend_label = 'growing' THEN 1 ELSE 0 END) AS growing_keywords,
                sum(CASE WHEN trend.trend_label = 'declining' THEN 1 ELSE 0 END) AS declining_keywords
            FROM (
                SELECT DISTINCT demand_key, normalized_keyword
                FROM demand_keyword_stage
            ) AS stage
            LEFT JOIN {KEYWORD_TREND_TABLE} AS trend
              ON stage.normalized_keyword = trend.normalized_search_term
            GROUP BY stage.demand_key
        ),
        global_month AS (
            SELECT max(month) AS latest_month
            FROM demand_keyword_stage
        )
        SELECT
            metrics.demand_key,
            metrics.primary_intent,
            metrics.primary_entity_type,
            metrics.primary_entity_value,
            metrics.demand_qualifier_type,
            metrics.demand_qualifier_value,
            {modes},
            metrics.keyword_count,
            metrics.best_search_rank,
            metrics.avg_search_rank,
            metrics.first_month,
            metrics.last_month,
            metrics.active_months,
            CASE
                WHEN first_last.first_month_keyword_count IS NULL
                  OR first_last.first_month_keyword_count = 0
                THEN NULL
                ELSE round(
                    (
                        (first_last.last_month_keyword_count - first_last.first_month_keyword_count)
                        * 100.0
                    ) / first_last.first_month_keyword_count,
                    2
                )
            END AS growth_percent,
            CASE
                WHEN metrics.active_months = 1
                 AND metrics.last_month = global_month.latest_month
                THEN 'emerging'
                WHEN first_last.first_month_keyword_count > 0
                 AND (
                    (first_last.last_month_keyword_count - first_last.first_month_keyword_count)
                    * 100.0
                 ) / first_last.first_month_keyword_count >= 25
                THEN 'growing'
                WHEN first_last.first_month_keyword_count > 0
                 AND (
                    (first_last.last_month_keyword_count - first_last.first_month_keyword_count)
                    * 100.0
                 ) / first_last.first_month_keyword_count <= -25
                THEN 'declining'
                WHEN coalesce(keyword_trends.growing_keywords, 0) > coalesce(keyword_trends.declining_keywords, 0)
                THEN 'growing'
                WHEN coalesce(keyword_trends.declining_keywords, 0) > coalesce(keyword_trends.growing_keywords, 0)
                THEN 'declining'
                ELSE 'stable'
            END AS trend_label
        FROM metrics
        LEFT JOIN first_last
          ON metrics.demand_key = first_last.demand_key
        LEFT JOIN keyword_trends
          ON metrics.demand_key = keyword_trends.demand_key
        CROSS JOIN global_month
        ORDER BY
            metrics.best_search_rank NULLS LAST,
            metrics.keyword_count DESC,
            metrics.demand_key
        """
    ).df()


def build_demand_master(connection: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    master_stage = create_master_stage(connection)
    master_stage.insert(
        0,
        "demand_id",
        [f"DM{index:06d}" for index in range(1, len(master_stage) + 1)],
    )
    master_stage.insert(
        1,
        "demand_name",
        master_stage.apply(demand_name, axis=1),
    )

    demand_master = master_stage[
        [
            "demand_id",
            "demand_name",
            "recipient",
            "profession",
            "interest",
            "pet",
            "occasion",
            "holiday",
            "theme",
            "lifestyle",
            "age_group",
            "gender",
            "primary_intent",
            "keyword_count",
            "best_search_rank",
            "avg_search_rank",
            "first_month",
            "last_month",
            "active_months",
            "growth_percent",
            "trend_label",
            "demand_key",
        ]
    ].copy()

    connection.register("demand_master_frame", demand_master)
    connection.execute(
        f"""
        CREATE TABLE {DEMAND_MASTER_TABLE} AS
        SELECT
            demand_id,
            demand_name,
            recipient,
            profession,
            interest,
            pet,
            occasion,
            holiday,
            theme,
            lifestyle,
            age_group,
            gender,
            primary_intent,
            keyword_count,
            best_search_rank,
            avg_search_rank,
            first_month,
            last_month,
            active_months,
            growth_percent,
            trend_label
        FROM demand_master_frame
        """
    )
    connection.execute(
        """
        CREATE OR REPLACE TEMP TABLE demand_id_map AS
        SELECT demand_key, demand_id
        FROM demand_master_frame
        """
    )
    connection.unregister("demand_master_frame")
    logger.info("Built %s with %s rows", DEMAND_MASTER_TABLE, f"{len(demand_master):,}")
    return demand_master


def build_demand_keywords(connection: duckdb.DuckDBPyConnection) -> int:
    logger.info("Building %s", DEMAND_KEYWORDS_TABLE)
    connection.execute(
        f"""
        CREATE TABLE {DEMAND_KEYWORDS_TABLE} AS
        SELECT
            demand_id_map.demand_id,
            demand_keyword_stage.raw_keyword,
            demand_keyword_stage.normalized_keyword,
            demand_keyword_stage.month,
            demand_keyword_stage.search_frequency_rank
        FROM demand_keyword_stage
        JOIN demand_id_map
          ON demand_keyword_stage.demand_key = demand_id_map.demand_key
        """
    )
    row_count = connection.execute(f"SELECT count(*) FROM {DEMAND_KEYWORDS_TABLE}").fetchone()[0]
    logger.info("Built %s with %s rows", DEMAND_KEYWORDS_TABLE, f"{row_count:,}")
    return int(row_count)


def build_demand_monthly(connection: duckdb.DuckDBPyConnection) -> int:
    logger.info("Building %s", DEMAND_MONTHLY_TABLE)
    connection.execute(
        f"""
        CREATE TABLE {DEMAND_MONTHLY_TABLE} AS
        SELECT
            demand_id_map.demand_id,
            demand_monthly_stage.month,
            demand_monthly_stage.keyword_count,
            demand_monthly_stage.best_rank,
            demand_monthly_stage.avg_rank
        FROM demand_monthly_stage
        JOIN demand_id_map
          ON demand_monthly_stage.demand_key = demand_id_map.demand_key
        ORDER BY demand_id_map.demand_id, demand_monthly_stage.month
        """
    )
    row_count = connection.execute(f"SELECT count(*) FROM {DEMAND_MONTHLY_TABLE}").fetchone()[0]
    logger.info("Built %s with %s rows", DEMAND_MONTHLY_TABLE, f"{row_count:,}")
    return int(row_count)


def export_query_to_csv(
    connection: duckdb.DuckDBPyConnection,
    query: str,
    output_path: Path,
    chunk_size: int = 100_000,
) -> int:
    cursor = connection.execute(query)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    total_rows = 0
    write_header = True
    while True:
        frame = cursor.fetch_df_chunk(chunk_size)
        if frame.empty:
            break
        frame.to_csv(
            output_path,
            mode="w" if write_header else "a",
            header=write_header,
            index=False,
        )
        total_rows += len(frame)
        write_header = False

    if write_header:
        pd.DataFrame().to_csv(output_path, index=False)

    return total_rows


def export_reports(connection: duckdb.DuckDBPyConnection, output_dir: Path) -> None:
    logger.info("Exporting demand reports to %s", output_dir.relative_to(PROJECT_ROOT))
    output_dir.mkdir(parents=True, exist_ok=True)

    exports = {
        "demand_master.csv": f"SELECT * FROM {DEMAND_MASTER_TABLE} ORDER BY demand_id",
        "demand_keywords.csv": f"SELECT * FROM {DEMAND_KEYWORDS_TABLE} ORDER BY demand_id, month, search_frequency_rank NULLS LAST, normalized_keyword",
        "demand_monthly.csv": f"SELECT * FROM {DEMAND_MONTHLY_TABLE} ORDER BY demand_id, month",
        "top_demands.csv": f"""
            SELECT *
            FROM {DEMAND_MASTER_TABLE}
            ORDER BY
                best_search_rank NULLS LAST,
                keyword_count DESC,
                CASE trend_label
                    WHEN 'growing' THEN 1
                    WHEN 'emerging' THEN 2
                    WHEN 'stable' THEN 3
                    WHEN 'declining' THEN 4
                    ELSE 5
                END,
                demand_id
        """,
    }

    for file_name, query in exports.items():
        row_count = export_query_to_csv(connection, query, output_dir / file_name)
        logger.info("Exported %s with %s rows", file_name, f"{row_count:,}")


def build_demand_engine(
    database_path: Path,
    output_dir: Path,
    rebuild: bool,
) -> None:
    if not database_path.exists():
        raise FileNotFoundError(f"DuckDB database not found: {database_path}")

    with duckdb.connect(str(database_path)) as connection:
        validate_inputs(connection)
        ensure_rebuild_allowed(connection, rebuild)
        if rebuild:
            drop_output_tables(connection)

        create_stage_tables(connection)
        build_demand_master(connection)
        build_demand_keywords(connection)
        build_demand_monthly(connection)
        export_reports(connection, output_dir)


def main() -> None:
    configure_logging()
    args = parse_args()
    logger.info("Starting Demand Engine build")
    build_demand_engine(
        database_path=args.database.resolve(),
        output_dir=args.output_dir.resolve(),
        rebuild=args.rebuild,
    )
    logger.info("Demand Engine build complete")
    logger.info("Build log: %s", LOG_PATH.relative_to(PROJECT_ROOT))


if __name__ == "__main__":
    main()
