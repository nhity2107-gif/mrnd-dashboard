"""Build Demand Segment tables from V3 demand and semantic evidence."""

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
OUTPUT_DIR = PROJECT_ROOT / "data" / "output" / "demand_segments"
LOG_DIR = PROJECT_ROOT / "logs"
LOG_PATH = LOG_DIR / "build_demand_segments.log"

DEMAND_MASTER_V3_TABLE = "demand_master_v3"
DEMAND_STRENGTH_V3_TABLE = "demand_strength_v3"
COMPOSITE_DEMANDS_TABLE = "composite_demands"
SEMANTIC_RELATIONSHIPS_TABLE = "semantic_relationships"
ENTITY_MASTER_TABLE = "entity_master"
MARKET_NODES_TABLE = "market_nodes"
INTENT_LAYER_TABLE = "intent_keywords"
KNOWLEDGE_GRAPH_TABLE = "keyword_entity_edges"

DEMAND_SEGMENTS_TABLE = "demand_segments"
SEGMENT_KEYWORDS_TABLE = "segment_keywords"

BASE_INPUT_TABLES = [
    COMPOSITE_DEMANDS_TABLE,
    SEMANTIC_RELATIONSHIPS_TABLE,
    ENTITY_MASTER_TABLE,
    MARKET_NODES_TABLE,
    INTENT_LAYER_TABLE,
    KNOWLEDGE_GRAPH_TABLE,
]
OUTPUT_TABLES = [
    SEGMENT_KEYWORDS_TABLE,
    DEMAND_SEGMENTS_TABLE,
]

DEMAND_SOURCE_COLUMNS = {
    "demand_id",
    "demand_name",
    "intent",
    "recipient",
    "profession",
    "interest",
    "occasion",
    "holiday",
    "lifestyle",
    "theme",
    "keyword_count",
    "best_rank",
    "median_rank",
    "active_months",
    "trend",
    "strength_score",
}

REQUIRED_COLUMNS = {
    COMPOSITE_DEMANDS_TABLE: {"demand_id", "demand_name", "intent", "best_rank"},
    SEMANTIC_RELATIONSHIPS_TABLE: {
        "left_type",
        "left_value",
        "right_type",
        "right_value",
        "relationship_type",
        "best_rank",
    },
    ENTITY_MASTER_TABLE: {"entity_id", "entity_type", "canonical", "active"},
    MARKET_NODES_TABLE: {"demand", "niche", "best_rank", "strength_score"},
    INTENT_LAYER_TABLE: {
        "keyword_id",
        "raw_keyword",
        "normalized_keyword",
        "month",
        "search_frequency_rank",
        "intent",
        "recipient",
        "profession",
        "pet",
        "interest",
        "theme",
        "lifestyle",
        "product",
        "customization",
        "holiday",
        "occasion",
    },
    KNOWLEDGE_GRAPH_TABLE: {
        "keyword_id",
        "entity_type",
        "entity_value",
        "normalized_keyword",
        "search_frequency_rank",
    },
}

SEGMENT_COLUMNS = [
    "segment_id",
    "parent_demand_id",
    "parent_demand",
    "segment_name",
    "intent",
    "recipient",
    "profession",
    "interest",
    "pet",
    "holiday",
    "occasion",
    "theme",
    "lifestyle",
    "keyword_count",
    "best_rank",
    "median_rank",
    "active_months",
    "trend",
    "segment_strength",
    "evidence_keywords",
]

PET_VALUES = {"bird", "cat", "dog", "fish", "horse"}
EXCLUDED_PARENT_INTENTS = {"apparel", "personalized"}
TREND_ORDER = {
    "growing": 1,
    "emerging": 2,
    "stable": 3,
    "declining": 4,
    "unknown": 5,
}

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build Demand Segment tables from V3 demand and semantic evidence."
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Drop existing Demand Segment tables before rebuilding.",
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
        help="Folder for Demand Segment CSV reports.",
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


def demand_source_table(connection: duckdb.DuckDBPyConnection) -> str:
    if table_exists(connection, DEMAND_MASTER_V3_TABLE):
        return DEMAND_MASTER_V3_TABLE
    if table_exists(connection, DEMAND_STRENGTH_V3_TABLE):
        logger.info(
            "%s is not present; using %s as the V3 demand source",
            DEMAND_MASTER_V3_TABLE,
            DEMAND_STRENGTH_V3_TABLE,
        )
        return DEMAND_STRENGTH_V3_TABLE
    raise RuntimeError(
        f"Missing required V3 demand source. Expected {DEMAND_MASTER_V3_TABLE} "
        f"or {DEMAND_STRENGTH_V3_TABLE}."
    )


def validate_inputs(connection: duckdb.DuckDBPyConnection, demand_table: str) -> None:
    missing_tables = [table_name for table_name in BASE_INPUT_TABLES if not table_exists(connection, table_name)]
    if missing_tables:
        raise RuntimeError(
            "Missing required table(s): "
            f"{', '.join(missing_tables)}. Run the intent, graph, semantic, and composite layers first."
        )

    missing_demand_columns = sorted(DEMAND_SOURCE_COLUMNS - table_columns(connection, demand_table))
    if missing_demand_columns:
        raise RuntimeError(
            f"{demand_table} is missing required columns: {', '.join(missing_demand_columns)}"
        )

    for table_name, required_columns in REQUIRED_COLUMNS.items():
        missing_columns = sorted(required_columns - table_columns(connection, table_name))
        if missing_columns:
            raise RuntimeError(
                f"{table_name} is missing required columns: {', '.join(missing_columns)}"
            )


def log_input_counts(connection: duckdb.DuckDBPyConnection, demand_table: str) -> None:
    for table_name in [demand_table, *BASE_INPUT_TABLES]:
        row_count = connection.execute(f"SELECT count(*) FROM {table_name}").fetchone()[0]
        logger.info("Input %s: %s rows", table_name, f"{row_count:,}")


def ensure_rebuild_allowed(connection: duckdb.DuckDBPyConnection, rebuild: bool) -> None:
    existing_tables = [table_name for table_name in OUTPUT_TABLES if table_exists(connection, table_name)]
    if existing_tables and not rebuild:
        raise RuntimeError(
            "Demand Segment tables already exist. Rerun with --rebuild to replace only "
            f"these tables: {', '.join(existing_tables)}"
        )


def drop_output_tables(connection: duckdb.DuckDBPyConnection) -> None:
    for table_name in OUTPUT_TABLES:
        logger.info("Dropping %s if it exists", table_name)
        connection.execute(f"DROP TABLE IF EXISTS {table_name}")


def nullable_column(table_alias: str, column_name: str) -> str:
    return f"nullif(trim(CAST({table_alias}.{column_name} AS VARCHAR)), '')"


def create_parent_demand_stage(connection: duckdb.DuckDBPyConnection, demand_table: str) -> None:
    logger.info("Creating parent demand stage from %s", demand_table)
    excluded_intents = ", ".join(f"'{intent}'" for intent in sorted(EXCLUDED_PARENT_INTENTS))
    pet_values = ", ".join(f"'{pet}'" for pet in sorted(PET_VALUES))

    connection.execute("DROP TABLE IF EXISTS parent_demand_stage")
    connection.execute(
        f"""
        CREATE TEMP TABLE parent_demand_stage AS
        WITH normalized AS (
            SELECT
                demand_id AS parent_demand_id,
                demand_name AS parent_demand,
                {nullable_column("demand", "intent")} AS parent_intent,
                lower({nullable_column("demand", "recipient")}) AS source_recipient,
                lower({nullable_column("demand", "profession")}) AS source_profession,
                lower({nullable_column("demand", "interest")}) AS source_interest,
                lower({nullable_column("demand", "occasion")}) AS source_occasion,
                lower({nullable_column("demand", "holiday")}) AS source_holiday,
                lower({nullable_column("demand", "lifestyle")}) AS source_lifestyle,
                lower({nullable_column("demand", "theme")}) AS source_theme,
                best_rank AS parent_best_rank,
                median_rank AS parent_median_rank,
                active_months AS parent_active_months,
                trend AS parent_trend,
                strength_score AS parent_strength
            FROM {demand_table} AS demand
        ),
        shaped AS (
            SELECT
                *,
                CASE
                    WHEN source_profession IS NOT NULL THEN 'profession'
                    WHEN source_recipient IN ({pet_values}) THEN 'pet'
                    WHEN source_recipient IS NOT NULL THEN 'recipient'
                    WHEN source_interest IS NOT NULL THEN 'interest'
                    ELSE NULL
                END AS parent_core_type,
                CASE
                    WHEN source_profession IS NOT NULL THEN source_profession
                    WHEN source_recipient IN ({pet_values}) THEN source_recipient
                    WHEN source_recipient IS NOT NULL THEN source_recipient
                    WHEN source_interest IS NOT NULL THEN source_interest
                    ELSE NULL
                END AS parent_core_value,
                CASE
                    WHEN source_recipient IS NOT NULL AND source_recipient NOT IN ({pet_values})
                    THEN source_recipient
                    ELSE NULL
                END AS parent_recipient,
                source_profession AS parent_profession,
                source_interest AS parent_interest,
                CASE
                    WHEN source_recipient IN ({pet_values}) THEN source_recipient
                    ELSE NULL
                END AS parent_pet
            FROM normalized
        )
        SELECT
            parent_demand_id,
            parent_demand,
            parent_intent,
            parent_core_type,
            parent_core_value,
            parent_recipient,
            parent_profession,
            parent_interest,
            parent_pet,
            parent_best_rank,
            parent_median_rank,
            parent_active_months,
            parent_trend,
            parent_strength
        FROM shaped
        WHERE parent_intent IS NOT NULL
          AND parent_intent NOT IN ({excluded_intents})
          AND parent_core_type IS NOT NULL
          AND source_occasion IS NULL
          AND source_holiday IS NULL
          AND source_lifestyle IS NULL
          AND source_theme IS NULL
          AND (
                CASE WHEN source_recipient IS NOT NULL THEN 1 ELSE 0 END
              + CASE WHEN source_profession IS NOT NULL THEN 1 ELSE 0 END
              + CASE WHEN source_interest IS NOT NULL THEN 1 ELSE 0 END
          ) = 1
        """
    )
    row_count = connection.execute("SELECT count(*) FROM parent_demand_stage").fetchone()[0]
    logger.info("Parent demand stage: %s rows", f"{row_count:,}")


def create_keyword_base_stage(connection: duckdb.DuckDBPyConnection) -> None:
    logger.info("Creating keyword base stage")
    connection.execute("DROP TABLE IF EXISTS segment_keyword_base_stage")
    connection.execute(
        f"""
        CREATE TEMP TABLE segment_keyword_base_stage AS
        SELECT
            keyword_id,
            raw_keyword,
            normalized_keyword,
            month,
            search_frequency_rank,
            lower({nullable_column("keyword", "intent")}) AS intent,
            lower({nullable_column("keyword", "recipient")}) AS recipient,
            lower({nullable_column("keyword", "profession")}) AS profession,
            lower({nullable_column("keyword", "pet")}) AS pet,
            lower({nullable_column("keyword", "interest")}) AS interest,
            lower({nullable_column("keyword", "theme")}) AS theme,
            lower({nullable_column("keyword", "lifestyle")}) AS lifestyle,
            lower({nullable_column("keyword", "holiday")}) AS holiday,
            lower({nullable_column("keyword", "occasion")}) AS occasion
        FROM {INTENT_LAYER_TABLE} AS keyword
        WHERE intent <> 'unknown'
          AND search_frequency_rank IS NOT NULL
          AND {nullable_column("keyword", "product")} IS NULL
          AND {nullable_column("keyword", "customization")} IS NULL
        """
    )
    row_count = connection.execute("SELECT count(*) FROM segment_keyword_base_stage").fetchone()[0]
    logger.info("Keyword base stage: %s rows", f"{row_count:,}")


def create_parent_match_stage(connection: duckdb.DuckDBPyConnection) -> None:
    logger.info("Creating parent keyword match stage")
    compatibility = """
        (
            keyword.intent = parent.parent_intent
            OR (keyword.intent = 'appreciation' AND parent.parent_intent = 'gift')
        )
    """

    parent_columns = """
        parent.parent_demand_id,
        parent.parent_demand,
        parent.parent_intent,
        parent.parent_core_type,
        parent.parent_core_value,
        parent.parent_recipient,
        parent.parent_profession,
        parent.parent_interest,
        parent.parent_pet,
        keyword.keyword_id,
        keyword.raw_keyword,
        keyword.normalized_keyword,
        keyword.month,
        keyword.search_frequency_rank,
        keyword.intent,
        keyword.recipient,
        keyword.profession,
        keyword.pet,
        keyword.interest,
        keyword.theme,
        keyword.lifestyle,
        keyword.holiday,
        keyword.occasion
    """

    connection.execute("DROP TABLE IF EXISTS segment_parent_match_stage")
    connection.execute(
        f"""
        CREATE TEMP TABLE segment_parent_match_stage AS
        SELECT
            {parent_columns},
            'profession_exact' AS parent_match_type
        FROM segment_keyword_base_stage AS keyword
        JOIN parent_demand_stage AS parent
          ON parent.parent_core_type = 'profession'
         AND keyword.profession = parent.parent_core_value
         AND {compatibility}

        UNION ALL

        SELECT
            {parent_columns},
            'recipient_exact' AS parent_match_type
        FROM segment_keyword_base_stage AS keyword
        JOIN parent_demand_stage AS parent
          ON parent.parent_core_type = 'recipient'
         AND keyword.recipient = parent.parent_core_value
         AND {compatibility}

        UNION ALL

        SELECT
            {parent_columns},
            'recipient_refinement' AS parent_match_type
        FROM segment_keyword_base_stage AS keyword
        JOIN parent_demand_stage AS parent
          ON parent.parent_core_type = 'recipient'
         AND keyword.recipient IS NOT NULL
         AND keyword.recipient <> parent.parent_core_value
         AND (' ' || keyword.recipient || ' ') LIKE ('% ' || parent.parent_core_value || ' %')
         AND {compatibility}

        UNION ALL

        SELECT
            {parent_columns},
            'pet_exact' AS parent_match_type
        FROM segment_keyword_base_stage AS keyword
        JOIN parent_demand_stage AS parent
          ON parent.parent_core_type = 'pet'
         AND (keyword.pet = parent.parent_core_value OR keyword.recipient = parent.parent_core_value)
         AND {compatibility}

        UNION ALL

        SELECT
            {parent_columns},
            'interest_exact' AS parent_match_type
        FROM segment_keyword_base_stage AS keyword
        JOIN parent_demand_stage AS parent
          ON parent.parent_core_type = 'interest'
         AND keyword.interest = parent.parent_core_value
         AND keyword.recipient IS NULL
         AND keyword.profession IS NULL
         AND keyword.pet IS NULL
         AND {compatibility}
        """
    )
    row_count = connection.execute("SELECT count(*) FROM segment_parent_match_stage").fetchone()[0]
    logger.info("Parent keyword match stage: %s rows", f"{row_count:,}")


def create_segment_candidate_stage(connection: duckdb.DuckDBPyConnection) -> None:
    logger.info("Creating segment candidate evidence stage")
    connection.execute("DROP TABLE IF EXISTS segment_candidate_evidence_stage")
    connection.execute(
        """
        CREATE TEMP TABLE segment_candidate_evidence_stage AS
        SELECT DISTINCT
            parent_demand_id,
            parent_demand,
            parent_intent,
            parent_core_type,
            parent_core_value,
            parent_recipient,
            parent_profession,
            parent_interest,
            parent_pet,
            keyword_id,
            raw_keyword,
            normalized_keyword,
            month,
            search_frequency_rank,
            intent,
            recipient,
            profession,
            pet,
            interest,
            theme,
            lifestyle,
            holiday,
            occasion,
            parent_match_type,
            'recipient_refinement' AS segment_dimension,
            recipient AS segment_value
        FROM segment_parent_match_stage
        WHERE parent_match_type = 'recipient_refinement'
          AND recipient IS NOT NULL

        UNION ALL

        SELECT DISTINCT
            parent_demand_id,
            parent_demand,
            parent_intent,
            parent_core_type,
            parent_core_value,
            parent_recipient,
            parent_profession,
            parent_interest,
            parent_pet,
            keyword_id,
            raw_keyword,
            normalized_keyword,
            month,
            search_frequency_rank,
            intent,
            recipient,
            profession,
            pet,
            interest,
            theme,
            lifestyle,
            holiday,
            occasion,
            parent_match_type,
            'profession' AS segment_dimension,
            profession AS segment_value
        FROM segment_parent_match_stage
        WHERE profession IS NOT NULL
          AND NOT (parent_core_type = 'profession' AND profession = parent_core_value)

        UNION ALL

        SELECT DISTINCT
            parent_demand_id,
            parent_demand,
            parent_intent,
            parent_core_type,
            parent_core_value,
            parent_recipient,
            parent_profession,
            parent_interest,
            parent_pet,
            keyword_id,
            raw_keyword,
            normalized_keyword,
            month,
            search_frequency_rank,
            intent,
            recipient,
            profession,
            pet,
            interest,
            theme,
            lifestyle,
            holiday,
            occasion,
            parent_match_type,
            'interest' AS segment_dimension,
            interest AS segment_value
        FROM segment_parent_match_stage
        WHERE interest IS NOT NULL
          AND NOT (parent_core_type = 'interest' AND interest = parent_core_value)

        UNION ALL

        SELECT DISTINCT
            parent_demand_id,
            parent_demand,
            parent_intent,
            parent_core_type,
            parent_core_value,
            parent_recipient,
            parent_profession,
            parent_interest,
            parent_pet,
            keyword_id,
            raw_keyword,
            normalized_keyword,
            month,
            search_frequency_rank,
            intent,
            recipient,
            profession,
            pet,
            interest,
            theme,
            lifestyle,
            holiday,
            occasion,
            parent_match_type,
            'pet' AS segment_dimension,
            pet AS segment_value
        FROM segment_parent_match_stage
        WHERE pet IS NOT NULL
          AND parent_match_type <> 'recipient_refinement'
          AND NOT (parent_core_type = 'pet' AND pet = parent_core_value)

        UNION ALL

        SELECT DISTINCT
            parent_demand_id,
            parent_demand,
            parent_intent,
            parent_core_type,
            parent_core_value,
            parent_recipient,
            parent_profession,
            parent_interest,
            parent_pet,
            keyword_id,
            raw_keyword,
            normalized_keyword,
            month,
            search_frequency_rank,
            intent,
            recipient,
            profession,
            pet,
            interest,
            theme,
            lifestyle,
            holiday,
            occasion,
            parent_match_type,
            'holiday' AS segment_dimension,
            holiday AS segment_value
        FROM segment_parent_match_stage
        WHERE holiday IS NOT NULL

        UNION ALL

        SELECT DISTINCT
            parent_demand_id,
            parent_demand,
            parent_intent,
            parent_core_type,
            parent_core_value,
            parent_recipient,
            parent_profession,
            parent_interest,
            parent_pet,
            keyword_id,
            raw_keyword,
            normalized_keyword,
            month,
            search_frequency_rank,
            intent,
            recipient,
            profession,
            pet,
            interest,
            theme,
            lifestyle,
            holiday,
            occasion,
            parent_match_type,
            'occasion' AS segment_dimension,
            CASE WHEN intent = 'appreciation' THEN 'appreciation' ELSE occasion END AS segment_value
        FROM segment_parent_match_stage
        WHERE intent = 'appreciation'
           OR (
                occasion IS NOT NULL
            AND NOT (holiday IS NOT NULL AND occasion = holiday)
           )

        UNION ALL

        SELECT DISTINCT
            parent_demand_id,
            parent_demand,
            parent_intent,
            parent_core_type,
            parent_core_value,
            parent_recipient,
            parent_profession,
            parent_interest,
            parent_pet,
            keyword_id,
            raw_keyword,
            normalized_keyword,
            month,
            search_frequency_rank,
            intent,
            recipient,
            profession,
            pet,
            interest,
            theme,
            lifestyle,
            holiday,
            occasion,
            parent_match_type,
            'theme' AS segment_dimension,
            theme AS segment_value
        FROM segment_parent_match_stage
        WHERE theme IS NOT NULL

        UNION ALL

        SELECT DISTINCT
            parent_demand_id,
            parent_demand,
            parent_intent,
            parent_core_type,
            parent_core_value,
            parent_recipient,
            parent_profession,
            parent_interest,
            parent_pet,
            keyword_id,
            raw_keyword,
            normalized_keyword,
            month,
            search_frequency_rank,
            intent,
            recipient,
            profession,
            pet,
            interest,
            theme,
            lifestyle,
            holiday,
            occasion,
            parent_match_type,
            'lifestyle' AS segment_dimension,
            lifestyle AS segment_value
        FROM segment_parent_match_stage
        WHERE lifestyle IS NOT NULL
        """
    )
    connection.execute(
        """
        DELETE FROM segment_candidate_evidence_stage
        WHERE segment_value IS NULL
           OR trim(segment_value) = ''
           OR segment_value = parent_core_value
        """
    )
    connection.execute(
        """
        UPDATE segment_candidate_evidence_stage
        SET occasion = 'appreciation'
        WHERE segment_dimension = 'occasion'
          AND segment_value = 'appreciation'
          AND occasion IS NULL
        """
    )
    row_count = connection.execute("SELECT count(*) FROM segment_candidate_evidence_stage").fetchone()[0]
    logger.info("Segment candidate evidence stage: %s rows", f"{row_count:,}")


def create_segment_metric_frame(connection: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    logger.info("Creating segment metric frame")
    return connection.execute(
        """
        WITH metrics AS (
            SELECT
                parent_demand_id,
                parent_demand,
                parent_intent,
                parent_core_type,
                parent_core_value,
                parent_recipient,
                parent_profession,
                parent_interest,
                parent_pet,
                segment_dimension,
                segment_value,
                parent_demand_id || '|' || segment_dimension || '|' || segment_value AS segment_key,
                count(*) AS keyword_count,
                count(DISTINCT normalized_keyword) AS distinct_keyword_count,
                min(search_frequency_rank) AS best_rank,
                quantile_cont(CAST(search_frequency_rank AS DOUBLE), 0.25) AS p25_rank,
                median(CAST(search_frequency_rank AS DOUBLE)) AS median_rank,
                count(DISTINCT month) AS active_months,
                min(month) AS first_month,
                max(month) AS last_month
            FROM segment_candidate_evidence_stage
            GROUP BY
                parent_demand_id,
                parent_demand,
                parent_intent,
                parent_core_type,
                parent_core_value,
                parent_recipient,
                parent_profession,
                parent_interest,
                parent_pet,
                segment_dimension,
                segment_value
        ),
        first_last AS (
            SELECT
                metrics.segment_key,
                first_month.best_rank AS first_best_rank,
                last_month.best_rank AS last_best_rank
            FROM metrics
            LEFT JOIN (
                SELECT
                    parent_demand_id || '|' || segment_dimension || '|' || segment_value AS segment_key,
                    month,
                    min(search_frequency_rank) AS best_rank
                FROM segment_candidate_evidence_stage
                GROUP BY segment_key, month
            ) AS first_month
              ON metrics.segment_key = first_month.segment_key
             AND metrics.first_month = first_month.month
            LEFT JOIN (
                SELECT
                    parent_demand_id || '|' || segment_dimension || '|' || segment_value AS segment_key,
                    month,
                    min(search_frequency_rank) AS best_rank
                FROM segment_candidate_evidence_stage
                GROUP BY segment_key, month
            ) AS last_month
              ON metrics.segment_key = last_month.segment_key
             AND metrics.last_month = last_month.month
        ),
        latest_month AS (
            SELECT max(month) AS value
            FROM segment_candidate_evidence_stage
        ),
        ranked_examples AS (
            SELECT
                parent_demand_id || '|' || segment_dimension || '|' || segment_value AS segment_key,
                normalized_keyword,
                min(search_frequency_rank) AS example_rank,
                row_number() OVER (
                    PARTITION BY parent_demand_id, segment_dimension, segment_value
                    ORDER BY min(search_frequency_rank) ASC NULLS LAST, normalized_keyword
                ) AS example_position
            FROM segment_candidate_evidence_stage
            GROUP BY
                parent_demand_id,
                segment_dimension,
                segment_value,
                normalized_keyword
        ),
        examples AS (
            SELECT
                segment_key,
                string_agg(normalized_keyword, ' | ' ORDER BY example_position) AS evidence_keywords
            FROM ranked_examples
            WHERE example_position <= 8
            GROUP BY segment_key
        ),
        max_rank AS (
            SELECT greatest(coalesce(max(search_frequency_rank), 1), 2) AS value
            FROM segment_candidate_evidence_stage
        ),
        scored AS (
            SELECT
                metrics.*,
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
                coalesce(examples.evidence_keywords, '') AS evidence_keywords,
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
                    greatest(
                        0.0,
                        100.0
                        * (
                            1.0
                            - (
                                ln(greatest(CAST(metrics.median_rank AS DOUBLE), 1.0))
                                / ln(CAST(max_rank.value AS DOUBLE))
                            )
                        )
                    )
                ) AS median_rank_score,
                least(100.0, metrics.active_months * 25.0) AS active_month_score
            FROM metrics
            LEFT JOIN first_last
              ON metrics.segment_key = first_last.segment_key
            LEFT JOIN examples
              ON metrics.segment_key = examples.segment_key
            CROSS JOIN latest_month
            CROSS JOIN max_rank
            WHERE metrics.distinct_keyword_count >= 1
        )
        SELECT
            segment_key,
            parent_demand_id,
            parent_demand,
            parent_intent,
            parent_core_type,
            parent_core_value,
            parent_recipient,
            parent_profession,
            parent_interest,
            parent_pet,
            segment_dimension,
            segment_value,
            keyword_count,
            best_rank,
            median_rank,
            active_months,
            trend,
            round(
                (best_rank_score * 0.45)
                + (p25_rank_score * 0.30)
                + (median_rank_score * 0.15)
                + (active_month_score * 0.10),
                2
            ) AS segment_strength,
            evidence_keywords
        FROM scored
        """
    ).df()


def clean_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value or "").strip()


def title_case(value: object) -> str:
    text = clean_text(value)
    return string.capwords(text) if text else ""


def strip_suffix(text: str, suffix: str) -> str:
    if text.lower().endswith(suffix.lower()):
        return text[: -len(suffix)].strip()
    return text


def segment_name(row: pd.Series) -> str:
    parent_demand = clean_text(row["parent_demand"])
    dimension = clean_text(row["segment_dimension"])
    value = title_case(row["segment_value"])
    if not parent_demand or not value:
        return parent_demand

    if dimension == "recipient_refinement":
        parent_suffix = ""
        for suffix in [" Gift", " Memorial", " Decor", " Matching", " Wedding"]:
            if parent_demand.lower().endswith(suffix.lower()):
                parent_suffix = suffix.strip()
                break
        return f"{value} {parent_suffix}".strip() if parent_suffix else value

    if dimension == "holiday":
        return f"{value} {parent_demand}"

    if dimension == "occasion":
        base = strip_suffix(parent_demand, " Gift")
        if parent_demand != base:
            return f"{base} {value} Gift"
        return f"{value} {parent_demand}"

    return f"{value} {parent_demand}"


def segment_dimension_values(row: pd.Series) -> dict[str, str | None]:
    dimension = clean_text(row["segment_dimension"])
    value = clean_text(row["segment_value"])
    recipient = clean_text(row["parent_recipient"]) or None
    profession = clean_text(row["parent_profession"]) or None
    interest = clean_text(row["parent_interest"]) or None
    pet = clean_text(row["parent_pet"]) or None
    holiday = None
    occasion = None
    theme = None
    lifestyle = None

    if dimension == "recipient_refinement":
        recipient = value or recipient
    elif dimension == "profession":
        profession = value or profession
    elif dimension == "interest":
        interest = value or interest
    elif dimension == "pet":
        pet = value or pet
    elif dimension == "holiday":
        holiday = value or None
    elif dimension == "occasion":
        occasion = value or None
    elif dimension == "theme":
        theme = value or None
    elif dimension == "lifestyle":
        lifestyle = value or None

    return {
        "recipient": recipient,
        "profession": profession,
        "interest": interest,
        "pet": pet,
        "holiday": holiday,
        "occasion": occasion,
        "theme": theme,
        "lifestyle": lifestyle,
    }


def build_demand_segments(connection: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    metrics = create_segment_metric_frame(connection)
    if metrics.empty:
        raise RuntimeError("No demand segments were produced from the available evidence")

    metrics["segment_name"] = metrics.apply(segment_name, axis=1)
    dimension_frame = pd.DataFrame(
        [segment_dimension_values(row) for _, row in metrics.iterrows()],
        index=metrics.index,
    )
    metrics = pd.concat([metrics, dimension_frame], axis=1)
    metrics["intent"] = metrics["parent_intent"].apply(clean_text)
    metrics["segment_name_key"] = metrics["segment_name"].str.lower().str.strip()
    metrics["trend_sort"] = metrics["trend"].map(TREND_ORDER).fillna(99)

    metrics = metrics[
        metrics["segment_name_key"].notna()
        & (metrics["segment_name_key"] != "")
        & (metrics["segment_name_key"] != metrics["parent_demand"].str.lower().str.strip())
    ].copy()

    metrics = metrics.sort_values(
        [
            "segment_strength",
            "best_rank",
            "active_months",
            "trend_sort",
            "segment_name_key",
            "parent_demand_id",
        ],
        ascending=[False, True, False, True, True, True],
        na_position="last",
    )
    metrics = metrics.drop_duplicates(subset=["segment_name_key"], keep="first").reset_index(drop=True)
    metrics.insert(0, "segment_id", [f"SEG{index:06d}" for index in range(1, len(metrics) + 1)])

    table_frame = metrics[
        [
            "segment_id",
            "parent_demand_id",
            "parent_demand",
            "segment_name",
            "intent",
            "recipient",
            "profession",
            "interest",
            "pet",
            "holiday",
            "occasion",
            "theme",
            "lifestyle",
            "keyword_count",
            "best_rank",
            "median_rank",
            "active_months",
            "trend",
            "segment_strength",
            "evidence_keywords",
        ]
    ].copy()

    connection.register("demand_segment_frame", table_frame)
    connection.register(
        "segment_id_map_frame",
        metrics[
            [
                "segment_key",
                "segment_id",
                "parent_demand_id",
                "parent_demand",
                "segment_name",
                "segment_dimension",
                "segment_value",
                "intent",
            ]
        ].copy(),
    )
    connection.execute(
        f"""
        CREATE TABLE {DEMAND_SEGMENTS_TABLE} AS
        SELECT {', '.join(SEGMENT_COLUMNS)}
        FROM demand_segment_frame
        ORDER BY
            segment_strength DESC,
            best_rank ASC NULLS LAST,
            active_months DESC,
            CASE trend
                WHEN 'growing' THEN 1
                WHEN 'emerging' THEN 2
                WHEN 'stable' THEN 3
                WHEN 'declining' THEN 4
                ELSE 5
            END,
            segment_name
        """
    )
    row_count = connection.execute(f"SELECT count(*) FROM {DEMAND_SEGMENTS_TABLE}").fetchone()[0]
    logger.info("Built %s with %s rows", DEMAND_SEGMENTS_TABLE, f"{row_count:,}")
    return table_frame


def build_segment_keywords(connection: duckdb.DuckDBPyConnection) -> int:
    logger.info("Building %s", SEGMENT_KEYWORDS_TABLE)
    connection.execute(
        f"""
        CREATE TABLE {SEGMENT_KEYWORDS_TABLE} AS
        SELECT DISTINCT
            id_map.segment_id,
            id_map.parent_demand_id,
            id_map.parent_demand,
            id_map.segment_name,
            id_map.intent,
            id_map.segment_dimension,
            id_map.segment_value,
            evidence.raw_keyword,
            evidence.normalized_keyword,
            evidence.month,
            evidence.search_frequency_rank
        FROM segment_candidate_evidence_stage AS evidence
        JOIN segment_id_map_frame AS id_map
          ON evidence.parent_demand_id || '|' || evidence.segment_dimension || '|' || evidence.segment_value
           = id_map.segment_key
        ORDER BY
            id_map.segment_id,
            evidence.search_frequency_rank ASC NULLS LAST,
            evidence.month,
            evidence.normalized_keyword
        """
    )
    row_count = connection.execute(f"SELECT count(*) FROM {SEGMENT_KEYWORDS_TABLE}").fetchone()[0]
    logger.info("Built %s with %s rows", SEGMENT_KEYWORDS_TABLE, f"{row_count:,}")
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
    logger.info("Exporting Demand Segment CSVs to %s", display_path(output_dir))
    output_dir.mkdir(parents=True, exist_ok=True)

    segment_order = """
        segment_strength DESC,
        best_rank ASC NULLS LAST,
        active_months DESC,
        CASE trend
            WHEN 'growing' THEN 1
            WHEN 'emerging' THEN 2
            WHEN 'stable' THEN 3
            WHEN 'declining' THEN 4
            ELSE 5
        END,
        segment_name
    """

    exports = {
        "demand_segments.csv": f"""
            SELECT {', '.join(SEGMENT_COLUMNS)}
            FROM {DEMAND_SEGMENTS_TABLE}
            ORDER BY {segment_order}
        """,
        "segment_keywords.csv": f"""
            SELECT *
            FROM {SEGMENT_KEYWORDS_TABLE}
            ORDER BY segment_id, search_frequency_rank ASC NULLS LAST, month, normalized_keyword
        """,
        "top_200_segments.csv": f"""
            SELECT {', '.join(SEGMENT_COLUMNS)}
            FROM {DEMAND_SEGMENTS_TABLE}
            ORDER BY {segment_order}
            LIMIT 200
        """,
    }

    for file_name, query in exports.items():
        row_count = export_query_to_csv(connection, query, output_dir / file_name)
        logger.info("Exported %s with %s rows", file_name, f"{row_count:,}")


def validate_outputs(connection: duckdb.DuckDBPyConnection) -> None:
    orphan_count = connection.execute(
        f"""
        SELECT count(*)
        FROM {DEMAND_SEGMENTS_TABLE}
        WHERE parent_demand_id IS NULL
           OR parent_demand IS NULL
        """
    ).fetchone()[0]
    if orphan_count:
        raise RuntimeError(f"Demand Segment validation failed: {orphan_count} orphan segment(s)")

    duplicate_count = connection.execute(
        f"""
        SELECT count(*)
        FROM (
            SELECT lower(segment_name) AS segment_name_key
            FROM {DEMAND_SEGMENTS_TABLE}
            GROUP BY lower(segment_name)
            HAVING count(*) > 1
        )
        """
    ).fetchone()[0]
    if duplicate_count:
        raise RuntimeError(
            f"Demand Segment validation failed: {duplicate_count} duplicate segment name(s)"
        )

    product_segment_count = connection.execute(
        f"""
        SELECT count(*)
        FROM {SEGMENT_KEYWORDS_TABLE}
        WHERE segment_dimension IN ('product', 'customization')
        """
    ).fetchone()[0]
    if product_segment_count:
        raise RuntimeError(
            "Demand Segment validation failed: product/customization segment evidence was generated"
        )

    logger.info("Validation passed: one parent per segment, no duplicate names, no product/customization segments")


def log_summary(connection: duckdb.DuckDBPyConnection) -> None:
    logger.info("Demand Segment summary")
    for table_name in [DEMAND_SEGMENTS_TABLE, SEGMENT_KEYWORDS_TABLE]:
        row_count = connection.execute(f"SELECT count(*) FROM {table_name}").fetchone()[0]
        logger.info("  %s: %s rows", table_name, f"{row_count:,}")

    logger.info("Segments by added dimension:")
    for dimension, count in connection.execute(
        f"""
        SELECT segment_dimension, count(DISTINCT segment_id)
        FROM {SEGMENT_KEYWORDS_TABLE}
        GROUP BY segment_dimension
        ORDER BY count(DISTINCT segment_id) DESC, segment_dimension
        """
    ).fetchall():
        logger.info("  %s: %s", dimension, f"{count:,}")

    logger.info("Top demand segments:")
    for row in connection.execute(
        f"""
        SELECT
            segment_id,
            parent_demand,
            segment_name,
            segment_strength,
            best_rank,
            median_rank,
            active_months,
            trend
        FROM {DEMAND_SEGMENTS_TABLE}
        ORDER BY
            segment_strength DESC,
            best_rank ASC NULLS LAST,
            active_months DESC
        LIMIT 10
        """
    ).fetchall():
        logger.info(
            "  %s | parent=%s | %s | strength=%s | best=%s | median=%s | active=%s | %s",
            row[0],
            row[1],
            row[2],
            row[3],
            row[4],
            round(float(row[5]), 2) if row[5] is not None else None,
            row[6],
            row[7],
        )


def build_demand_segment_layer(database_path: Path, output_dir: Path, rebuild: bool) -> None:
    if not database_path.exists():
        raise FileNotFoundError(f"DuckDB database not found: {database_path}")

    with duckdb.connect(str(database_path)) as connection:
        demand_table = demand_source_table(connection)
        validate_inputs(connection, demand_table)
        log_input_counts(connection, demand_table)
        ensure_rebuild_allowed(connection, rebuild)
        if rebuild:
            drop_output_tables(connection)

        create_parent_demand_stage(connection, demand_table)
        create_keyword_base_stage(connection)
        create_parent_match_stage(connection)
        create_segment_candidate_stage(connection)
        build_demand_segments(connection)
        build_segment_keywords(connection)
        validate_outputs(connection)
        export_reports(connection, output_dir)
        log_summary(connection)


def main() -> None:
    configure_logging()
    args = parse_args()
    logger.info("Starting Demand Segment build")
    build_demand_segment_layer(
        database_path=args.database.resolve(),
        output_dir=args.output_dir.resolve(),
        rebuild=args.rebuild,
    )
    logger.info("Demand Segment build complete")
    logger.info("Build log: %s", display_path(LOG_PATH))


if __name__ == "__main__":
    main()
