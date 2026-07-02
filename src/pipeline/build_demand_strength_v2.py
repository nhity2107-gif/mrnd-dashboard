"""Build rank-based Demand Strength V2 tables from ABA demand objects."""

from __future__ import annotations

import argparse
import logging
import math
import string
from pathlib import Path

import duckdb
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DUCKDB_PATH = PROJECT_ROOT / "data" / "output" / "aba.duckdb"
OUTPUT_DIR = PROJECT_ROOT / "data" / "output" / "demand_v2"
LOG_DIR = PROJECT_ROOT / "logs"
LOG_PATH = LOG_DIR / "build_demand_strength_v2.log"

DEMAND_OBJECTS_TABLE = "demand_objects"
NORMALIZED_TABLE = "normalized_keywords"
KEYWORD_METRICS_TABLE = "keyword_metrics_monthly"

DEMAND_MASTER_TABLE = "demand_master_v2"
DEMAND_KEYWORDS_TABLE = "demand_keywords_v2"
DEMAND_MONTHLY_TABLE = "demand_monthly_v2"
DEMAND_PROFILE_TABLE = "demand_profile_v2"

INPUT_TABLES = [
    DEMAND_OBJECTS_TABLE,
    NORMALIZED_TABLE,
    KEYWORD_METRICS_TABLE,
]
OUTPUT_TABLES = [
    DEMAND_PROFILE_TABLE,
    DEMAND_MONTHLY_TABLE,
    DEMAND_KEYWORDS_TABLE,
    DEMAND_MASTER_TABLE,
]

DEMAND_OBJECT_COLUMNS = {
    "raw_keyword",
    "normalized_keyword",
    "recipient",
    "profession",
    "interest",
    "pet",
    "occasion",
    "product",
    "customization",
    "age_group",
    "gender",
    "holiday",
    "theme",
    "lifestyle",
    "month",
    "search_frequency_rank",
    "reporting_date",
}
NORMALIZED_COLUMNS = {
    "normalized_search_term",
    "month",
    "search_frequency_rank",
    "reporting_date",
}
KEYWORD_METRICS_COLUMNS = {
    "normalized_search_term",
    "month",
    "min_search_frequency_rank",
}

GIFT_PATTERN = r"(^|[^a-z0-9])(gift|gifts|present|presents)($|[^a-z0-9])"
PERSONALIZED_PATTERN = (
    r"(^|[^a-z0-9])"
    r"(personalized|personalised|custom|customized|customised|name|photo|picture|"
    r"portrait|engraved|engraving|monogram|monogrammed)"
    r"($|[^a-z0-9])"
)

PET_ROLE_PATTERNS = {
    "dog mom": r"(^|[^a-z0-9])dog\s+(mom|moms|mama|mother|mothers)($|[^a-z0-9])",
    "cat mom": r"(^|[^a-z0-9])cat\s+(mom|moms|mama|mother|mothers)($|[^a-z0-9])",
    "dog dad": r"(^|[^a-z0-9])dog\s+(dad|dads|daddy|father|fathers)($|[^a-z0-9])",
    "cat dad": r"(^|[^a-z0-9])cat\s+(dad|dads|daddy|father|fathers)($|[^a-z0-9])",
}
RECIPIENT_FALLBACKS = {
    "grandma": r"(^|[^a-z0-9])(grandma|grandmas|grandmother|grandmothers|nana|granny|grammy)($|[^a-z0-9])",
    "grandpa": r"(^|[^a-z0-9])(grandpa|grandpas|grandfather|grandfathers|papa|gramps)($|[^a-z0-9])",
    "mom": r"(^|[^a-z0-9])(mom|moms|mother|mothers|mama|mommy)($|[^a-z0-9])",
    "dad": r"(^|[^a-z0-9])(dad|dads|father|fathers|daddy)($|[^a-z0-9])",
    "wife": r"(^|[^a-z0-9])(wife|wives)($|[^a-z0-9])",
    "husband": r"(^|[^a-z0-9])husbands?($|[^a-z0-9])",
    "daughter": r"(^|[^a-z0-9])daughters?($|[^a-z0-9])",
    "son": r"(^|[^a-z0-9])sons?($|[^a-z0-9])",
    "sister": r"(^|[^a-z0-9])sisters?($|[^a-z0-9])",
    "brother": r"(^|[^a-z0-9])brothers?($|[^a-z0-9])",
    "best friend": r"(^|[^a-z0-9])best\s+friends?($|[^a-z0-9])",
}
PROFESSION_FALLBACKS = {
    "teacher": r"(^|[^a-z0-9])(teacher|teachers|educator|educators)($|[^a-z0-9])",
    "nurse": r"(^|[^a-z0-9])(nurse|nurses|rn)($|[^a-z0-9])",
}
INTEREST_FALLBACKS = {
    "fishing": r"(^|[^a-z0-9])(fishing|angler|anglers)($|[^a-z0-9])",
    "gardening": r"(^|[^a-z0-9])(gardening|garden|gardener|gardeners)($|[^a-z0-9])",
}

MASTER_COLUMNS = [
    "demand_id",
    "demand_name",
    "primary_type",
    "primary_value",
    "primary_intent",
    "best_rank",
    "p10_rank",
    "p25_rank",
    "median_rank",
    "top_100_count",
    "top_500_count",
    "top_1000_count",
    "top_5000_count",
    "top_50000_count",
    "active_months",
    "first_month",
    "last_month",
    "rank_momentum",
    "stability_score",
    "demand_strength_score",
    "trend_label",
]

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build rank-based Demand Strength V2 tables and CSV reports."
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Drop existing V2 demand strength tables before rebuilding.",
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
        help="Folder for Demand Strength V2 CSV reports.",
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


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


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


def table_columns(connection: duckdb.DuckDBPyConnection, table_name: str) -> set[str]:
    return {row[1] for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()}


def validate_inputs(connection: duckdb.DuckDBPyConnection) -> None:
    missing_tables = [table_name for table_name in INPUT_TABLES if not table_exists(connection, table_name)]
    if missing_tables:
        raise RuntimeError(f"Missing required input table(s): {', '.join(missing_tables)}")

    required_columns = {
        DEMAND_OBJECTS_TABLE: DEMAND_OBJECT_COLUMNS,
        NORMALIZED_TABLE: NORMALIZED_COLUMNS,
        KEYWORD_METRICS_TABLE: KEYWORD_METRICS_COLUMNS,
    }
    for table_name, columns in required_columns.items():
        missing_columns = sorted(columns - table_columns(connection, table_name))
        if missing_columns:
            raise RuntimeError(
                f"{table_name} is missing required columns: {', '.join(missing_columns)}"
            )


def log_input_counts(connection: duckdb.DuckDBPyConnection) -> None:
    for table_name in INPUT_TABLES:
        row_count = connection.execute(f"SELECT count(*) FROM {table_name}").fetchone()[0]
        logger.info("Input %s: %s rows", table_name, f"{row_count:,}")


def ensure_rebuild_allowed(connection: duckdb.DuckDBPyConnection, rebuild: bool) -> None:
    existing_tables = [table_name for table_name in OUTPUT_TABLES if table_exists(connection, table_name)]
    if existing_tables and not rebuild:
        raise RuntimeError(
            "Demand Strength V2 tables already exist. Rerun with --rebuild to replace only "
            f"these V2 tables: {', '.join(existing_tables)}"
        )


def drop_output_tables(connection: duckdb.DuckDBPyConnection) -> None:
    for table_name in OUTPUT_TABLES:
        logger.info("Dropping %s if it exists", table_name)
        connection.execute(f"DROP TABLE IF EXISTS {table_name}")


def nullable_column(column_name: str) -> str:
    return f"nullif(trim(CAST({column_name} AS VARCHAR)), '')"


def regex_case_expression(cases: dict[str, str], value_name: str, fallback: str = "NULL") -> str:
    when_clauses = "\n                    ".join(
        f"WHEN regexp_matches(keyword_text, {sql_literal(pattern)}) THEN {sql_literal(value)}"
        for value, pattern in cases.items()
    )
    return f"CASE\n                    {when_clauses}\n                    ELSE {fallback}\n                END AS {value_name}"


def create_stage_tables(connection: duckdb.DuckDBPyConnection) -> None:
    logger.info("Creating Demand Strength V2 keyword stage")
    pet_role_regex = regex_case_expression(PET_ROLE_PATTERNS, "regex_pet_role")
    recipient_regex = regex_case_expression(RECIPIENT_FALLBACKS, "regex_recipient")
    profession_regex = regex_case_expression(PROFESSION_FALLBACKS, "regex_profession")
    interest_regex = regex_case_expression(INTEREST_FALLBACKS, "regex_interest")

    connection.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE demand_keyword_stage_v2 AS
        WITH source AS (
            SELECT
                raw_keyword,
                normalized_keyword,
                lower(coalesce(normalized_keyword, '')) AS keyword_text,
                {nullable_column("recipient")} AS source_recipient,
                {nullable_column("profession")} AS source_profession,
                {nullable_column("interest")} AS source_interest,
                {nullable_column("pet")} AS source_pet,
                {nullable_column("occasion")} AS occasion,
                {nullable_column("product")} AS product,
                {nullable_column("customization")} AS customization,
                {nullable_column("age_group")} AS age_group,
                {nullable_column("gender")} AS gender,
                {nullable_column("holiday")} AS holiday,
                {nullable_column("theme")} AS theme,
                {nullable_column("lifestyle")} AS lifestyle,
                month,
                search_frequency_rank,
                reporting_date
            FROM {DEMAND_OBJECTS_TABLE}
        ),
        matched AS (
            SELECT
                *,
                regexp_matches(keyword_text, {sql_literal(GIFT_PATTERN)}) AS is_gift,
                regexp_matches(keyword_text, {sql_literal(PERSONALIZED_PATTERN)}) AS is_personalized,
                {pet_role_regex},
                {recipient_regex},
                {profession_regex},
                {interest_regex}
            FROM source
        ),
        resolved AS (
            SELECT
                *,
                CASE
                    WHEN regex_pet_role IS NOT NULL THEN regex_pet_role
                    WHEN source_recipient IN ('dog mom', 'cat mom', 'dog dad', 'cat dad')
                    THEN source_recipient
                    WHEN source_recipient IN ('mom', 'mother') AND source_pet = 'dog'
                    THEN 'dog mom'
                    WHEN source_recipient IN ('mom', 'mother') AND source_pet = 'cat'
                    THEN 'cat mom'
                    WHEN source_recipient IN ('dad', 'father') AND source_pet = 'dog'
                    THEN 'dog dad'
                    WHEN source_recipient IN ('dad', 'father') AND source_pet = 'cat'
                    THEN 'cat dad'
                    ELSE NULL
                END AS resolved_pet_role,
                CASE
                    WHEN source_profession IS NOT NULL THEN source_profession
                    WHEN source_recipient IN ('teacher', 'nurse') THEN source_recipient
                    WHEN regex_profession IS NOT NULL THEN regex_profession
                    ELSE NULL
                END AS resolved_profession,
                CASE
                    WHEN source_recipient IN ('teacher', 'nurse', 'dog mom', 'cat mom', 'dog dad', 'cat dad')
                    THEN NULL
                    WHEN source_recipient IS NOT NULL THEN source_recipient
                    WHEN regex_recipient IS NOT NULL THEN regex_recipient
                    ELSE NULL
                END AS resolved_recipient,
                CASE
                    WHEN source_interest IS NOT NULL THEN source_interest
                    WHEN regex_interest IS NOT NULL THEN regex_interest
                    ELSE NULL
                END AS resolved_interest,
                CASE
                    WHEN is_gift THEN 'gift'
                    WHEN is_personalized THEN 'personalized'
                    ELSE 'general'
                END AS primary_intent
            FROM matched
        ),
        classified AS (
            SELECT
                *,
                CASE
                    WHEN resolved_pet_role IS NOT NULL THEN 'pet_role'
                    WHEN resolved_recipient IS NOT NULL THEN 'recipient'
                    WHEN resolved_profession IS NOT NULL THEN 'profession'
                    WHEN resolved_interest IS NOT NULL THEN 'interest'
                    ELSE 'unclassified'
                END AS primary_type,
                CASE
                    WHEN resolved_pet_role IS NOT NULL THEN resolved_pet_role
                    WHEN resolved_recipient IS NOT NULL THEN resolved_recipient
                    WHEN resolved_profession IS NOT NULL THEN resolved_profession
                    WHEN resolved_interest IS NOT NULL THEN resolved_interest
                    ELSE 'unclassified'
                END AS primary_value
            FROM resolved
        )
        SELECT
            concat(primary_intent, '|', primary_type, '|', primary_value) AS demand_key,
            raw_keyword,
            normalized_keyword,
            month,
            search_frequency_rank,
            reporting_date,
            primary_intent,
            primary_type,
            primary_value,
            resolved_interest AS interest,
            occasion,
            holiday,
            theme,
            lifestyle,
            age_group,
            gender,
            product,
            customization
        FROM classified
        """
    )

    logger.info("Creating Demand Strength V2 monthly stage")
    connection.execute(
        """
        CREATE OR REPLACE TEMP TABLE demand_monthly_stage_v2 AS
        SELECT
            demand_key,
            month,
            min(search_frequency_rank) AS best_rank,
            quantile_cont(CAST(search_frequency_rank AS DOUBLE), 0.10) AS p10_rank,
            quantile_cont(CAST(search_frequency_rank AS DOUBLE), 0.25) AS p25_rank,
            median(CAST(search_frequency_rank AS DOUBLE)) AS median_rank,
            sum(CASE WHEN search_frequency_rank <= 100 THEN 1 ELSE 0 END) AS top_100_count,
            sum(CASE WHEN search_frequency_rank <= 500 THEN 1 ELSE 0 END) AS top_500_count,
            sum(CASE WHEN search_frequency_rank <= 1000 THEN 1 ELSE 0 END) AS top_1000_count,
            sum(CASE WHEN search_frequency_rank <= 5000 THEN 1 ELSE 0 END) AS top_5000_count,
            count(*) AS keyword_count
        FROM demand_keyword_stage_v2
        GROUP BY demand_key, month
        """
    )


def clamp_score(value: float) -> float:
    return max(0.0, min(100.0, value))


def rank_score(value: object, max_rank: int) -> float:
    if pd.isna(value):
        return 0.0
    rank = max(1.0, float(value))
    scale = max(2.0, float(max_rank))
    return clamp_score(100.0 * (1.0 - (math.log(rank) / math.log(scale))))


def diversity_score(value: object, max_diversity: int) -> float:
    if pd.isna(value) or max_diversity <= 0:
        return 0.0
    return clamp_score(100.0 * (math.log1p(float(value)) / math.log1p(float(max_diversity))))


def title_case(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value or "").strip()
    return string.capwords(text) if text else ""


def demand_name(row: pd.Series) -> str:
    primary_value = str(row["primary_value"] or "unclassified").strip()
    base_name = "Unclassified" if primary_value == "unclassified" else title_case(primary_value)

    primary_intent = str(row["primary_intent"])
    if primary_intent == "gift":
        return f"{base_name} Gift"
    if primary_intent == "personalized":
        return f"Personalized {base_name}"
    return f"{base_name} Demand"


def create_master_metrics_frame(connection: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    logger.info("Aggregating Demand Strength V2 master metrics")
    return connection.execute(
        """
        WITH metrics AS (
            SELECT
                demand_key,
                min(primary_type) AS primary_type,
                min(primary_value) AS primary_value,
                min(primary_intent) AS primary_intent,
                min(search_frequency_rank) AS best_rank,
                quantile_cont(CAST(search_frequency_rank AS DOUBLE), 0.10) AS p10_rank,
                quantile_cont(CAST(search_frequency_rank AS DOUBLE), 0.25) AS p25_rank,
                median(CAST(search_frequency_rank AS DOUBLE)) AS median_rank,
                sum(CASE WHEN search_frequency_rank <= 100 THEN 1 ELSE 0 END) AS top_100_count,
                sum(CASE WHEN search_frequency_rank <= 500 THEN 1 ELSE 0 END) AS top_500_count,
                sum(CASE WHEN search_frequency_rank <= 1000 THEN 1 ELSE 0 END) AS top_1000_count,
                sum(CASE WHEN search_frequency_rank <= 5000 THEN 1 ELSE 0 END) AS top_5000_count,
                sum(CASE WHEN search_frequency_rank <= 50000 THEN 1 ELSE 0 END) AS top_50000_count,
                count(*) AS keyword_count,
                count(DISTINCT normalized_keyword) AS distinct_keyword_count,
                count(DISTINCT month) AS active_months,
                min(month) AS first_month,
                max(month) AS last_month
            FROM demand_keyword_stage_v2
            GROUP BY demand_key
        ),
        global_months AS (
            SELECT
                min(month) AS earliest_month,
                max(month) AS latest_month,
                count(DISTINCT month) AS total_months
            FROM demand_keyword_stage_v2
        ),
        monthly_variability AS (
            SELECT
                demand_key,
                coalesce(
                    stddev_samp(p25_rank) / nullif(avg(p25_rank), 0),
                    0.0
                ) AS p25_cv
            FROM demand_monthly_stage_v2
            GROUP BY demand_key
        ),
        first_last AS (
            SELECT
                metrics.demand_key,
                first_month.best_rank AS first_best_rank,
                last_month.best_rank AS last_best_rank,
                first_month.p25_rank AS first_p25_rank,
                last_month.p25_rank AS last_p25_rank
            FROM metrics
            LEFT JOIN demand_monthly_stage_v2 AS first_month
              ON metrics.demand_key = first_month.demand_key
             AND metrics.first_month = first_month.month
            LEFT JOIN demand_monthly_stage_v2 AS last_month
              ON metrics.demand_key = last_month.demand_key
             AND metrics.last_month = last_month.month
        ),
        scored AS (
            SELECT
                metrics.*,
                CASE
                    WHEN metrics.active_months <= 1 THEN 0.0
                    WHEN coalesce(first_last.first_p25_rank, first_last.first_best_rank) IS NULL THEN 0.0
                    WHEN coalesce(first_last.first_p25_rank, first_last.first_best_rank) = 0 THEN 0.0
                    ELSE round(
                        (
                            coalesce(first_last.first_p25_rank, first_last.first_best_rank)
                            - coalesce(first_last.last_p25_rank, first_last.last_best_rank)
                        )
                        * 100.0
                        / coalesce(first_last.first_p25_rank, first_last.first_best_rank),
                        2
                    )
                END AS rank_momentum,
                round(
                    (
                        least(100.0, metrics.active_months * 100.0 / global_months.total_months)
                        * 0.6
                    )
                    + (
                        100.0 - least(100.0, coalesce(monthly_variability.p25_cv, 0.0) * 100.0)
                    )
                    * 0.4,
                    2
                ) AS stability_score,
                global_months.earliest_month,
                global_months.latest_month
            FROM metrics
            LEFT JOIN monthly_variability
              ON metrics.demand_key = monthly_variability.demand_key
            LEFT JOIN first_last
              ON metrics.demand_key = first_last.demand_key
            CROSS JOIN global_months
        )
        SELECT
            demand_key,
            primary_type,
            primary_value,
            primary_intent,
            best_rank,
            p10_rank,
            p25_rank,
            median_rank,
            top_100_count,
            top_500_count,
            top_1000_count,
            top_5000_count,
            top_50000_count,
            keyword_count,
            distinct_keyword_count,
            active_months,
            first_month,
            last_month,
            rank_momentum,
            stability_score,
            CASE
                WHEN active_months <= 2
                 AND first_month > earliest_month
                 AND last_month = latest_month
                THEN 'emerging'
                WHEN rank_momentum >= 10 THEN 'growing'
                WHEN rank_momentum <= -10 THEN 'declining'
                ELSE 'stable'
            END AS trend_label
        FROM scored
        """
    ).df()


def score_master_frame(
    connection: duckdb.DuckDBPyConnection,
    master_metrics: pd.DataFrame,
) -> pd.DataFrame:
    if master_metrics.empty:
        raise RuntimeError("No demand rows were produced from demand_objects")

    max_rank = int(
        connection.execute(
            "SELECT coalesce(max(search_frequency_rank), 1) FROM demand_keyword_stage_v2"
        ).fetchone()[0]
    )
    max_diversity = int(master_metrics["distinct_keyword_count"].max() or 1)

    master = master_metrics.copy()
    master["best_rank_score"] = master["best_rank"].apply(lambda value: rank_score(value, max_rank))
    master["p25_rank_score"] = master["p25_rank"].apply(lambda value: rank_score(value, max_rank))
    master["top_1000_coverage_score"] = (
        master["top_1000_count"].astype(float)
        / master["keyword_count"].astype(float).clip(lower=1.0)
        * 100.0
    ).clip(lower=0.0, upper=100.0)
    master["rank_momentum_score"] = master["rank_momentum"].apply(
        lambda value: 50.0 if pd.isna(value) else clamp_score(50.0 + float(value))
    )
    master["keyword_diversity_score"] = master["distinct_keyword_count"].apply(
        lambda value: diversity_score(value, max_diversity)
    )

    master["demand_strength_score"] = (
        (master["best_rank_score"] * 0.35)
        + (master["p25_rank_score"] * 0.20)
        + (master["top_1000_coverage_score"] * 0.15)
        + (master["rank_momentum_score"] * 0.15)
        + (master["stability_score"].astype(float) * 0.10)
        + (master["keyword_diversity_score"] * 0.05)
    ).round(2)

    unclassified = master["primary_type"] == "unclassified"
    score_columns = [
        "best_rank_score",
        "p25_rank_score",
        "top_1000_coverage_score",
        "rank_momentum_score",
        "keyword_diversity_score",
        "demand_strength_score",
    ]
    master.loc[unclassified, score_columns] = 0.0

    sort_columns = ["demand_strength_score", "best_rank", "p25_rank", "demand_key"]
    master = master.sort_values(
        sort_columns,
        ascending=[False, True, True, True],
        na_position="last",
    ).reset_index(drop=True)
    master.insert(0, "demand_id", [f"DM{index:06d}" for index in range(1, len(master) + 1)])
    master.insert(1, "demand_name", master.apply(demand_name, axis=1))

    return master


def build_demand_master(connection: duckdb.DuckDBPyConnection) -> int:
    metrics = create_master_metrics_frame(connection)
    master = score_master_frame(connection, metrics)

    frame_columns = MASTER_COLUMNS + ["demand_key"]
    connection.register("demand_master_v2_frame", master[frame_columns])
    connection.execute(
        f"""
        CREATE TABLE {DEMAND_MASTER_TABLE} AS
        SELECT
            demand_id,
            demand_name,
            primary_type,
            primary_value,
            primary_intent,
            best_rank,
            p10_rank,
            p25_rank,
            median_rank,
            top_100_count,
            top_500_count,
            top_1000_count,
            top_5000_count,
            top_50000_count,
            active_months,
            first_month,
            last_month,
            rank_momentum,
            stability_score,
            demand_strength_score,
            trend_label
        FROM demand_master_v2_frame
        """
    )
    connection.execute(
        """
        CREATE OR REPLACE TEMP TABLE demand_id_map_v2 AS
        SELECT demand_key, demand_id
        FROM demand_master_v2_frame
        """
    )
    connection.unregister("demand_master_v2_frame")

    row_count = len(master)
    logger.info("Built %s with %s rows", DEMAND_MASTER_TABLE, f"{row_count:,}")
    return row_count


def build_demand_keywords(connection: duckdb.DuckDBPyConnection) -> int:
    logger.info("Building %s", DEMAND_KEYWORDS_TABLE)
    connection.execute(
        f"""
        CREATE TABLE {DEMAND_KEYWORDS_TABLE} AS
        SELECT
            demand_id_map_v2.demand_id,
            demand_keyword_stage_v2.raw_keyword,
            demand_keyword_stage_v2.normalized_keyword,
            demand_keyword_stage_v2.month,
            demand_keyword_stage_v2.search_frequency_rank,
            demand_keyword_stage_v2.reporting_date
        FROM demand_keyword_stage_v2
        JOIN demand_id_map_v2
          ON demand_keyword_stage_v2.demand_key = demand_id_map_v2.demand_key
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
            demand_id_map_v2.demand_id,
            demand_monthly_stage_v2.month,
            demand_monthly_stage_v2.best_rank,
            demand_monthly_stage_v2.p10_rank,
            demand_monthly_stage_v2.p25_rank,
            demand_monthly_stage_v2.median_rank,
            demand_monthly_stage_v2.top_100_count,
            demand_monthly_stage_v2.top_500_count,
            demand_monthly_stage_v2.top_1000_count,
            demand_monthly_stage_v2.top_5000_count,
            demand_monthly_stage_v2.keyword_count
        FROM demand_monthly_stage_v2
        JOIN demand_id_map_v2
          ON demand_monthly_stage_v2.demand_key = demand_id_map_v2.demand_key
        ORDER BY demand_id_map_v2.demand_id, demand_monthly_stage_v2.month
        """
    )
    row_count = connection.execute(f"SELECT count(*) FROM {DEMAND_MONTHLY_TABLE}").fetchone()[0]
    logger.info("Built %s with %s rows", DEMAND_MONTHLY_TABLE, f"{row_count:,}")
    return int(row_count)


def build_demand_profile(connection: duckdb.DuckDBPyConnection) -> int:
    logger.info("Building %s", DEMAND_PROFILE_TABLE)
    connection.execute(
        f"""
        CREATE TABLE {DEMAND_PROFILE_TABLE} AS
        WITH profile_source AS (
            SELECT demand_key, 'holiday' AS dimension, holiday AS value, search_frequency_rank
            FROM demand_keyword_stage_v2
            UNION ALL
            SELECT demand_key, 'occasion' AS dimension, occasion AS value, search_frequency_rank
            FROM demand_keyword_stage_v2
            UNION ALL
            SELECT demand_key, 'interest' AS dimension, interest AS value, search_frequency_rank
            FROM demand_keyword_stage_v2
            UNION ALL
            SELECT demand_key, 'theme' AS dimension, theme AS value, search_frequency_rank
            FROM demand_keyword_stage_v2
            UNION ALL
            SELECT demand_key, 'lifestyle' AS dimension, lifestyle AS value, search_frequency_rank
            FROM demand_keyword_stage_v2
            UNION ALL
            SELECT demand_key, 'age_group' AS dimension, age_group AS value, search_frequency_rank
            FROM demand_keyword_stage_v2
            UNION ALL
            SELECT demand_key, 'gender' AS dimension, gender AS value, search_frequency_rank
            FROM demand_keyword_stage_v2
            UNION ALL
            SELECT demand_key, 'product' AS dimension, product AS value, search_frequency_rank
            FROM demand_keyword_stage_v2
            UNION ALL
            SELECT demand_key, 'customization' AS dimension, customization AS value, search_frequency_rank
            FROM demand_keyword_stage_v2
        )
        SELECT
            demand_id_map_v2.demand_id,
            profile_source.dimension,
            profile_source.value,
            count(*) AS keyword_count,
            min(profile_source.search_frequency_rank) AS best_rank,
            sum(CASE WHEN profile_source.search_frequency_rank <= 1000 THEN 1 ELSE 0 END)
                AS top_1000_count
        FROM profile_source
        JOIN demand_id_map_v2
          ON profile_source.demand_key = demand_id_map_v2.demand_key
        WHERE profile_source.value IS NOT NULL
          AND trim(profile_source.value) <> ''
        GROUP BY
            demand_id_map_v2.demand_id,
            profile_source.dimension,
            profile_source.value
        ORDER BY
            demand_id_map_v2.demand_id,
            profile_source.dimension,
            best_rank NULLS LAST,
            profile_source.value
        """
    )
    row_count = connection.execute(f"SELECT count(*) FROM {DEMAND_PROFILE_TABLE}").fetchone()[0]
    logger.info("Built %s with %s rows", DEMAND_PROFILE_TABLE, f"{row_count:,}")
    return int(row_count)


def export_query_to_csv(
    connection: duckdb.DuckDBPyConnection,
    query: str,
    output_path: Path,
    chunk_size: int = 100_000,
) -> int:
    cursor = connection.execute(query)
    columns = [description[0] for description in cursor.description]
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
        pd.DataFrame(columns=columns).to_csv(output_path, index=False)

    return total_rows


def export_reports(connection: duckdb.DuckDBPyConnection, output_dir: Path) -> None:
    logger.info("Exporting Demand Strength V2 reports to %s", display_path(output_dir))
    output_dir.mkdir(parents=True, exist_ok=True)

    exports = {
        "demand_master_v2.csv": f"SELECT * FROM {DEMAND_MASTER_TABLE} ORDER BY demand_id",
        "demand_keywords_v2.csv": f"SELECT * FROM {DEMAND_KEYWORDS_TABLE}",
        "demand_monthly_v2.csv": f"SELECT * FROM {DEMAND_MONTHLY_TABLE} ORDER BY demand_id, month",
        "demand_profile_v2.csv": f"""
            SELECT *
            FROM {DEMAND_PROFILE_TABLE}
            ORDER BY demand_id, dimension, best_rank NULLS LAST, value
        """,
        "top_demands_by_strength.csv": f"""
            SELECT *
            FROM {DEMAND_MASTER_TABLE}
            WHERE primary_type <> 'unclassified'
            ORDER BY
                demand_strength_score DESC,
                best_rank ASC NULLS LAST,
                p25_rank ASC NULLS LAST,
                demand_id
        """,
        "top_demands_by_best_rank.csv": f"""
            SELECT *
            FROM {DEMAND_MASTER_TABLE}
            WHERE primary_type <> 'unclassified'
            ORDER BY
                best_rank ASC NULLS LAST,
                demand_strength_score DESC,
                p25_rank ASC NULLS LAST,
                demand_id
        """,
        "top_growing_demands.csv": f"""
            SELECT *
            FROM {DEMAND_MASTER_TABLE}
            WHERE primary_type <> 'unclassified'
              AND trend_label IN ('growing', 'emerging')
            ORDER BY
                CASE trend_label
                    WHEN 'growing' THEN 1
                    WHEN 'emerging' THEN 2
                    ELSE 3
                END,
                rank_momentum DESC,
                demand_strength_score DESC,
                best_rank ASC NULLS LAST,
                demand_id
        """,
    }

    for file_name, query in exports.items():
        row_count = export_query_to_csv(connection, query, output_dir / file_name)
        logger.info("Exported %s with %s rows", file_name, f"{row_count:,}")


def log_summary(connection: duckdb.DuckDBPyConnection) -> None:
    logger.info("Demand Strength V2 summary")
    for table_name in [
        DEMAND_MASTER_TABLE,
        DEMAND_KEYWORDS_TABLE,
        DEMAND_MONTHLY_TABLE,
        DEMAND_PROFILE_TABLE,
    ]:
        row_count = connection.execute(f"SELECT count(*) FROM {table_name}").fetchone()[0]
        logger.info("  %s: %s rows", table_name, f"{row_count:,}")

    top_rows = connection.execute(
        f"""
        SELECT
            demand_id,
            demand_name,
            best_rank,
            p25_rank,
            demand_strength_score,
            trend_label
        FROM {DEMAND_MASTER_TABLE}
        ORDER BY demand_strength_score DESC, best_rank ASC NULLS LAST
        LIMIT 10
        """
    ).fetchall()
    logger.info("Top demands by strength:")
    for demand_id, name, best_rank, p25_rank, score, trend in top_rows:
        logger.info(
            "  %s | %s | best=%s | p25=%s | score=%s | %s",
            demand_id,
            name,
            best_rank,
            round(float(p25_rank), 2) if p25_rank is not None else None,
            score,
            trend,
        )


def build_demand_strength_v2(database_path: Path, output_dir: Path, rebuild: bool) -> None:
    if not database_path.exists():
        raise FileNotFoundError(f"DuckDB database not found: {database_path}")

    with duckdb.connect(str(database_path)) as connection:
        validate_inputs(connection)
        log_input_counts(connection)
        ensure_rebuild_allowed(connection, rebuild)
        if rebuild:
            drop_output_tables(connection)

        create_stage_tables(connection)
        build_demand_master(connection)
        build_demand_keywords(connection)
        build_demand_monthly(connection)
        build_demand_profile(connection)
        export_reports(connection, output_dir)
        log_summary(connection)


def main() -> None:
    configure_logging()
    args = parse_args()
    logger.info("Starting Demand Strength V2 build")
    build_demand_strength_v2(
        database_path=args.database.resolve(),
        output_dir=args.output_dir.resolve(),
        rebuild=args.rebuild,
    )
    logger.info("Demand Strength V2 build complete")
    logger.info("Build log: %s", display_path(LOG_PATH))


if __name__ == "__main__":
    main()
