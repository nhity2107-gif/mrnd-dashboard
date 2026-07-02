"""Build deterministic Market Node tables from semantic relationships."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import duckdb
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DUCKDB_PATH = PROJECT_ROOT / "data" / "output" / "aba.duckdb"
OUTPUT_DIR = PROJECT_ROOT / "data" / "output" / "market_nodes"
LOG_DIR = PROJECT_ROOT / "logs"
LOG_PATH = LOG_DIR / "build_market_nodes.log"

SEMANTIC_RELATIONSHIPS_TABLE = "semantic_relationships"
DEMAND_MASTER_TABLE = "demand_master_v2"
DEMAND_PROFILE_TABLE = "demand_profile_v2"
DEMAND_KEYWORDS_TABLE = "demand_keywords_v2"
KEYWORD_ENTITY_EDGES_TABLE = "keyword_entity_edges"

MARKET_NODES_TABLE = "market_nodes"
MARKET_NODE_MONTHLY_TABLE = "market_node_monthly"
MARKET_NODE_EVIDENCE_TABLE = "market_node_evidence"

INPUT_TABLES = [
    SEMANTIC_RELATIONSHIPS_TABLE,
    DEMAND_MASTER_TABLE,
    DEMAND_PROFILE_TABLE,
    DEMAND_KEYWORDS_TABLE,
    KEYWORD_ENTITY_EDGES_TABLE,
]
OUTPUT_TABLES = [
    MARKET_NODE_EVIDENCE_TABLE,
    MARKET_NODE_MONTHLY_TABLE,
    MARKET_NODES_TABLE,
]

REQUIRED_COLUMNS = {
    SEMANTIC_RELATIONSHIPS_TABLE: {
        "left_type",
        "left_value",
        "right_type",
        "right_value",
        "relationship_type",
        "best_rank",
        "top100_count",
        "top1000_count",
        "average_rank",
        "strength",
        "example_keywords",
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
    DEMAND_PROFILE_TABLE: {
        "demand_id",
        "dimension",
        "value",
        "keyword_count",
        "best_rank",
        "top_1000_count",
    },
    DEMAND_KEYWORDS_TABLE: {
        "demand_id",
        "raw_keyword",
        "normalized_keyword",
        "month",
        "search_frequency_rank",
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

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build Market Node tables from semantic relationships and Demand V2 evidence."
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Drop existing market node tables before rebuilding.",
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
        help="Folder for market node CSV reports.",
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
            f"{', '.join(missing_tables)}. Run Demand V2, Knowledge Graph, and Semantic Relationship builds first."
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
            "Market node tables already exist. Rerun with --rebuild to replace only "
            f"these tables: {', '.join(existing_tables)}"
        )


def drop_output_tables(connection: duckdb.DuckDBPyConnection) -> None:
    for table_name in OUTPUT_TABLES:
        logger.info("Dropping %s if it exists", table_name)
        connection.execute(f"DROP TABLE IF EXISTS {table_name}")


def create_candidate_stage(connection: duckdb.DuckDBPyConnection) -> None:
    logger.info("Creating market node candidate stage")
    connection.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE market_node_candidate_stage AS
        WITH semantic_niches AS (
            SELECT
                left_type,
                left_value,
                right_type AS niche_type,
                right_value AS niche_value,
                strength AS semantic_strength
            FROM {SEMANTIC_RELATIONSHIPS_TABLE}
            WHERE relationship_type = 'demand_core_to_niche'
              AND right_type IN ('interest', 'theme', 'lifestyle')
        ),
        matched_demands AS (
            SELECT
                semantic_niches.left_type,
                semantic_niches.left_value,
                semantic_niches.niche_type,
                semantic_niches.niche_value,
                semantic_niches.semantic_strength,
                demand_master.demand_id,
                demand_master.demand_name,
                demand_master.primary_type,
                demand_master.primary_value,
                demand_master.primary_intent,
                demand_master.best_rank AS demand_best_rank,
                demand_master.demand_strength_score,
                profile.keyword_count AS profile_keyword_count,
                profile.best_rank AS profile_best_rank,
                profile.top_1000_count AS profile_top1000_count
            FROM semantic_niches
            JOIN {DEMAND_MASTER_TABLE} AS demand_master
              ON (
                    semantic_niches.left_type = 'recipient'
                AND demand_master.primary_type = 'recipient'
                AND demand_master.primary_value = semantic_niches.left_value
              )
              OR (
                    semantic_niches.left_type = 'profession'
                AND demand_master.primary_type = 'profession'
                AND demand_master.primary_value = semantic_niches.left_value
              )
              OR (
                    semantic_niches.left_type = 'recipient'
                AND demand_master.primary_type = 'pet_role'
                AND demand_master.primary_value = semantic_niches.left_value
              )
              OR (
                    semantic_niches.left_type = 'pet'
                AND demand_master.primary_type = 'pet_role'
                AND (
                       demand_master.primary_value = semantic_niches.left_value
                    OR starts_with(demand_master.primary_value, semantic_niches.left_value || ' ')
                )
              )
            JOIN {DEMAND_PROFILE_TABLE} AS profile
              ON demand_master.demand_id = profile.demand_id
             AND semantic_niches.niche_type = profile.dimension
             AND semantic_niches.niche_value = profile.value
            WHERE demand_master.primary_type <> 'unclassified'
        ),
        ranked_demands AS (
            SELECT
                *,
                row_number() OVER (
                    PARTITION BY
                        left_type,
                        left_value,
                        niche_type,
                        niche_value,
                        primary_type,
                        primary_value
                    ORDER BY
                        CASE primary_intent
                            WHEN 'gift' THEN 1
                            WHEN 'personalized' THEN 2
                            WHEN 'general' THEN 3
                            ELSE 4
                        END,
                        demand_strength_score DESC,
                        demand_best_rank ASC NULLS LAST,
                        demand_id
                ) AS demand_choice_rank
            FROM matched_demands
        )
        SELECT DISTINCT
            concat(demand_id, '|', niche_type, '|', niche_value) AS node_key,
            demand_id,
            demand_name,
            primary_type,
            primary_value,
            primary_intent,
            left_type,
            left_value,
            niche_type,
            niche_value,
            semantic_strength
        FROM ranked_demands
        WHERE demand_choice_rank = 1
        """
    )
    row_count = connection.execute("SELECT count(*) FROM market_node_candidate_stage").fetchone()[0]
    logger.info("Candidate market nodes: %s rows", f"{row_count:,}")


def create_evidence_stage(connection: duckdb.DuckDBPyConnection) -> None:
    logger.info("Creating market node evidence stage")
    connection.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE market_node_evidence_stage AS
        SELECT DISTINCT
            candidates.node_key,
            candidates.demand_id,
            candidates.demand_name,
            candidates.primary_type,
            candidates.primary_value,
            candidates.left_type,
            candidates.left_value,
            candidates.niche_type,
            candidates.niche_value,
            demand_keywords.raw_keyword,
            demand_keywords.normalized_keyword,
            demand_keywords.month,
            demand_keywords.search_frequency_rank
        FROM market_node_candidate_stage AS candidates
        JOIN {DEMAND_KEYWORDS_TABLE} AS demand_keywords
          ON candidates.demand_id = demand_keywords.demand_id
        JOIN {KEYWORD_ENTITY_EDGES_TABLE} AS niche_edges
          ON demand_keywords.normalized_keyword = niche_edges.normalized_keyword
         AND demand_keywords.raw_keyword = niche_edges.raw_keyword
         AND demand_keywords.month = niche_edges.month
         AND demand_keywords.search_frequency_rank = niche_edges.search_frequency_rank
         AND candidates.niche_type = niche_edges.entity_type
         AND candidates.niche_value = niche_edges.entity_value
        """
    )
    row_count = connection.execute("SELECT count(*) FROM market_node_evidence_stage").fetchone()[0]
    logger.info("Candidate evidence rows: %s", f"{row_count:,}")


def create_monthly_stage(connection: duckdb.DuckDBPyConnection) -> None:
    logger.info("Creating market node monthly stage")
    connection.execute(
        """
        CREATE OR REPLACE TEMP TABLE market_node_monthly_stage AS
        SELECT
            node_key,
            month,
            min(search_frequency_rank) AS best_rank,
            quantile_cont(CAST(search_frequency_rank AS DOUBLE), 0.25) AS p25_rank,
            sum(CASE WHEN search_frequency_rank <= 100 THEN 1 ELSE 0 END) AS top100,
            sum(CASE WHEN search_frequency_rank <= 1000 THEN 1 ELSE 0 END) AS top1000,
            count(*) AS keyword_count
        FROM market_node_evidence_stage
        GROUP BY node_key, month
        """
    )


def create_qualified_node_stage(connection: duckdb.DuckDBPyConnection) -> None:
    logger.info("Creating qualified market node stage")
    connection.execute(
        """
        CREATE OR REPLACE TEMP TABLE market_node_metric_stage AS
        WITH metrics AS (
            SELECT
                evidence.node_key,
                min(evidence.demand_name) AS demand,
                min(evidence.niche_value) AS niche,
                min(CASE
                    WHEN evidence.left_type = 'recipient' THEN evidence.left_value
                    WHEN evidence.primary_type = 'pet_role' THEN evidence.primary_value
                    ELSE NULL
                END) AS recipient,
                min(CASE
                    WHEN evidence.left_type = 'profession' THEN evidence.left_value
                    ELSE NULL
                END) AS profession,
                min(CASE
                    WHEN evidence.left_type = 'pet' THEN evidence.left_value
                    WHEN evidence.primary_type = 'pet_role' AND starts_with(evidence.primary_value, 'dog')
                    THEN 'dog'
                    WHEN evidence.primary_type = 'pet_role' AND starts_with(evidence.primary_value, 'cat')
                    THEN 'cat'
                    ELSE NULL
                END) AS pet,
                min(CASE WHEN evidence.niche_type = 'interest' THEN evidence.niche_value ELSE NULL END)
                    AS interest,
                min(CASE WHEN evidence.niche_type = 'theme' THEN evidence.niche_value ELSE NULL END)
                    AS theme,
                min(CASE WHEN evidence.niche_type = 'lifestyle' THEN evidence.niche_value ELSE NULL END)
                    AS lifestyle,
                min(evidence.search_frequency_rank) AS best_rank,
                quantile_cont(CAST(evidence.search_frequency_rank AS DOUBLE), 0.25) AS p25_rank,
                median(CAST(evidence.search_frequency_rank AS DOUBLE)) AS median_rank,
                sum(CASE WHEN evidence.search_frequency_rank <= 100 THEN 1 ELSE 0 END) AS top100,
                sum(CASE WHEN evidence.search_frequency_rank <= 500 THEN 1 ELSE 0 END) AS top500,
                sum(CASE WHEN evidence.search_frequency_rank <= 1000 THEN 1 ELSE 0 END) AS top1000,
                count(DISTINCT evidence.month) AS active_months,
                count(*) AS keyword_rows,
                count(DISTINCT evidence.normalized_keyword) AS distinct_keyword_count,
                min(evidence.month) AS first_month,
                max(evidence.month) AS last_month
            FROM market_node_evidence_stage AS evidence
            GROUP BY evidence.node_key
        ),
        latest_month AS (
            SELECT max(month) AS value
            FROM market_node_evidence_stage
        ),
        first_last AS (
            SELECT
                metrics.node_key,
                first_month.best_rank AS first_best_rank,
                last_month.best_rank AS last_best_rank
            FROM metrics
            LEFT JOIN market_node_monthly_stage AS first_month
              ON metrics.node_key = first_month.node_key
             AND metrics.first_month = first_month.month
            LEFT JOIN market_node_monthly_stage AS last_month
              ON metrics.node_key = last_month.node_key
             AND metrics.last_month = last_month.month
        ),
        top_holiday AS (
            SELECT node_key, entity_value AS holiday
            FROM (
                SELECT
                    evidence.node_key,
                    holiday_edges.entity_value,
                    row_number() OVER (
                        PARTITION BY evidence.node_key
                        ORDER BY
                            min(evidence.search_frequency_rank) ASC NULLS LAST,
                            count(*) DESC,
                            holiday_edges.entity_value
                    ) AS position
                FROM market_node_evidence_stage AS evidence
                JOIN keyword_entity_edges AS holiday_edges
                  ON evidence.normalized_keyword = holiday_edges.normalized_keyword
                 AND evidence.raw_keyword = holiday_edges.raw_keyword
                 AND evidence.month = holiday_edges.month
                 AND evidence.search_frequency_rank = holiday_edges.search_frequency_rank
                 AND holiday_edges.entity_type = 'holiday'
                GROUP BY evidence.node_key, holiday_edges.entity_value
            )
            WHERE position = 1
        ),
        top_occasion AS (
            SELECT node_key, entity_value AS occasion
            FROM (
                SELECT
                    evidence.node_key,
                    occasion_edges.entity_value,
                    row_number() OVER (
                        PARTITION BY evidence.node_key
                        ORDER BY
                            min(evidence.search_frequency_rank) ASC NULLS LAST,
                            count(*) DESC,
                            occasion_edges.entity_value
                    ) AS position
                FROM market_node_evidence_stage AS evidence
                JOIN keyword_entity_edges AS occasion_edges
                  ON evidence.normalized_keyword = occasion_edges.normalized_keyword
                 AND evidence.raw_keyword = occasion_edges.raw_keyword
                 AND evidence.month = occasion_edges.month
                 AND evidence.search_frequency_rank = occasion_edges.search_frequency_rank
                 AND occasion_edges.entity_type = 'occasion'
                GROUP BY evidence.node_key, occasion_edges.entity_value
            )
            WHERE position = 1
        ),
        max_rank AS (
            SELECT greatest(coalesce(max(search_frequency_rank), 1), 2) AS value
            FROM market_node_evidence_stage
        ),
        scored AS (
            SELECT
                metrics.*,
                top_holiday.holiday,
                top_occasion.occasion,
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
                    greatest(0.0, metrics.top1000 * 100.0 / nullif(metrics.keyword_rows, 0))
                ) AS top1000_coverage_score,
                least(
                    100.0,
                    greatest(0.0, metrics.top100 * 100.0 / nullif(metrics.keyword_rows, 0))
                ) AS top100_coverage_score
            FROM metrics
            LEFT JOIN first_last
              ON metrics.node_key = first_last.node_key
            LEFT JOIN top_holiday
              ON metrics.node_key = top_holiday.node_key
            LEFT JOIN top_occasion
              ON metrics.node_key = top_occasion.node_key
            CROSS JOIN latest_month
            CROSS JOIN max_rank
            WHERE metrics.distinct_keyword_count >= 10
               OR metrics.top1000 >= 5
        )
        SELECT
            node_key,
            demand,
            niche,
            recipient,
            profession,
            pet,
            interest,
            theme,
            lifestyle,
            holiday,
            occasion,
            best_rank,
            p25_rank,
            median_rank,
            top100,
            top500,
            top1000,
            active_months,
            round(
                (best_rank_score * 0.55)
                + (p25_rank_score * 0.25)
                + (top1000_coverage_score * 0.15)
                + (top100_coverage_score * 0.05),
                2
            ) AS strength_score,
            trend
        FROM scored
        """
    )
    row_count = connection.execute("SELECT count(*) FROM market_node_metric_stage").fetchone()[0]
    logger.info("Qualified market nodes: %s", f"{row_count:,}")


def build_market_nodes_table(connection: duckdb.DuckDBPyConnection) -> int:
    logger.info("Building %s", MARKET_NODES_TABLE)
    connection.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE market_node_id_stage AS
        SELECT
            printf(
                'MN%06d',
                row_number() OVER (
                    ORDER BY
                        strength_score DESC,
                        best_rank ASC NULLS LAST,
                        p25_rank ASC NULLS LAST,
                        demand,
                        niche
                )
            ) AS market_node_id,
            *
        FROM market_node_metric_stage
        """
    )
    connection.execute(
        f"""
        CREATE TABLE {MARKET_NODES_TABLE} AS
        SELECT
            market_node_id,
            demand,
            niche,
            recipient,
            profession,
            pet,
            interest,
            theme,
            lifestyle,
            holiday,
            occasion,
            best_rank,
            p25_rank,
            median_rank,
            top100,
            top500,
            top1000,
            active_months,
            strength_score,
            trend
        FROM market_node_id_stage
        ORDER BY market_node_id
        """
    )
    row_count = connection.execute(f"SELECT count(*) FROM {MARKET_NODES_TABLE}").fetchone()[0]
    logger.info("Built %s with %s rows", MARKET_NODES_TABLE, f"{row_count:,}")
    return int(row_count)


def build_market_node_monthly(connection: duckdb.DuckDBPyConnection) -> int:
    logger.info("Building %s", MARKET_NODE_MONTHLY_TABLE)
    connection.execute(
        f"""
        CREATE TABLE {MARKET_NODE_MONTHLY_TABLE} AS
        SELECT
            market_node_id,
            monthly.month,
            monthly.best_rank,
            monthly.p25_rank,
            monthly.top100,
            monthly.top1000,
            monthly.keyword_count
        FROM market_node_monthly_stage AS monthly
        JOIN market_node_id_stage AS node_ids
          ON monthly.node_key = node_ids.node_key
        ORDER BY market_node_id, monthly.month
        """
    )
    row_count = connection.execute(f"SELECT count(*) FROM {MARKET_NODE_MONTHLY_TABLE}").fetchone()[0]
    logger.info("Built %s with %s rows", MARKET_NODE_MONTHLY_TABLE, f"{row_count:,}")
    return int(row_count)


def build_market_node_evidence(connection: duckdb.DuckDBPyConnection) -> int:
    logger.info("Building %s", MARKET_NODE_EVIDENCE_TABLE)
    connection.execute(
        f"""
        CREATE TABLE {MARKET_NODE_EVIDENCE_TABLE} AS
        SELECT
            node_ids.market_node_id,
            evidence.raw_keyword,
            evidence.normalized_keyword,
            evidence.month,
            evidence.search_frequency_rank
        FROM market_node_evidence_stage AS evidence
        JOIN market_node_id_stage AS node_ids
          ON evidence.node_key = node_ids.node_key
        ORDER BY
            node_ids.market_node_id,
            evidence.search_frequency_rank ASC NULLS LAST,
            evidence.month,
            evidence.normalized_keyword
        """
    )
    row_count = connection.execute(f"SELECT count(*) FROM {MARKET_NODE_EVIDENCE_TABLE}").fetchone()[0]
    logger.info("Built %s with %s rows", MARKET_NODE_EVIDENCE_TABLE, f"{row_count:,}")
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
    logger.info("Exporting market node CSVs to %s", display_path(output_dir))
    output_dir.mkdir(parents=True, exist_ok=True)

    exports = {
        "market_nodes.csv": f"""
            SELECT *
            FROM {MARKET_NODES_TABLE}
            ORDER BY market_node_id
        """,
        "market_node_monthly.csv": f"""
            SELECT *
            FROM {MARKET_NODE_MONTHLY_TABLE}
            ORDER BY market_node_id, month
        """,
        "market_node_evidence.csv": f"""
            SELECT *
            FROM {MARKET_NODE_EVIDENCE_TABLE}
            ORDER BY market_node_id, search_frequency_rank ASC NULLS LAST, month, normalized_keyword
        """,
        "top_market_nodes.csv": f"""
            SELECT *
            FROM {MARKET_NODES_TABLE}
            ORDER BY
                strength_score DESC,
                best_rank ASC NULLS LAST,
                p25_rank ASC NULLS LAST,
                market_node_id
        """,
    }

    for file_name, query in exports.items():
        row_count = export_query_to_csv(connection, query, output_dir / file_name)
        logger.info("Exported %s with %s rows", file_name, f"{row_count:,}")


def log_summary(connection: duckdb.DuckDBPyConnection) -> None:
    logger.info("Market Node summary")
    for table_name in [MARKET_NODES_TABLE, MARKET_NODE_MONTHLY_TABLE, MARKET_NODE_EVIDENCE_TABLE]:
        row_count = connection.execute(f"SELECT count(*) FROM {table_name}").fetchone()[0]
        logger.info("  %s: %s rows", table_name, f"{row_count:,}")

    logger.info("Top market nodes:")
    for row in connection.execute(
        f"""
        SELECT
            market_node_id,
            demand,
            niche,
            best_rank,
            p25_rank,
            top1000,
            strength_score,
            trend
        FROM {MARKET_NODES_TABLE}
        ORDER BY strength_score DESC, best_rank ASC NULLS LAST
        LIMIT 10
        """
    ).fetchall():
        logger.info(
            "  %s | %s + %s | best=%s | p25=%s | top1000=%s | strength=%s | %s",
            row[0],
            row[1],
            row[2],
            row[3],
            round(float(row[4]), 2) if row[4] is not None else None,
            row[5],
            row[6],
            row[7],
        )


def build_market_nodes(database_path: Path, output_dir: Path, rebuild: bool) -> None:
    if not database_path.exists():
        raise FileNotFoundError(f"DuckDB database not found: {database_path}")

    with duckdb.connect(str(database_path)) as connection:
        validate_inputs(connection)
        log_input_counts(connection)
        ensure_rebuild_allowed(connection, rebuild)
        if rebuild:
            drop_output_tables(connection)

        create_candidate_stage(connection)
        create_evidence_stage(connection)
        create_monthly_stage(connection)
        create_qualified_node_stage(connection)
        build_market_nodes_table(connection)
        build_market_node_monthly(connection)
        build_market_node_evidence(connection)
        export_reports(connection, output_dir)
        log_summary(connection)


def main() -> None:
    configure_logging()
    args = parse_args()
    logger.info("Starting Market Node build")
    build_market_nodes(
        database_path=args.database.resolve(),
        output_dir=args.output_dir.resolve(),
        rebuild=args.rebuild,
    )
    logger.info("Market Node build complete")
    logger.info("Build log: %s", display_path(LOG_PATH))


if __name__ == "__main__":
    main()
