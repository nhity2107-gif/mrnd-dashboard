"""Build deterministic intent-first keyword and market node tables."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import duckdb
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DUCKDB_PATH = PROJECT_ROOT / "data" / "output" / "aba.duckdb"
OUTPUT_DIR = PROJECT_ROOT / "data" / "output" / "intent_layer"
LOG_DIR = PROJECT_ROOT / "logs"
LOG_PATH = LOG_DIR / "build_intent_layer.log"

DEMAND_OBJECTS_TABLE = "demand_objects"
DEMAND_MASTER_TABLE = "demand_master_v2"
MARKET_NODES_TABLE = "market_nodes"
KEYWORD_ENTITY_EDGES_TABLE = "keyword_entity_edges"

INTENT_KEYWORDS_TABLE = "intent_keywords"
INTENT_SUMMARY_TABLE = "intent_summary"
INTENT_MARKET_NODES_TABLE = "intent_market_nodes"

INPUT_TABLES = [
    DEMAND_OBJECTS_TABLE,
    DEMAND_MASTER_TABLE,
    MARKET_NODES_TABLE,
    KEYWORD_ENTITY_EDGES_TABLE,
]
OUTPUT_TABLES = [
    INTENT_MARKET_NODES_TABLE,
    INTENT_SUMMARY_TABLE,
    INTENT_KEYWORDS_TABLE,
]

REQUIRED_COLUMNS = {
    DEMAND_OBJECTS_TABLE: {
        "demand_id",
        "raw_keyword",
        "normalized_keyword",
        "recipient",
        "profession",
        "interest",
        "pet",
        "occasion",
        "product",
        "customization",
        "style",
        "modifier",
        "age_group",
        "gender",
        "holiday",
        "theme",
        "lifestyle",
        "month",
        "search_frequency_rank",
        "reporting_date",
    },
    DEMAND_MASTER_TABLE: {
        "demand_id",
        "demand_name",
        "primary_type",
        "primary_value",
        "primary_intent",
        "best_rank",
        "demand_strength_score",
        "trend_label",
    },
    MARKET_NODES_TABLE: {
        "market_node_id",
        "recipient",
        "profession",
        "pet",
        "interest",
        "theme",
        "lifestyle",
    },
    KEYWORD_ENTITY_EDGES_TABLE: {
        "keyword_id",
        "normalized_keyword",
        "raw_keyword",
        "entity_type",
        "entity_value",
        "month",
        "search_frequency_rank",
    },
}

INTENT_TYPES = [
    "gift",
    "personalized",
    "matching",
    "memorial",
    "appreciation",
    "birthday",
    "christmas",
    "retirement",
    "graduation",
    "wedding",
    "anniversary",
    "housewarming",
    "sympathy",
    "decor",
    "apparel",
    "unknown",
]

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build intent-first keyword, summary, and market node tables."
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Drop existing intent layer tables before rebuilding.",
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
        help="Folder for intent layer CSV reports.",
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
        raise RuntimeError(
            "Missing required table(s): "
            f"{', '.join(missing_tables)}. Run Demand V2, Market Nodes, and Knowledge Graph first."
        )

    for table_name, required_columns in REQUIRED_COLUMNS.items():
        missing_columns = sorted(required_columns - table_columns(connection, table_name))
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
            "Intent layer tables already exist. Rerun with --rebuild to replace only "
            f"these tables: {', '.join(existing_tables)}"
        )


def drop_output_tables(connection: duckdb.DuckDBPyConnection) -> None:
    for table_name in OUTPUT_TABLES:
        logger.info("Dropping %s if it exists", table_name)
        connection.execute(f"DROP TABLE IF EXISTS {table_name}")


def nullable_column(column_name: str) -> str:
    return f"nullif(trim(CAST({column_name} AS VARCHAR)), '')"


def build_intent_keywords(connection: duckdb.DuckDBPyConnection) -> int:
    logger.info("Building %s", INTENT_KEYWORDS_TABLE)
    connection.execute(
        f"""
        CREATE TABLE {INTENT_KEYWORDS_TABLE} AS
        WITH base AS (
            SELECT
                demand_id AS keyword_id,
                raw_keyword,
                normalized_keyword,
                lower(coalesce(normalized_keyword, '')) AS keyword_text,
                month,
                search_frequency_rank,
                reporting_date,
                {nullable_column("recipient")} AS recipient,
                {nullable_column("profession")} AS profession,
                {nullable_column("pet")} AS pet,
                {nullable_column("interest")} AS interest,
                {nullable_column("theme")} AS theme,
                {nullable_column("lifestyle")} AS lifestyle,
                {nullable_column("product")} AS product,
                {nullable_column("customization")} AS customization,
                {nullable_column("style")} AS style,
                {nullable_column("holiday")} AS holiday,
                {nullable_column("occasion")} AS occasion,
                {nullable_column("age_group")} AS age_group,
                {nullable_column("gender")} AS gender
            FROM {DEMAND_OBJECTS_TABLE}
        ),
        intent_classified AS (
            SELECT
                *,
                CASE
                    WHEN regexp_matches(keyword_text, '(^|[^a-z0-9])(appreciation|thank\\s+you|thanks)($|[^a-z0-9])')
                    THEN 'appreciation'
                    WHEN regexp_matches(keyword_text, '(^|[^a-z0-9])(memorial|remembrance|bereavement)($|[^a-z0-9])')
                      OR regexp_matches(keyword_text, '(^|[^a-z0-9])in\\s+memory\\s+of($|[^a-z0-9])')
                    THEN 'memorial'
                    WHEN regexp_matches(keyword_text, '(^|[^a-z0-9])(matching|matchy|couple|couples|his\\s+and\\s+hers)($|[^a-z0-9])')
                      OR regexp_matches(keyword_text, '(^|[^a-z0-9])family\\s+matching($|[^a-z0-9])')
                      OR regexp_matches(keyword_text, '(^|[^a-z0-9])(mommy|daddy)\\s+and\\s+me($|[^a-z0-9])')
                    THEN 'matching'
                    WHEN regexp_matches(keyword_text, '(^|[^a-z0-9])(gift|gifts|present|presents)($|[^a-z0-9])')
                    THEN 'gift'
                    WHEN regexp_matches(keyword_text, '(^|[^a-z0-9])(personalized|personalised|custom|customized|customised|engraved|monogram|monogrammed)($|[^a-z0-9])')
                    THEN 'personalized'
                    WHEN regexp_matches(keyword_text, '(^|[^a-z0-9])birthdays?($|[^a-z0-9])')
                    THEN 'birthday'
                    WHEN regexp_matches(keyword_text, '(^|[^a-z0-9])christmas($|[^a-z0-9])')
                    THEN 'christmas'
                    WHEN regexp_matches(keyword_text, '(^|[^a-z0-9])retirement($|[^a-z0-9])')
                    THEN 'retirement'
                    WHEN regexp_matches(keyword_text, '(^|[^a-z0-9])(graduation|graduate|grad)($|[^a-z0-9])')
                    THEN 'graduation'
                    WHEN regexp_matches(keyword_text, '(^|[^a-z0-9])(wedding|bride|groom|bridal)($|[^a-z0-9])')
                    THEN 'wedding'
                    WHEN regexp_matches(keyword_text, '(^|[^a-z0-9])anniversary($|[^a-z0-9])')
                    THEN 'anniversary'
                    WHEN regexp_matches(keyword_text, '(^|[^a-z0-9])housewarming($|[^a-z0-9])')
                    THEN 'housewarming'
                    WHEN regexp_matches(keyword_text, '(^|[^a-z0-9])(sympathy|condolence|condolences)($|[^a-z0-9])')
                    THEN 'sympathy'
                    WHEN regexp_matches(keyword_text, '(^|[^a-z0-9])(decor|decoration|decorations|wall\\s+art|poster|posters|sign|signs)($|[^a-z0-9])')
                    THEN 'decor'
                    WHEN regexp_matches(keyword_text, '(^|[^a-z0-9])(shirt|shirts|tshirt|tshirts|t\\s+shirt|sweatshirt|hoodie|apparel|clothes|clothing|hat|hats)($|[^a-z0-9])')
                    THEN 'apparel'
                    ELSE 'unknown'
                END AS intent,
                CASE
                    WHEN regexp_matches(keyword_text, '(^|[^a-z0-9])(appreciation|thank\\s+you|thanks)($|[^a-z0-9])')
                    THEN 'appreciation_or_thank_you'
                    WHEN regexp_matches(keyword_text, '(^|[^a-z0-9])(memorial|remembrance|bereavement)($|[^a-z0-9])')
                      OR regexp_matches(keyword_text, '(^|[^a-z0-9])in\\s+memory\\s+of($|[^a-z0-9])')
                    THEN 'memorial_terms'
                    WHEN regexp_matches(keyword_text, '(^|[^a-z0-9])(matching|matchy|couple|couples|his\\s+and\\s+hers)($|[^a-z0-9])')
                      OR regexp_matches(keyword_text, '(^|[^a-z0-9])family\\s+matching($|[^a-z0-9])')
                      OR regexp_matches(keyword_text, '(^|[^a-z0-9])(mommy|daddy)\\s+and\\s+me($|[^a-z0-9])')
                    THEN 'matching_terms'
                    WHEN regexp_matches(keyword_text, '(^|[^a-z0-9])(gift|gifts|present|presents)($|[^a-z0-9])')
                    THEN 'gift_or_present'
                    WHEN regexp_matches(keyword_text, '(^|[^a-z0-9])(personalized|personalised|custom|customized|customised|engraved|monogram|monogrammed)($|[^a-z0-9])')
                    THEN 'personalized_or_custom'
                    WHEN regexp_matches(keyword_text, '(^|[^a-z0-9])birthdays?($|[^a-z0-9])')
                    THEN 'birthday_terms'
                    WHEN regexp_matches(keyword_text, '(^|[^a-z0-9])christmas($|[^a-z0-9])')
                    THEN 'christmas_terms'
                    WHEN regexp_matches(keyword_text, '(^|[^a-z0-9])retirement($|[^a-z0-9])')
                    THEN 'retirement_terms'
                    WHEN regexp_matches(keyword_text, '(^|[^a-z0-9])(graduation|graduate|grad)($|[^a-z0-9])')
                    THEN 'graduation_terms'
                    WHEN regexp_matches(keyword_text, '(^|[^a-z0-9])(wedding|bride|groom|bridal)($|[^a-z0-9])')
                    THEN 'wedding_terms'
                    WHEN regexp_matches(keyword_text, '(^|[^a-z0-9])anniversary($|[^a-z0-9])')
                    THEN 'anniversary_terms'
                    WHEN regexp_matches(keyword_text, '(^|[^a-z0-9])housewarming($|[^a-z0-9])')
                    THEN 'housewarming_terms'
                    WHEN regexp_matches(keyword_text, '(^|[^a-z0-9])(sympathy|condolence|condolences)($|[^a-z0-9])')
                    THEN 'sympathy_terms'
                    WHEN regexp_matches(keyword_text, '(^|[^a-z0-9])(decor|decoration|decorations|wall\\s+art|poster|posters|sign|signs)($|[^a-z0-9])')
                    THEN 'decor_terms'
                    WHEN regexp_matches(keyword_text, '(^|[^a-z0-9])(shirt|shirts|tshirt|tshirts|t\\s+shirt|sweatshirt|hoodie|apparel|clothes|clothing|hat|hats)($|[^a-z0-9])')
                    THEN 'apparel_terms'
                    ELSE 'unknown'
                END AS intent_rule
            FROM base
        ),
        audience_classified AS (
            SELECT
                *,
                CASE
                    WHEN profession IS NOT NULL THEN 'profession'
                    WHEN recipient IS NOT NULL THEN 'recipient'
                    WHEN pet IS NOT NULL THEN 'pet'
                    WHEN interest IS NOT NULL THEN 'interest'
                    ELSE NULL
                END AS primary_audience_type,
                CASE
                    WHEN profession IS NOT NULL THEN profession
                    WHEN recipient IS NOT NULL THEN recipient
                    WHEN pet IS NOT NULL THEN pet
                    WHEN interest IS NOT NULL THEN interest
                    ELSE NULL
                END AS primary_audience_value
            FROM intent_classified
        ),
        niche_classified AS (
            SELECT
                *,
                CASE
                    WHEN interest IS NOT NULL
                     AND NOT (primary_audience_type = 'interest' AND primary_audience_value = interest)
                    THEN 'interest'
                    WHEN theme IS NOT NULL
                    THEN 'theme'
                    WHEN lifestyle IS NOT NULL
                    THEN 'lifestyle'
                    ELSE NULL
                END AS niche_type,
                CASE
                    WHEN interest IS NOT NULL
                     AND NOT (primary_audience_type = 'interest' AND primary_audience_value = interest)
                    THEN interest
                    WHEN theme IS NOT NULL
                    THEN theme
                    WHEN lifestyle IS NOT NULL
                    THEN lifestyle
                    ELSE NULL
                END AS niche_value
            FROM audience_classified
        )
        SELECT
            keyword_id,
            raw_keyword,
            normalized_keyword,
            month,
            search_frequency_rank,
            reporting_date,
            intent,
            intent_rule,
            primary_audience_type,
            primary_audience_value,
            niche_type,
            niche_value,
            recipient,
            profession,
            pet,
            interest,
            theme,
            lifestyle,
            product,
            customization,
            style,
            holiday,
            occasion,
            age_group,
            gender
        FROM niche_classified
        """
    )
    row_count = connection.execute(f"SELECT count(*) FROM {INTENT_KEYWORDS_TABLE}").fetchone()[0]
    logger.info("Built %s with %s rows", INTENT_KEYWORDS_TABLE, f"{row_count:,}")
    return int(row_count)


def build_intent_summary(connection: duckdb.DuckDBPyConnection) -> int:
    logger.info("Building %s", INTENT_SUMMARY_TABLE)
    connection.execute(
        f"""
        CREATE TABLE {INTENT_SUMMARY_TABLE} AS
        WITH metrics AS (
            SELECT
                intent,
                count(*) AS keyword_count,
                count(DISTINCT normalized_keyword) AS distinct_keyword_count,
                min(search_frequency_rank) AS best_rank,
                quantile_cont(CAST(search_frequency_rank AS DOUBLE), 0.25) AS p25_rank,
                median(CAST(search_frequency_rank AS DOUBLE)) AS median_rank,
                sum(CASE WHEN search_frequency_rank <= 100 THEN 1 ELSE 0 END) AS top100_count,
                sum(CASE WHEN search_frequency_rank <= 1000 THEN 1 ELSE 0 END) AS top1000_count,
                avg(search_frequency_rank) AS average_rank,
                count(DISTINCT month) AS active_months,
                min(month) AS first_month,
                max(month) AS last_month
            FROM {INTENT_KEYWORDS_TABLE}
            GROUP BY intent
        ),
        distinct_examples AS (
            SELECT
                intent,
                normalized_keyword,
                min(search_frequency_rank) AS example_rank
            FROM {INTENT_KEYWORDS_TABLE}
            GROUP BY intent, normalized_keyword
        ),
        ranked_examples AS (
            SELECT
                *,
                row_number() OVER (
                    PARTITION BY intent
                    ORDER BY example_rank ASC NULLS LAST, normalized_keyword
                ) AS example_position
            FROM distinct_examples
        ),
        examples AS (
            SELECT
                intent,
                string_agg(normalized_keyword, ' | ' ORDER BY example_position) AS example_keywords
            FROM ranked_examples
            WHERE example_position <= 10
            GROUP BY intent
        )
        SELECT
            metrics.intent,
            metrics.keyword_count,
            metrics.distinct_keyword_count,
            metrics.best_rank,
            metrics.p25_rank,
            metrics.median_rank,
            metrics.top100_count,
            metrics.top1000_count,
            round(metrics.average_rank, 2) AS average_rank,
            metrics.active_months,
            metrics.first_month,
            metrics.last_month,
            examples.example_keywords
        FROM metrics
        LEFT JOIN examples
          ON metrics.intent = examples.intent
        ORDER BY
            metrics.best_rank ASC NULLS LAST,
            metrics.top1000_count DESC,
            metrics.keyword_count DESC,
            metrics.intent
        """
    )
    row_count = connection.execute(f"SELECT count(*) FROM {INTENT_SUMMARY_TABLE}").fetchone()[0]
    logger.info("Built %s with %s rows", INTENT_SUMMARY_TABLE, f"{row_count:,}")
    return int(row_count)


def create_intent_node_evidence_stage(connection: duckdb.DuckDBPyConnection) -> None:
    logger.info("Creating intent market node evidence stage")
    connection.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE intent_node_evidence_stage AS
        SELECT DISTINCT
            concat(
                intent_keywords.intent,
                '|',
                intent_keywords.primary_audience_type,
                '|',
                intent_keywords.primary_audience_value,
                '|',
                coalesce(intent_keywords.niche_type, ''),
                '|',
                coalesce(intent_keywords.niche_value, '')
            ) AS node_key,
            intent_keywords.*
        FROM {INTENT_KEYWORDS_TABLE} AS intent_keywords
        JOIN {KEYWORD_ENTITY_EDGES_TABLE} AS audience_edges
          ON intent_keywords.keyword_id = audience_edges.keyword_id
         AND intent_keywords.primary_audience_type = audience_edges.entity_type
         AND intent_keywords.primary_audience_value = audience_edges.entity_value
        LEFT JOIN {KEYWORD_ENTITY_EDGES_TABLE} AS niche_edges
          ON intent_keywords.keyword_id = niche_edges.keyword_id
         AND intent_keywords.niche_type = niche_edges.entity_type
         AND intent_keywords.niche_value = niche_edges.entity_value
        WHERE intent_keywords.primary_audience_type IS NOT NULL
          AND (
                intent_keywords.niche_type IS NULL
             OR niche_edges.keyword_id IS NOT NULL
          )
        """
    )
    row_count = connection.execute("SELECT count(*) FROM intent_node_evidence_stage").fetchone()[0]
    logger.info("Intent node evidence stage: %s rows", f"{row_count:,}")


def build_intent_market_nodes(connection: duckdb.DuckDBPyConnection) -> int:
    logger.info("Building %s", INTENT_MARKET_NODES_TABLE)
    create_intent_node_evidence_stage(connection)
    connection.execute(
        f"""
        CREATE TABLE {INTENT_MARKET_NODES_TABLE} AS
        WITH metrics AS (
            SELECT
                node_key,
                min(intent) AS intent,
                min(primary_audience_type) AS primary_audience_type,
                min(primary_audience_value) AS primary_audience_value,
                min(niche_type) AS niche_type,
                min(niche_value) AS niche_value,
                min(CASE WHEN primary_audience_type = 'recipient' THEN primary_audience_value ELSE NULL END)
                    AS recipient,
                min(CASE WHEN primary_audience_type = 'profession' THEN primary_audience_value ELSE NULL END)
                    AS profession,
                min(CASE WHEN primary_audience_type = 'pet' THEN primary_audience_value ELSE NULL END)
                    AS pet,
                min(CASE
                    WHEN primary_audience_type = 'interest' THEN primary_audience_value
                    WHEN niche_type = 'interest' THEN niche_value
                    ELSE NULL
                END) AS interest,
                min(CASE WHEN niche_type = 'theme' THEN niche_value ELSE NULL END) AS theme,
                min(CASE WHEN niche_type = 'lifestyle' THEN niche_value ELSE NULL END) AS lifestyle,
                min(search_frequency_rank) AS best_rank,
                quantile_cont(CAST(search_frequency_rank AS DOUBLE), 0.25) AS p25_rank,
                median(CAST(search_frequency_rank AS DOUBLE)) AS median_rank,
                sum(CASE WHEN search_frequency_rank <= 100 THEN 1 ELSE 0 END) AS top100_count,
                sum(CASE WHEN search_frequency_rank <= 500 THEN 1 ELSE 0 END) AS top500_count,
                sum(CASE WHEN search_frequency_rank <= 1000 THEN 1 ELSE 0 END) AS top1000_count,
                count(*) AS keyword_count,
                count(DISTINCT normalized_keyword) AS distinct_keyword_count,
                count(DISTINCT month) AS active_months,
                min(month) AS first_month,
                max(month) AS last_month
            FROM intent_node_evidence_stage
            GROUP BY node_key
        ),
        top_product AS (
            SELECT node_key, product
            FROM (
                SELECT
                    node_key,
                    product,
                    row_number() OVER (
                        PARTITION BY node_key
                        ORDER BY min(search_frequency_rank) ASC NULLS LAST, count(*) DESC, product
                    ) AS position
                FROM intent_node_evidence_stage
                WHERE product IS NOT NULL
                GROUP BY node_key, product
            )
            WHERE position = 1
        ),
        top_customization AS (
            SELECT node_key, customization
            FROM (
                SELECT
                    node_key,
                    customization,
                    row_number() OVER (
                        PARTITION BY node_key
                        ORDER BY min(search_frequency_rank) ASC NULLS LAST, count(*) DESC, customization
                    ) AS position
                FROM intent_node_evidence_stage
                WHERE customization IS NOT NULL
                GROUP BY node_key, customization
            )
            WHERE position = 1
        ),
        top_holiday AS (
            SELECT node_key, holiday
            FROM (
                SELECT
                    node_key,
                    holiday,
                    row_number() OVER (
                        PARTITION BY node_key
                        ORDER BY min(search_frequency_rank) ASC NULLS LAST, count(*) DESC, holiday
                    ) AS position
                FROM intent_node_evidence_stage
                WHERE holiday IS NOT NULL
                GROUP BY node_key, holiday
            )
            WHERE position = 1
        ),
        top_occasion AS (
            SELECT node_key, occasion
            FROM (
                SELECT
                    node_key,
                    occasion,
                    row_number() OVER (
                        PARTITION BY node_key
                        ORDER BY min(search_frequency_rank) ASC NULLS LAST, count(*) DESC, occasion
                    ) AS position
                FROM intent_node_evidence_stage
                WHERE occasion IS NOT NULL
                GROUP BY node_key, occasion
            )
            WHERE position = 1
        ),
        legacy_nodes AS (
            SELECT
                metrics.node_key,
                count(DISTINCT market_nodes.market_node_id) AS legacy_market_node_count
            FROM metrics
            LEFT JOIN {MARKET_NODES_TABLE} AS market_nodes
              ON (
                    metrics.primary_audience_type = 'recipient'
                AND metrics.primary_audience_value = market_nodes.recipient
              )
              OR (
                    metrics.primary_audience_type = 'profession'
                AND metrics.primary_audience_value = market_nodes.profession
              )
              OR (
                    metrics.primary_audience_type = 'pet'
                AND metrics.primary_audience_value = market_nodes.pet
              )
            WHERE metrics.niche_value IS NULL
               OR metrics.niche_value IN (
                    market_nodes.interest,
                    market_nodes.theme,
                    market_nodes.lifestyle
               )
            GROUP BY metrics.node_key
        ),
        latest_month AS (
            SELECT max(month) AS value
            FROM intent_node_evidence_stage
        ),
        first_last AS (
            SELECT
                metrics.node_key,
                first_month.best_rank AS first_best_rank,
                last_month.best_rank AS last_best_rank
            FROM metrics
            LEFT JOIN (
                SELECT node_key, month, min(search_frequency_rank) AS best_rank
                FROM intent_node_evidence_stage
                GROUP BY node_key, month
            ) AS first_month
              ON metrics.node_key = first_month.node_key
             AND metrics.first_month = first_month.month
            LEFT JOIN (
                SELECT node_key, month, min(search_frequency_rank) AS best_rank
                FROM intent_node_evidence_stage
                GROUP BY node_key, month
            ) AS last_month
              ON metrics.node_key = last_month.node_key
             AND metrics.last_month = last_month.month
        ),
        max_rank AS (
            SELECT greatest(coalesce(max(search_frequency_rank), 1), 2) AS value
            FROM intent_node_evidence_stage
        ),
        distinct_examples AS (
            SELECT
                node_key,
                normalized_keyword,
                min(search_frequency_rank) AS example_rank
            FROM intent_node_evidence_stage
            GROUP BY node_key, normalized_keyword
        ),
        ranked_examples AS (
            SELECT
                *,
                row_number() OVER (
                    PARTITION BY node_key
                    ORDER BY example_rank ASC NULLS LAST, normalized_keyword
                ) AS example_position
            FROM distinct_examples
        ),
        examples AS (
            SELECT
                node_key,
                string_agg(normalized_keyword, ' | ' ORDER BY example_position) AS example_keywords
            FROM ranked_examples
            WHERE example_position <= 10
            GROUP BY node_key
        ),
        scored AS (
            SELECT
                metrics.*,
                top_product.product,
                top_customization.customization,
                top_holiday.holiday,
                top_occasion.occasion,
                coalesce(legacy_nodes.legacy_market_node_count, 0) AS legacy_market_node_count,
                CASE
                    WHEN metrics.active_months = 1
                     AND metrics.last_month = latest_month.value
                    THEN 'emerging'
                    WHEN first_last.first_best_rank IS NULL
                      OR first_last.first_best_rank = 0
                    THEN 'stable'
                    WHEN (
                        (first_last.first_best_rank - first_last.last_best_rank)
                        * 100.0
                        / first_last.first_best_rank
                    ) >= 10
                    THEN 'growing'
                    WHEN (
                        (first_last.first_best_rank - first_last.last_best_rank)
                        * 100.0
                        / first_last.first_best_rank
                    ) <= -10
                    THEN 'declining'
                    ELSE 'stable'
                END AS trend,
                least(
                    100.0,
                    greatest(
                        0.0,
                        100.0
                        * (
                            1.0
                            - (
                                ln(greatest(CAST(metrics.best_rank AS DOUBLE), 1.0))
                                / ln(CAST(max_rank.value AS DOUBLE))
                            )
                        )
                    )
                ) AS best_rank_score,
                least(
                    100.0,
                    greatest(
                        0.0,
                        100.0
                        * (
                            1.0
                            - (
                                ln(greatest(CAST(metrics.p25_rank AS DOUBLE), 1.0))
                                / ln(CAST(max_rank.value AS DOUBLE))
                            )
                        )
                    )
                ) AS p25_rank_score,
                least(
                    100.0,
                    greatest(0.0, metrics.top1000_count * 100.0 / nullif(metrics.keyword_count, 0))
                ) AS top1000_coverage_score,
                examples.example_keywords
            FROM metrics
            LEFT JOIN top_product
              ON metrics.node_key = top_product.node_key
            LEFT JOIN top_customization
              ON metrics.node_key = top_customization.node_key
            LEFT JOIN top_holiday
              ON metrics.node_key = top_holiday.node_key
            LEFT JOIN top_occasion
              ON metrics.node_key = top_occasion.node_key
            LEFT JOIN legacy_nodes
              ON metrics.node_key = legacy_nodes.node_key
            LEFT JOIN first_last
              ON metrics.node_key = first_last.node_key
            LEFT JOIN examples
              ON metrics.node_key = examples.node_key
            CROSS JOIN latest_month
            CROSS JOIN max_rank
        )
        SELECT
            printf(
                'IMN%06d',
                row_number() OVER (
                    ORDER BY
                        round(
                            (best_rank_score * 0.60)
                            + (p25_rank_score * 0.25)
                            + (top1000_coverage_score * 0.15),
                            2
                        ) DESC,
                        best_rank ASC NULLS LAST,
                        p25_rank ASC NULLS LAST,
                        intent,
                        primary_audience_type,
                        primary_audience_value,
                        niche_type,
                        niche_value
                )
            ) AS intent_market_node_id,
            intent,
            primary_audience_type,
            primary_audience_value,
            niche_type,
            niche_value,
            recipient,
            profession,
            pet,
            interest,
            theme,
            lifestyle,
            product,
            customization,
            holiday,
            occasion,
            best_rank,
            p25_rank,
            median_rank,
            top100_count,
            top500_count,
            top1000_count,
            keyword_count,
            distinct_keyword_count,
            active_months,
            round(
                (best_rank_score * 0.60)
                + (p25_rank_score * 0.25)
                + (top1000_coverage_score * 0.15),
                2
            ) AS strength_score,
            trend,
            legacy_market_node_count,
            example_keywords
        FROM scored
        ORDER BY intent_market_node_id
        """
    )
    row_count = connection.execute(f"SELECT count(*) FROM {INTENT_MARKET_NODES_TABLE}").fetchone()[0]
    logger.info("Built %s with %s rows", INTENT_MARKET_NODES_TABLE, f"{row_count:,}")
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


def grouped_examples_query(
    dimension_column: str,
    value_column: str,
    output_value_name: str,
    where_clause: str,
) -> str:
    return f"""
        WITH source AS (
            SELECT
                intent,
                {value_column} AS {output_value_name},
                normalized_keyword,
                search_frequency_rank,
                month
            FROM {INTENT_KEYWORDS_TABLE}
            WHERE {where_clause}
        ),
        metrics AS (
            SELECT
                intent,
                {output_value_name},
                count(*) AS keyword_count,
                count(DISTINCT normalized_keyword) AS distinct_keyword_count,
                min(search_frequency_rank) AS best_rank,
                quantile_cont(CAST(search_frequency_rank AS DOUBLE), 0.25) AS p25_rank,
                sum(CASE WHEN search_frequency_rank <= 100 THEN 1 ELSE 0 END) AS top100_count,
                sum(CASE WHEN search_frequency_rank <= 1000 THEN 1 ELSE 0 END) AS top1000_count,
                count(DISTINCT month) AS active_months
            FROM source
            GROUP BY intent, {output_value_name}
        ),
        distinct_examples AS (
            SELECT
                intent,
                {output_value_name},
                normalized_keyword,
                min(search_frequency_rank) AS example_rank
            FROM source
            GROUP BY intent, {output_value_name}, normalized_keyword
        ),
        ranked_examples AS (
            SELECT
                *,
                row_number() OVER (
                    PARTITION BY intent, {output_value_name}
                    ORDER BY example_rank ASC NULLS LAST, normalized_keyword
                ) AS example_position
            FROM distinct_examples
        ),
        examples AS (
            SELECT
                intent,
                {output_value_name},
                string_agg(normalized_keyword, ' | ' ORDER BY example_position) AS example_keywords
            FROM ranked_examples
            WHERE example_position <= 5
            GROUP BY intent, {output_value_name}
        )
        SELECT
            metrics.*,
            examples.example_keywords
        FROM metrics
        LEFT JOIN examples
          ON metrics.intent = examples.intent
         AND metrics.{output_value_name} = examples.{output_value_name}
        ORDER BY
            metrics.best_rank ASC NULLS LAST,
            metrics.top1000_count DESC,
            metrics.keyword_count DESC,
            metrics.intent,
            metrics.{output_value_name}
    """


def export_reports(connection: duckdb.DuckDBPyConnection, output_dir: Path) -> None:
    logger.info("Exporting intent layer CSVs to %s", display_path(output_dir))
    output_dir.mkdir(parents=True, exist_ok=True)

    exports = {
        "intent_keywords.csv": f"""
            SELECT *
            FROM {INTENT_KEYWORDS_TABLE}
            ORDER BY keyword_id
        """,
        "intent_summary.csv": f"""
            SELECT *
            FROM {INTENT_SUMMARY_TABLE}
            ORDER BY best_rank ASC NULLS LAST, top1000_count DESC, keyword_count DESC, intent
        """,
        "intent_market_nodes.csv": f"""
            SELECT *
            FROM {INTENT_MARKET_NODES_TABLE}
            ORDER BY intent_market_node_id
        """,
        "top_intent_recipient.csv": grouped_examples_query(
            "recipient",
            "recipient",
            "recipient",
            "recipient IS NOT NULL",
        ),
        "top_intent_niche.csv": f"""
            WITH source AS (
                SELECT intent, niche_type, niche_value, normalized_keyword, search_frequency_rank, month
                FROM {INTENT_KEYWORDS_TABLE}
                WHERE niche_type IS NOT NULL
                  AND niche_value IS NOT NULL
                UNION ALL
                SELECT intent, 'interest' AS niche_type, interest AS niche_value, normalized_keyword, search_frequency_rank, month
                FROM {INTENT_KEYWORDS_TABLE}
                WHERE primary_audience_type = 'interest'
                  AND interest IS NOT NULL
            ),
            metrics AS (
                SELECT
                    intent,
                    niche_type,
                    niche_value,
                    count(*) AS keyword_count,
                    count(DISTINCT normalized_keyword) AS distinct_keyword_count,
                    min(search_frequency_rank) AS best_rank,
                    quantile_cont(CAST(search_frequency_rank AS DOUBLE), 0.25) AS p25_rank,
                    sum(CASE WHEN search_frequency_rank <= 100 THEN 1 ELSE 0 END) AS top100_count,
                    sum(CASE WHEN search_frequency_rank <= 1000 THEN 1 ELSE 0 END) AS top1000_count,
                    count(DISTINCT month) AS active_months
                FROM source
                GROUP BY intent, niche_type, niche_value
            ),
            distinct_examples AS (
                SELECT
                    intent,
                    niche_type,
                    niche_value,
                    normalized_keyword,
                    min(search_frequency_rank) AS example_rank
                FROM source
                GROUP BY intent, niche_type, niche_value, normalized_keyword
            ),
            ranked_examples AS (
                SELECT
                    *,
                    row_number() OVER (
                        PARTITION BY intent, niche_type, niche_value
                        ORDER BY example_rank ASC NULLS LAST, normalized_keyword
                    ) AS example_position
                FROM distinct_examples
            ),
            examples AS (
                SELECT
                    intent,
                    niche_type,
                    niche_value,
                    string_agg(normalized_keyword, ' | ' ORDER BY example_position) AS example_keywords
                FROM ranked_examples
                WHERE example_position <= 5
                GROUP BY intent, niche_type, niche_value
            )
            SELECT
                metrics.*,
                examples.example_keywords
            FROM metrics
            LEFT JOIN examples
              ON metrics.intent = examples.intent
             AND metrics.niche_type = examples.niche_type
             AND metrics.niche_value = examples.niche_value
            ORDER BY
                metrics.best_rank ASC NULLS LAST,
                metrics.top1000_count DESC,
                metrics.keyword_count DESC,
                metrics.intent,
                metrics.niche_type,
                metrics.niche_value
        """,
        "top_intent_product.csv": grouped_examples_query(
            "product",
            "product",
            "product",
            "product IS NOT NULL",
        ),
    }

    for file_name, query in exports.items():
        row_count = export_query_to_csv(connection, query, output_dir / file_name)
        logger.info("Exported %s with %s rows", file_name, f"{row_count:,}")


def log_summary(connection: duckdb.DuckDBPyConnection) -> None:
    logger.info("Intent layer summary")
    for table_name in [INTENT_KEYWORDS_TABLE, INTENT_SUMMARY_TABLE, INTENT_MARKET_NODES_TABLE]:
        row_count = connection.execute(f"SELECT count(*) FROM {table_name}").fetchone()[0]
        logger.info("  %s: %s rows", table_name, f"{row_count:,}")

    logger.info("Top intents:")
    for row in connection.execute(
        f"""
        SELECT intent, keyword_count, best_rank, top1000_count
        FROM {INTENT_SUMMARY_TABLE}
        ORDER BY best_rank ASC NULLS LAST, top1000_count DESC, keyword_count DESC
        LIMIT 10
        """
    ).fetchall():
        logger.info("  %s | keywords=%s | best=%s | top1000=%s", row[0], row[1], row[2], row[3])

    logger.info("Top intent market nodes:")
    for row in connection.execute(
        f"""
        SELECT
            intent_market_node_id,
            intent,
            primary_audience_type,
            primary_audience_value,
            niche_type,
            niche_value,
            best_rank,
            strength_score,
            trend
        FROM {INTENT_MARKET_NODES_TABLE}
        ORDER BY strength_score DESC, best_rank ASC NULLS LAST
        LIMIT 10
        """
    ).fetchall():
        logger.info(
            "  %s | %s + %s=%s + %s=%s | best=%s | strength=%s | %s",
            row[0],
            row[1],
            row[2],
            row[3],
            row[4],
            row[5],
            row[6],
            row[7],
            row[8],
        )


def build_intent_layer(database_path: Path, output_dir: Path, rebuild: bool) -> None:
    if not database_path.exists():
        raise FileNotFoundError(f"DuckDB database not found: {database_path}")

    with duckdb.connect(str(database_path)) as connection:
        validate_inputs(connection)
        log_input_counts(connection)
        ensure_rebuild_allowed(connection, rebuild)
        if rebuild:
            drop_output_tables(connection)

        build_intent_keywords(connection)
        build_intent_summary(connection)
        build_intent_market_nodes(connection)
        export_reports(connection, output_dir)
        log_summary(connection)


def main() -> None:
    configure_logging()
    args = parse_args()
    logger.info("Starting Intent Layer build")
    build_intent_layer(
        database_path=args.database.resolve(),
        output_dir=args.output_dir.resolve(),
        rebuild=args.rebuild,
    )
    logger.info("Intent Layer build complete")
    logger.info("Build log: %s", display_path(LOG_PATH))


if __name__ == "__main__":
    main()
