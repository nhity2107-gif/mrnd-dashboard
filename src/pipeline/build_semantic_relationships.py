"""Build business-meaningful semantic relationships from keyword entity edges."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import duckdb
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DUCKDB_PATH = PROJECT_ROOT / "data" / "output" / "aba.duckdb"
OUTPUT_DIR = PROJECT_ROOT / "data" / "output" / "semantic_relationships"
LOG_DIR = PROJECT_ROOT / "logs"
LOG_PATH = LOG_DIR / "build_semantic_relationships.log"

KEYWORD_ENTITY_EDGES_TABLE = "keyword_entity_edges"
SEMANTIC_RELATIONSHIPS_TABLE = "semantic_relationships"

INPUT_TABLES = [KEYWORD_ENTITY_EDGES_TABLE]
OUTPUT_TABLES = [SEMANTIC_RELATIONSHIPS_TABLE]

REQUIRED_EDGE_COLUMNS = {
    "keyword_id",
    "normalized_keyword",
    "raw_keyword",
    "entity_id",
    "entity_type",
    "entity_value",
    "month",
    "search_frequency_rank",
}

CORE_TYPES = ["recipient", "profession", "pet"]
NICHE_TYPES = ["interest", "theme", "lifestyle"]
SEASONALITY_TYPES = ["holiday", "occasion"]
SOLUTION_TYPES = ["product"]

ALLOWED_RELATIONSHIPS = [
    ("recipient", "interest", "demand_core_to_niche"),
    ("recipient", "theme", "demand_core_to_niche"),
    ("recipient", "lifestyle", "demand_core_to_niche"),
    ("profession", "interest", "demand_core_to_niche"),
    ("profession", "theme", "demand_core_to_niche"),
    ("profession", "lifestyle", "demand_core_to_niche"),
    ("pet", "interest", "demand_core_to_niche"),
    ("pet", "theme", "demand_core_to_niche"),
    ("pet", "lifestyle", "demand_core_to_niche"),
    ("recipient", "holiday", "demand_core_to_seasonality"),
    ("profession", "holiday", "demand_core_to_seasonality"),
    ("pet", "holiday", "demand_core_to_seasonality"),
    ("recipient", "occasion", "demand_core_to_seasonality"),
    ("profession", "occasion", "demand_core_to_seasonality"),
    ("recipient", "product", "demand_core_to_solution"),
    ("profession", "product", "demand_core_to_solution"),
    ("pet", "product", "demand_core_to_solution"),
]

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build semantic relationship table and CSV reports from keyword_entity_edges."
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Drop existing semantic_relationships before rebuilding.",
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
        help="Folder for semantic relationship CSV reports.",
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
        raise RuntimeError(
            "Missing required graph table(s): "
            f"{', '.join(missing_tables)}. Run build_knowledge_graph.py first."
        )

    missing_columns = sorted(REQUIRED_EDGE_COLUMNS - table_columns(connection, KEYWORD_ENTITY_EDGES_TABLE))
    if missing_columns:
        raise RuntimeError(
            f"{KEYWORD_ENTITY_EDGES_TABLE} is missing required columns: "
            f"{', '.join(missing_columns)}"
        )


def log_input_counts(connection: duckdb.DuckDBPyConnection) -> None:
    for table_name in INPUT_TABLES:
        row_count = connection.execute(f"SELECT count(*) FROM {table_name}").fetchone()[0]
        logger.info("Input %s: %s rows", table_name, f"{row_count:,}")


def ensure_rebuild_allowed(connection: duckdb.DuckDBPyConnection, rebuild: bool) -> None:
    existing_tables = [table_name for table_name in OUTPUT_TABLES if table_exists(connection, table_name)]
    if existing_tables and not rebuild:
        raise RuntimeError(
            "Semantic relationship tables already exist. Rerun with --rebuild to replace only "
            f"these tables: {', '.join(existing_tables)}"
        )


def drop_output_tables(connection: duckdb.DuckDBPyConnection) -> None:
    for table_name in OUTPUT_TABLES:
        logger.info("Dropping %s if it exists", table_name)
        connection.execute(f"DROP TABLE IF EXISTS {table_name}")


def allowed_relationship_values_sql() -> str:
    rows = ",\n            ".join(
        (
            f"({sql_literal(left_type)}, {sql_literal(right_type)}, "
            f"{sql_literal(relationship_type)})"
        )
        for left_type, right_type, relationship_type in ALLOWED_RELATIONSHIPS
    )
    return rows


def create_allowed_relationships(connection: duckdb.DuckDBPyConnection) -> None:
    connection.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE allowed_semantic_relationships (
            left_type VARCHAR,
            right_type VARCHAR,
            relationship_type VARCHAR
        )
        """
    )
    connection.execute(
        f"""
        INSERT INTO allowed_semantic_relationships
        VALUES
            {allowed_relationship_values_sql()}
        """
    )


def build_semantic_relationships_table(connection: duckdb.DuckDBPyConnection) -> int:
    logger.info("Building %s", SEMANTIC_RELATIONSHIPS_TABLE)
    create_allowed_relationships(connection)
    connection.execute(
        f"""
        CREATE TABLE {SEMANTIC_RELATIONSHIPS_TABLE} AS
        WITH max_rank AS (
            SELECT greatest(coalesce(max(search_frequency_rank), 1), 2) AS value
            FROM {KEYWORD_ENTITY_EDGES_TABLE}
        ),
        relationship_rows AS (
            SELECT
                left_edge.entity_type AS left_type,
                left_edge.entity_value AS left_value,
                right_edge.entity_type AS right_type,
                right_edge.entity_value AS right_value,
                allowed.relationship_type,
                left_edge.keyword_id,
                left_edge.normalized_keyword,
                left_edge.search_frequency_rank
            FROM {KEYWORD_ENTITY_EDGES_TABLE} AS left_edge
            JOIN {KEYWORD_ENTITY_EDGES_TABLE} AS right_edge
              ON left_edge.keyword_id = right_edge.keyword_id
            JOIN allowed_semantic_relationships AS allowed
              ON left_edge.entity_type = allowed.left_type
             AND right_edge.entity_type = allowed.right_type
        ),
        metrics AS (
            SELECT
                left_type,
                left_value,
                right_type,
                right_value,
                relationship_type,
                count(*) AS keyword_count,
                min(search_frequency_rank) AS best_rank,
                sum(CASE WHEN search_frequency_rank <= 100 THEN 1 ELSE 0 END) AS top100_count,
                sum(CASE WHEN search_frequency_rank <= 1000 THEN 1 ELSE 0 END) AS top1000_count,
                avg(search_frequency_rank) AS average_rank
            FROM relationship_rows
            GROUP BY
                left_type,
                left_value,
                right_type,
                right_value,
                relationship_type
        ),
        scored AS (
            SELECT
                metrics.*,
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
                        metrics.top100_count * 100.0 / nullif(metrics.keyword_count, 0)
                    )
                ) AS top100_coverage_score,
                least(
                    100.0,
                    greatest(
                        0.0,
                        metrics.top1000_count * 100.0 / nullif(metrics.keyword_count, 0)
                    )
                ) AS top1000_coverage_score
            FROM metrics
            CROSS JOIN max_rank
        ),
        distinct_examples AS (
            SELECT
                left_type,
                left_value,
                right_type,
                right_value,
                relationship_type,
                normalized_keyword,
                min(search_frequency_rank) AS example_rank
            FROM relationship_rows
            GROUP BY
                left_type,
                left_value,
                right_type,
                right_value,
                relationship_type,
                normalized_keyword
        ),
        ranked_examples AS (
            SELECT
                *,
                row_number() OVER (
                    PARTITION BY left_type, left_value, right_type, right_value, relationship_type
                    ORDER BY example_rank ASC NULLS LAST, normalized_keyword
                ) AS example_position
            FROM distinct_examples
        ),
        examples AS (
            SELECT
                left_type,
                left_value,
                right_type,
                right_value,
                relationship_type,
                string_agg(
                    normalized_keyword,
                    ' | '
                    ORDER BY example_position
                ) AS example_keywords
            FROM ranked_examples
            WHERE example_position <= 5
            GROUP BY
                left_type,
                left_value,
                right_type,
                right_value,
                relationship_type
        )
        SELECT
            scored.left_type,
            scored.left_value,
            scored.right_type,
            scored.right_value,
            scored.relationship_type,
            scored.best_rank,
            scored.top100_count,
            scored.top1000_count,
            round(scored.average_rank, 2) AS average_rank,
            round(
                (scored.best_rank_score * 0.70)
                + (scored.top1000_coverage_score * 0.20)
                + (scored.top100_coverage_score * 0.10),
                2
            ) AS strength,
            examples.example_keywords
        FROM scored
        LEFT JOIN examples
          ON scored.left_type = examples.left_type
         AND scored.left_value = examples.left_value
         AND scored.right_type = examples.right_type
         AND scored.right_value = examples.right_value
         AND scored.relationship_type = examples.relationship_type
        ORDER BY
            strength DESC,
            best_rank ASC NULLS LAST,
            top1000_count DESC,
            left_type,
            left_value,
            right_type,
            right_value
        """
    )
    row_count = connection.execute(f"SELECT count(*) FROM {SEMANTIC_RELATIONSHIPS_TABLE}").fetchone()[0]
    logger.info("Built %s with %s rows", SEMANTIC_RELATIONSHIPS_TABLE, f"{row_count:,}")
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
    logger.info("Exporting semantic relationship CSVs to %s", display_path(output_dir))
    output_dir.mkdir(parents=True, exist_ok=True)

    exports = {
        "semantic_relationships.csv": f"""
            SELECT *
            FROM {SEMANTIC_RELATIONSHIPS_TABLE}
            ORDER BY
                strength DESC,
                best_rank ASC NULLS LAST,
                top1000_count DESC,
                left_type,
                left_value,
                right_type,
                right_value
        """,
        "top_niche_candidates.csv": f"""
            SELECT *
            FROM {SEMANTIC_RELATIONSHIPS_TABLE}
            WHERE relationship_type = 'demand_core_to_niche'
            ORDER BY
                strength DESC,
                best_rank ASC NULLS LAST,
                top1000_count DESC,
                left_type,
                left_value,
                right_type,
                right_value
        """,
        "top_solution_candidates.csv": f"""
            SELECT *
            FROM {SEMANTIC_RELATIONSHIPS_TABLE}
            WHERE relationship_type = 'demand_core_to_solution'
            ORDER BY
                strength DESC,
                best_rank ASC NULLS LAST,
                top1000_count DESC,
                left_type,
                left_value,
                right_type,
                right_value
        """,
    }

    for file_name, query in exports.items():
        row_count = export_query_to_csv(connection, query, output_dir / file_name)
        logger.info("Exported %s with %s rows", file_name, f"{row_count:,}")


def log_summary(connection: duckdb.DuckDBPyConnection) -> None:
    logger.info("Semantic relationship summary")
    row_count = connection.execute(f"SELECT count(*) FROM {SEMANTIC_RELATIONSHIPS_TABLE}").fetchone()[0]
    logger.info("  %s: %s rows", SEMANTIC_RELATIONSHIPS_TABLE, f"{row_count:,}")

    logger.info("Rows by relationship type:")
    for relationship_type, count in connection.execute(
        f"""
        SELECT relationship_type, count(*)
        FROM {SEMANTIC_RELATIONSHIPS_TABLE}
        GROUP BY relationship_type
        ORDER BY relationship_type
        """
    ).fetchall():
        logger.info("  %s: %s", relationship_type, f"{count:,}")

    logger.info("Top semantic relationships:")
    for row in connection.execute(
        f"""
        SELECT
            left_type,
            left_value,
            right_type,
            right_value,
            relationship_type,
            best_rank,
            top1000_count,
            strength
        FROM {SEMANTIC_RELATIONSHIPS_TABLE}
        ORDER BY strength DESC, best_rank ASC NULLS LAST, top1000_count DESC
        LIMIT 10
        """
    ).fetchall():
        logger.info(
            "  %s=%s -> %s=%s | %s | best=%s | top1000=%s | strength=%s",
            row[0],
            row[1],
            row[2],
            row[3],
            row[4],
            row[5],
            row[6],
            row[7],
        )


def build_semantic_relationships(database_path: Path, output_dir: Path, rebuild: bool) -> None:
    if not database_path.exists():
        raise FileNotFoundError(f"DuckDB database not found: {database_path}")

    with duckdb.connect(str(database_path)) as connection:
        validate_inputs(connection)
        log_input_counts(connection)
        ensure_rebuild_allowed(connection, rebuild)
        if rebuild:
            drop_output_tables(connection)

        build_semantic_relationships_table(connection)
        export_reports(connection, output_dir)
        log_summary(connection)


def main() -> None:
    configure_logging()
    args = parse_args()
    logger.info("Starting Semantic Relationship build")
    build_semantic_relationships(
        database_path=args.database.resolve(),
        output_dir=args.output_dir.resolve(),
        rebuild=args.rebuild,
    )
    logger.info("Semantic Relationship build complete")
    logger.info("Build log: %s", display_path(LOG_PATH))


if __name__ == "__main__":
    main()
