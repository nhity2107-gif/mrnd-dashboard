"""Build Composite Demand V3 tables from the intent and entity layers."""

from __future__ import annotations

import argparse
import logging
import string
from pathlib import Path

import duckdb
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DUCKDB_PATH = PROJECT_ROOT / "data" / "output" / "aba.duckdb"
OUTPUT_DIR = PROJECT_ROOT / "data" / "output" / "composite_demands"
LOG_DIR = PROJECT_ROOT / "logs"
LOG_PATH = LOG_DIR / "build_composite_demands.log"

INTENT_KEYWORDS_TABLE = "intent_keywords"
INTENT_SUMMARY_TABLE = "intent_summary"
INTENT_MARKET_NODES_TABLE = "intent_market_nodes"
SEMANTIC_RELATIONSHIPS_TABLE = "semantic_relationships"
DEMAND_OBJECTS_TABLE = "demand_objects"
KEYWORD_ENTITY_EDGES_TABLE = "keyword_entity_edges"

COMPOSITE_DEMANDS_TABLE = "composite_demands"
COMPOSITE_KEYWORDS_TABLE = "composite_keywords"
DEMAND_STRENGTH_V3_TABLE = "demand_strength_v3"

INPUT_TABLES = [
    INTENT_KEYWORDS_TABLE,
    INTENT_SUMMARY_TABLE,
    INTENT_MARKET_NODES_TABLE,
    SEMANTIC_RELATIONSHIPS_TABLE,
    DEMAND_OBJECTS_TABLE,
    KEYWORD_ENTITY_EDGES_TABLE,
]
OUTPUT_TABLES = [
    DEMAND_STRENGTH_V3_TABLE,
    COMPOSITE_KEYWORDS_TABLE,
    COMPOSITE_DEMANDS_TABLE,
]

REQUIRED_COLUMNS = {
    INTENT_KEYWORDS_TABLE: {
        "keyword_id",
        "raw_keyword",
        "normalized_keyword",
        "month",
        "search_frequency_rank",
        "intent",
        "primary_audience_type",
        "primary_audience_value",
        "niche_type",
        "niche_value",
        "recipient",
        "profession",
        "pet",
        "interest",
        "occasion",
        "holiday",
        "lifestyle",
        "theme",
        "product",
    },
    INTENT_SUMMARY_TABLE: {"intent", "best_rank"},
    INTENT_MARKET_NODES_TABLE: {"intent", "primary_audience_type", "primary_audience_value"},
    SEMANTIC_RELATIONSHIPS_TABLE: {
        "left_type",
        "left_value",
        "right_type",
        "right_value",
        "relationship_type",
        "best_rank",
    },
    DEMAND_OBJECTS_TABLE: {"demand_id", "normalized_keyword", "search_frequency_rank"},
    KEYWORD_ENTITY_EDGES_TABLE: {
        "keyword_id",
        "entity_type",
        "entity_value",
        "search_frequency_rank",
    },
}

COMPOSITE_COLUMNS = [
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
    "product_count",
    "keyword_count",
    "best_rank",
    "p25_rank",
    "median_rank",
    "average_rank",
    "active_months",
    "trend",
]

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build Composite Demand V3 tables from intent and entity evidence."
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Drop existing composite demand tables before rebuilding.",
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
        help="Folder for Composite Demand V3 CSV reports.",
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
            f"{', '.join(missing_tables)}. Run the intent and semantic layers first."
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
            "Composite demand tables already exist. Rerun with --rebuild to replace only "
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
    return string.capwords(text) if text else ""


def clean_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value or "").strip()


def composite_name(row: pd.Series) -> str:
    intent = clean_text(row["intent"])
    audience_type = clean_text(row["audience_type"])
    audience = clean_text(row["audience_value"])
    interest = clean_text(row["interest"])
    holiday = clean_text(row["holiday"])
    occasion = clean_text(row["occasion"])
    lifestyle = clean_text(row["lifestyle"])
    theme = clean_text(row["theme"])

    if audience_type == "interest" and interest == audience:
        interest = ""

    audience_name = title_case(audience)
    if not audience_name:
        audience_name = "Unspecified"

    if intent == "gift":
        if holiday:
            return f"{title_case(holiday)} {audience_name} Gift"
        if interest:
            return f"{audience_name} {title_case(interest)} Gift"
        if lifestyle:
            return f"{audience_name} {title_case(lifestyle)} Gift"
        if theme:
            return f"{audience_name} {title_case(theme)} Gift"
        if occasion:
            return f"{title_case(occasion)} {audience_name} Gift"
        return f"{audience_name} Gift"

    if intent == "appreciation":
        return f"{audience_name} Appreciation"
    if intent == "memorial":
        return f"{audience_name} Memorial"
    if intent == "personalized":
        if interest:
            return f"Personalized {audience_name} {title_case(interest)}"
        return f"Personalized {audience_name}"
    if intent == "christmas":
        if interest:
            return f"Christmas {audience_name} {title_case(interest)}"
        return f"Christmas {audience_name}"
    if intent and intent != "unknown":
        if interest:
            return f"{audience_name} {title_case(interest)} {title_case(intent)}"
        return f"{audience_name} {title_case(intent)}"

    if interest:
        return f"{audience_name} {title_case(interest)} Demand"
    if lifestyle:
        return f"{audience_name} {title_case(lifestyle)} Demand"
    if theme:
        return f"{audience_name} {title_case(theme)} Demand"
    return f"{audience_name} Demand"


def create_composite_evidence_stage(connection: duckdb.DuckDBPyConnection) -> None:
    logger.info("Creating composite demand evidence stage")
    connection.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE composite_evidence_stage AS
        WITH usable_keywords AS (
            SELECT
                keyword_id,
                raw_keyword,
                normalized_keyword,
                month,
                search_frequency_rank,
                intent,
                primary_audience_type,
                primary_audience_value,
                niche_type,
                niche_value,
                recipient,
                profession,
                pet,
                interest,
                occasion,
                holiday,
                lifestyle,
                theme,
                product
            FROM {INTENT_KEYWORDS_TABLE}
            WHERE intent <> 'unknown'
              AND primary_audience_type IS NOT NULL
              AND primary_audience_value IS NOT NULL
        ),
        normalized AS (
            SELECT
                *,
                CASE
                    WHEN primary_audience_type = 'profession' THEN primary_audience_value
                    ELSE NULL
                END AS composite_profession,
                CASE
                    WHEN primary_audience_type = 'recipient' THEN primary_audience_value
                    WHEN primary_audience_type = 'pet' THEN primary_audience_value
                    ELSE NULL
                END AS composite_recipient,
                CASE
                    WHEN intent IN ('appreciation', 'memorial') THEN NULL
                    WHEN niche_type = 'interest' THEN niche_value
                    WHEN primary_audience_type = 'interest' THEN primary_audience_value
                    ELSE NULL
                END AS composite_interest,
                CASE
                    WHEN intent = 'appreciation' THEN 'appreciation'
                    WHEN niche_type = 'occasion' THEN niche_value
                    ELSE occasion
                END AS composite_occasion,
                CASE
                    WHEN intent = 'christmas' THEN 'christmas'
                    WHEN holiday IS NOT NULL THEN holiday
                    ELSE NULL
                END AS composite_holiday,
                CASE WHEN niche_type = 'lifestyle' THEN niche_value ELSE lifestyle END
                    AS composite_lifestyle,
                CASE WHEN niche_type = 'theme' THEN niche_value ELSE theme END
                    AS composite_theme
            FROM usable_keywords
        )
        SELECT
            concat(
                intent,
                '|',
                coalesce(composite_recipient, ''),
                '|',
                coalesce(composite_profession, ''),
                '|',
                coalesce(composite_interest, ''),
                '|',
                coalesce(composite_occasion, ''),
                '|',
                coalesce(composite_holiday, ''),
                '|',
                coalesce(composite_lifestyle, ''),
                '|',
                coalesce(composite_theme, '')
            ) AS composite_key,
            *
        FROM normalized
        """
    )
    row_count = connection.execute("SELECT count(*) FROM composite_evidence_stage").fetchone()[0]
    logger.info("Composite evidence stage: %s rows", f"{row_count:,}")


def create_composite_metric_stage(connection: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    logger.info("Creating composite demand metric stage")
    return connection.execute(
        """
        WITH metrics AS (
            SELECT
                composite_key,
                min(intent) AS intent,
                min(primary_audience_type) AS audience_type,
                min(primary_audience_value) AS audience_value,
                min(composite_recipient) AS recipient,
                min(composite_profession) AS profession,
                min(composite_interest) AS interest,
                min(composite_occasion) AS occasion,
                min(composite_holiday) AS holiday,
                min(composite_lifestyle) AS lifestyle,
                min(composite_theme) AS theme,
                count(DISTINCT product) AS product_count,
                count(*) AS keyword_count,
                min(search_frequency_rank) AS best_rank,
                quantile_cont(CAST(search_frequency_rank AS DOUBLE), 0.25) AS p25_rank,
                median(CAST(search_frequency_rank AS DOUBLE)) AS median_rank,
                avg(search_frequency_rank) AS average_rank,
                count(DISTINCT month) AS active_months,
                count(DISTINCT normalized_keyword) AS distinct_keyword_count,
                min(month) AS first_month,
                max(month) AS last_month
            FROM composite_evidence_stage
            GROUP BY composite_key
        ),
        first_last AS (
            SELECT
                metrics.composite_key,
                first_month.best_rank AS first_best_rank,
                last_month.best_rank AS last_best_rank
            FROM metrics
            LEFT JOIN (
                SELECT composite_key, month, min(search_frequency_rank) AS best_rank
                FROM composite_evidence_stage
                GROUP BY composite_key, month
            ) AS first_month
              ON metrics.composite_key = first_month.composite_key
             AND metrics.first_month = first_month.month
            LEFT JOIN (
                SELECT composite_key, month, min(search_frequency_rank) AS best_rank
                FROM composite_evidence_stage
                GROUP BY composite_key, month
            ) AS last_month
              ON metrics.composite_key = last_month.composite_key
             AND metrics.last_month = last_month.month
        ),
        latest_month AS (
            SELECT max(month) AS value
            FROM composite_evidence_stage
        )
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
            END AS trend
        FROM metrics
        LEFT JOIN first_last
          ON metrics.composite_key = first_last.composite_key
        CROSS JOIN latest_month
        WHERE metrics.distinct_keyword_count >= 2
           OR metrics.best_rank <= 100000
        """
    ).df()


def build_composite_demands(connection: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    metrics = create_composite_metric_stage(connection)
    if metrics.empty:
        raise RuntimeError("No composite demands were produced from intent_keywords")

    metrics["demand_name"] = metrics.apply(composite_name, axis=1)
    metrics = metrics.sort_values(
        ["best_rank", "p25_rank", "keyword_count", "composite_key"],
        ascending=[True, True, False, True],
        na_position="last",
    ).reset_index(drop=True)
    metrics.insert(0, "demand_id", [f"CD{index:06d}" for index in range(1, len(metrics) + 1)])

    connection.register("composite_metric_frame", metrics)
    connection.execute(
        f"""
        CREATE TABLE {COMPOSITE_DEMANDS_TABLE} AS
        SELECT
            demand_id,
            demand_name,
            intent,
            recipient,
            profession,
            interest,
            occasion,
            holiday,
            lifestyle,
            theme,
            product_count,
            keyword_count,
            best_rank,
            p25_rank,
            median_rank,
            round(average_rank, 2) AS average_rank,
            active_months,
            trend
        FROM composite_metric_frame
        ORDER BY demand_id
        """
    )
    connection.execute(
        """
        CREATE OR REPLACE TEMP TABLE composite_id_map AS
        SELECT composite_key, demand_id
        FROM composite_metric_frame
        """
    )
    row_count = connection.execute(f"SELECT count(*) FROM {COMPOSITE_DEMANDS_TABLE}").fetchone()[0]
    logger.info("Built %s with %s rows", COMPOSITE_DEMANDS_TABLE, f"{row_count:,}")
    return metrics


def build_composite_keywords(connection: duckdb.DuckDBPyConnection) -> int:
    logger.info("Building %s", COMPOSITE_KEYWORDS_TABLE)
    connection.execute(
        f"""
        CREATE TABLE {COMPOSITE_KEYWORDS_TABLE} AS
        SELECT
            id_map.demand_id,
            evidence.raw_keyword,
            evidence.normalized_keyword,
            evidence.month,
            evidence.search_frequency_rank
        FROM composite_evidence_stage AS evidence
        JOIN composite_id_map AS id_map
          ON evidence.composite_key = id_map.composite_key
        ORDER BY
            id_map.demand_id,
            evidence.search_frequency_rank ASC NULLS LAST,
            evidence.month,
            evidence.normalized_keyword
        """
    )
    row_count = connection.execute(f"SELECT count(*) FROM {COMPOSITE_KEYWORDS_TABLE}").fetchone()[0]
    logger.info("Built %s with %s rows", COMPOSITE_KEYWORDS_TABLE, f"{row_count:,}")
    return int(row_count)


def build_demand_strength_v3(connection: duckdb.DuckDBPyConnection) -> int:
    logger.info("Building %s", DEMAND_STRENGTH_V3_TABLE)
    connection.execute(
        f"""
        CREATE TABLE {DEMAND_STRENGTH_V3_TABLE} AS
        WITH max_rank AS (
            SELECT greatest(coalesce(max(search_frequency_rank), 1), 2) AS value
            FROM composite_evidence_stage
        ),
        scored AS (
            SELECT
                demands.*,
                least(
                    100.0,
                    greatest(
                        0.0,
                        100.0
                        * (
                            1.0
                            - (
                                ln(greatest(CAST(demands.best_rank AS DOUBLE), 1.0))
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
                                ln(greatest(CAST(demands.p25_rank AS DOUBLE), 1.0))
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
                                ln(greatest(CAST(demands.median_rank AS DOUBLE), 1.0))
                                / ln(CAST(max_rank.value AS DOUBLE))
                            )
                        )
                    )
                ) AS median_rank_score,
                least(100.0, demands.active_months * 25.0) AS active_month_score
            FROM {COMPOSITE_DEMANDS_TABLE} AS demands
            CROSS JOIN max_rank
        )
        SELECT
            demand_id,
            demand_name,
            intent,
            recipient,
            profession,
            interest,
            occasion,
            holiday,
            lifestyle,
            theme,
            product_count,
            keyword_count,
            best_rank,
            p25_rank,
            median_rank,
            average_rank,
            active_months,
            trend,
            round(
                (best_rank_score * 0.45)
                + (p25_rank_score * 0.30)
                + (median_rank_score * 0.15)
                + (active_month_score * 0.10),
                2
            ) AS strength_score
        FROM scored
        ORDER BY
            strength_score DESC,
            best_rank ASC NULLS LAST,
            p25_rank ASC NULLS LAST,
            demand_id
        """
    )
    row_count = connection.execute(f"SELECT count(*) FROM {DEMAND_STRENGTH_V3_TABLE}").fetchone()[0]
    logger.info("Built %s with %s rows", DEMAND_STRENGTH_V3_TABLE, f"{row_count:,}")
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
    logger.info("Exporting Composite Demand CSVs to %s", display_path(output_dir))
    output_dir.mkdir(parents=True, exist_ok=True)

    exports = {
        "composite_demands.csv": f"SELECT * FROM {COMPOSITE_DEMANDS_TABLE} ORDER BY demand_id",
        "composite_keywords.csv": f"""
            SELECT *
            FROM {COMPOSITE_KEYWORDS_TABLE}
            ORDER BY demand_id, search_frequency_rank ASC NULLS LAST, month, normalized_keyword
        """,
        "top_composite_demands.csv": f"""
            SELECT *
            FROM {DEMAND_STRENGTH_V3_TABLE}
            ORDER BY
                strength_score DESC,
                best_rank ASC NULLS LAST,
                p25_rank ASC NULLS LAST,
                demand_id
        """,
        "demand_strength_v3.csv": f"""
            SELECT *
            FROM {DEMAND_STRENGTH_V3_TABLE}
            ORDER BY
                strength_score DESC,
                best_rank ASC NULLS LAST,
                p25_rank ASC NULLS LAST,
                demand_id
        """,
    }

    for file_name, query in exports.items():
        row_count = export_query_to_csv(connection, query, output_dir / file_name)
        logger.info("Exported %s with %s rows", file_name, f"{row_count:,}")


def log_summary(connection: duckdb.DuckDBPyConnection) -> None:
    logger.info("Composite Demand summary")
    for table_name in [COMPOSITE_DEMANDS_TABLE, COMPOSITE_KEYWORDS_TABLE, DEMAND_STRENGTH_V3_TABLE]:
        row_count = connection.execute(f"SELECT count(*) FROM {table_name}").fetchone()[0]
        logger.info("  %s: %s rows", table_name, f"{row_count:,}")

    logger.info("Top composite demands:")
    for row in connection.execute(
        f"""
        SELECT demand_id, demand_name, best_rank, p25_rank, median_rank, active_months, strength_score, trend
        FROM {DEMAND_STRENGTH_V3_TABLE}
        ORDER BY strength_score DESC, best_rank ASC NULLS LAST
        LIMIT 10
        """
    ).fetchall():
        logger.info(
            "  %s | %s | best=%s | p25=%s | median=%s | active=%s | strength=%s | %s",
            row[0],
            row[1],
            row[2],
            round(float(row[3]), 2) if row[3] is not None else None,
            round(float(row[4]), 2) if row[4] is not None else None,
            row[5],
            row[6],
            row[7],
        )


def build_composite_demand_layer(database_path: Path, output_dir: Path, rebuild: bool) -> None:
    if not database_path.exists():
        raise FileNotFoundError(f"DuckDB database not found: {database_path}")

    with duckdb.connect(str(database_path)) as connection:
        validate_inputs(connection)
        log_input_counts(connection)
        ensure_rebuild_allowed(connection, rebuild)
        if rebuild:
            drop_output_tables(connection)

        create_composite_evidence_stage(connection)
        build_composite_demands(connection)
        build_composite_keywords(connection)
        build_demand_strength_v3(connection)
        export_reports(connection, output_dir)
        log_summary(connection)


def main() -> None:
    configure_logging()
    args = parse_args()
    logger.info("Starting Composite Demand build")
    build_composite_demand_layer(
        database_path=args.database.resolve(),
        output_dir=args.output_dir.resolve(),
        rebuild=args.rebuild,
    )
    logger.info("Composite Demand build complete")
    logger.info("Build log: %s", display_path(LOG_PATH))


if __name__ == "__main__":
    main()
