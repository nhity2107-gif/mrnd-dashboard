"""Build deterministic knowledge graph tables from ABA demand objects."""

from __future__ import annotations

import argparse
import logging
import re
from pathlib import Path

import duckdb
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DUCKDB_PATH = PROJECT_ROOT / "data" / "output" / "aba.duckdb"
MASTER_DIR = PROJECT_ROOT / "knowledge" / "master"
OUTPUT_DIR = PROJECT_ROOT / "data" / "output" / "knowledge_graph"
LOG_DIR = PROJECT_ROOT / "logs"
LOG_PATH = LOG_DIR / "build_knowledge_graph.log"

DEMAND_OBJECTS_TABLE = "demand_objects"
NORMALIZED_TABLE = "normalized_keywords"

ENTITY_MASTER_TABLE = "entity_master"
KEYWORD_ENTITY_EDGES_TABLE = "keyword_entity_edges"
ENTITY_COOCCURRENCE_TABLE = "entity_cooccurrence"

INPUT_TABLES = [
    DEMAND_OBJECTS_TABLE,
    NORMALIZED_TABLE,
]
OUTPUT_TABLES = [
    ENTITY_COOCCURRENCE_TABLE,
    KEYWORD_ENTITY_EDGES_TABLE,
    ENTITY_MASTER_TABLE,
]

ENTITY_COLUMNS = [
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
]

MASTER_COLUMNS = ["canonical", "entity_type", "aliases", "priority", "active", "notes"]
ENTITY_MASTER_COLUMNS = ["entity_id", "entity_type", "canonical", "aliases", "priority", "active"]

DEMAND_OBJECT_COLUMNS = {
    "demand_id",
    "raw_keyword",
    "normalized_keyword",
    "month",
    "search_frequency_rank",
    *ENTITY_COLUMNS,
}
NORMALIZED_COLUMNS = {
    "raw_search_term",
    "normalized_search_term",
    "month",
    "search_frequency_rank",
}

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build entity graph tables from demand_objects and knowledge/master dictionaries."
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Drop existing knowledge graph tables before rebuilding.",
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=DUCKDB_PATH,
        help="Path to data/output/aba.duckdb.",
    )
    parser.add_argument(
        "--master-dir",
        type=Path,
        default=MASTER_DIR,
        help="Folder containing knowledge/master CSV dictionaries.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help="Folder for exported knowledge graph CSV reports.",
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


def validate_inputs(connection: duckdb.DuckDBPyConnection, master_dir: Path) -> None:
    if not master_dir.exists():
        raise FileNotFoundError(f"Knowledge master directory not found: {master_dir}")

    missing_tables = [table_name for table_name in INPUT_TABLES if not table_exists(connection, table_name)]
    if missing_tables:
        raise RuntimeError(f"Missing required input table(s): {', '.join(missing_tables)}")

    required_columns = {
        DEMAND_OBJECTS_TABLE: DEMAND_OBJECT_COLUMNS,
        NORMALIZED_TABLE: NORMALIZED_COLUMNS,
    }
    for table_name, columns in required_columns.items():
        missing_columns = sorted(columns - table_columns(connection, table_name))
        if missing_columns:
            raise RuntimeError(
                f"{table_name} is missing required columns: {', '.join(missing_columns)}"
            )

    master_paths = sorted(master_dir.glob("*.csv"))
    if not master_paths:
        raise RuntimeError(f"No knowledge master CSV files found in {master_dir}")


def log_input_counts(connection: duckdb.DuckDBPyConnection) -> None:
    for table_name in INPUT_TABLES:
        row_count = connection.execute(f"SELECT count(*) FROM {table_name}").fetchone()[0]
        logger.info("Input %s: %s rows", table_name, f"{row_count:,}")


def ensure_rebuild_allowed(connection: duckdb.DuckDBPyConnection, rebuild: bool) -> None:
    existing_tables = [table_name for table_name in OUTPUT_TABLES if table_exists(connection, table_name)]
    if existing_tables and not rebuild:
        raise RuntimeError(
            "Knowledge graph tables already exist. Rerun with --rebuild to replace only "
            f"these graph tables: {', '.join(existing_tables)}"
        )


def drop_output_tables(connection: duckdb.DuckDBPyConnection) -> None:
    for table_name in OUTPUT_TABLES:
        logger.info("Dropping %s if it exists", table_name)
        connection.execute(f"DROP TABLE IF EXISTS {table_name}")


def normalize_text(value: object) -> str:
    text = "" if pd.isna(value) else str(value)
    text = text.strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text


def normalize_entity_type(value: object) -> str:
    text = normalize_text(value)
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return re.sub(r"_+", "_", text).strip("_")


def parse_priority(value: object) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return 0


def parse_active(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y", "active"}


def alias_set(value: object) -> set[str]:
    if pd.isna(value):
        return set()
    return {
        normalize_text(part)
        for part in str(value).split("|")
        if normalize_text(part)
    }


def merge_entity_record(
    records: dict[tuple[str, str], dict[str, object]],
    entity_type: str,
    canonical: str,
    aliases: set[str],
    priority: int,
    active: bool,
) -> None:
    key = (entity_type, canonical)
    existing = records.get(key)
    if existing is None:
        records[key] = {
            "entity_type": entity_type,
            "canonical": canonical,
            "aliases": set(aliases),
            "priority": priority,
            "active": active,
        }
        return

    existing["aliases"] = set(existing["aliases"]) | aliases
    existing["priority"] = max(int(existing["priority"]), priority)
    existing["active"] = bool(existing["active"]) or active


def load_master_entities(master_dir: Path) -> dict[tuple[str, str], dict[str, object]]:
    records: dict[tuple[str, str], dict[str, object]] = {}
    master_paths = sorted(master_dir.glob("*.csv"))
    logger.info("Loading %s knowledge master file(s)", len(master_paths))

    for master_path in master_paths:
        frame = pd.read_csv(master_path, dtype=str).fillna("")
        missing_columns = [column for column in MASTER_COLUMNS if column not in frame.columns]
        if missing_columns:
            raise RuntimeError(
                f"{master_path.name} is missing required columns: {', '.join(missing_columns)}"
            )

        for _, row in frame.iterrows():
            entity_type = normalize_entity_type(row["entity_type"])
            if entity_type not in ENTITY_COLUMNS:
                continue

            canonical = normalize_text(row["canonical"])
            if not canonical:
                continue

            aliases = alias_set(row["aliases"])
            priority = parse_priority(row["priority"])
            active = parse_active(row["active"])
            merge_entity_record(records, entity_type, canonical, aliases, priority, active)

    logger.info("Loaded %s master entity records", f"{len(records):,}")
    return records


def observed_entity_rows(connection: duckdb.DuckDBPyConnection) -> list[tuple[str, str]]:
    selects = [
        (
            f"SELECT {sql_literal(entity_type)} AS entity_type, "
            f"trim(CAST({entity_type} AS VARCHAR)) AS canonical "
            f"FROM {DEMAND_OBJECTS_TABLE} "
            f"WHERE {entity_type} IS NOT NULL AND trim(CAST({entity_type} AS VARCHAR)) <> ''"
        )
        for entity_type in ENTITY_COLUMNS
    ]
    query = "\nUNION\n".join(selects)
    return [
        (row[0], normalize_text(row[1]))
        for row in connection.execute(query).fetchall()
        if row[1]
    ]


def entity_master_frame(
    connection: duckdb.DuckDBPyConnection,
    master_dir: Path,
) -> pd.DataFrame:
    records = load_master_entities(master_dir)

    observed_rows = observed_entity_rows(connection)
    added_observed = 0
    for entity_type, canonical in observed_rows:
        key = (entity_type, canonical)
        if key in records:
            continue
        merge_entity_record(records, entity_type, canonical, set(), 0, True)
        added_observed += 1

    logger.info("Added %s observed-only entity records", f"{added_observed:,}")

    rows = []
    for record in records.values():
        rows.append(
            {
                "entity_type": record["entity_type"],
                "canonical": record["canonical"],
                "aliases": "|".join(sorted(set(record["aliases"]))),
                "priority": int(record["priority"]),
                "active": bool(record["active"]),
            }
        )

    frame = pd.DataFrame(rows)
    frame = frame.sort_values(
        ["entity_type", "canonical"],
        ascending=[True, True],
    ).reset_index(drop=True)
    frame.insert(0, "entity_id", [f"ENT{index:06d}" for index in range(1, len(frame) + 1)])
    return frame[ENTITY_MASTER_COLUMNS]


def build_entity_master(connection: duckdb.DuckDBPyConnection, master_dir: Path) -> int:
    logger.info("Building %s", ENTITY_MASTER_TABLE)
    frame = entity_master_frame(connection, master_dir)

    connection.register("entity_master_frame", frame)
    connection.execute(
        f"""
        CREATE TABLE {ENTITY_MASTER_TABLE} AS
        SELECT
            entity_id,
            entity_type,
            canonical,
            aliases,
            priority,
            active
        FROM entity_master_frame
        """
    )
    connection.unregister("entity_master_frame")

    row_count = len(frame)
    logger.info("Built %s with %s rows", ENTITY_MASTER_TABLE, f"{row_count:,}")
    return row_count


def entity_values_union_sql() -> str:
    selects = []
    for entity_type in ENTITY_COLUMNS:
        selects.append(
            f"""
            SELECT
                demand_id AS keyword_id,
                normalized_keyword,
                raw_keyword,
                {sql_literal(entity_type)} AS entity_type,
                trim(CAST({entity_type} AS VARCHAR)) AS entity_value,
                month,
                search_frequency_rank
            FROM {DEMAND_OBJECTS_TABLE}
            WHERE {entity_type} IS NOT NULL
              AND trim(CAST({entity_type} AS VARCHAR)) <> ''
            """
        )
    return "\nUNION ALL\n".join(selects)


def build_keyword_entity_edges(connection: duckdb.DuckDBPyConnection) -> int:
    logger.info("Building %s", KEYWORD_ENTITY_EDGES_TABLE)
    connection.execute(
        f"""
        CREATE TABLE {KEYWORD_ENTITY_EDGES_TABLE} AS
        WITH entity_values AS (
            {entity_values_union_sql()}
        )
        SELECT
            entity_values.keyword_id,
            entity_values.normalized_keyword,
            entity_values.raw_keyword,
            entity_master.entity_id,
            entity_values.entity_type,
            entity_values.entity_value,
            entity_values.month,
            entity_values.search_frequency_rank
        FROM entity_values
        JOIN {ENTITY_MASTER_TABLE} AS entity_master
          ON entity_values.entity_type = entity_master.entity_type
         AND entity_values.entity_value = entity_master.canonical
        """
    )
    row_count = connection.execute(f"SELECT count(*) FROM {KEYWORD_ENTITY_EDGES_TABLE}").fetchone()[0]
    logger.info("Built %s with %s rows", KEYWORD_ENTITY_EDGES_TABLE, f"{row_count:,}")
    return int(row_count)


def build_entity_cooccurrence(connection: duckdb.DuckDBPyConnection) -> int:
    logger.info("Building %s", ENTITY_COOCCURRENCE_TABLE)
    connection.execute(
        f"""
        CREATE TABLE {ENTITY_COOCCURRENCE_TABLE} AS
        WITH pairs AS (
            SELECT
                left_edge.entity_type AS entity_a_type,
                left_edge.entity_value AS entity_a_value,
                right_edge.entity_type AS entity_b_type,
                right_edge.entity_value AS entity_b_value,
                left_edge.keyword_id,
                left_edge.normalized_keyword,
                left_edge.search_frequency_rank
            FROM {KEYWORD_ENTITY_EDGES_TABLE} AS left_edge
            JOIN {KEYWORD_ENTITY_EDGES_TABLE} AS right_edge
              ON left_edge.keyword_id = right_edge.keyword_id
             AND (
                    left_edge.entity_type < right_edge.entity_type
                 OR (
                        left_edge.entity_type = right_edge.entity_type
                    AND left_edge.entity_value < right_edge.entity_value
                 )
             )
        ),
        metrics AS (
            SELECT
                entity_a_type,
                entity_a_value,
                entity_b_type,
                entity_b_value,
                count(*) AS keyword_count,
                min(search_frequency_rank) AS best_rank,
                sum(CASE WHEN search_frequency_rank <= 1000 THEN 1 ELSE 0 END) AS top_1000_count
            FROM pairs
            GROUP BY
                entity_a_type,
                entity_a_value,
                entity_b_type,
                entity_b_value
        ),
        distinct_examples AS (
            SELECT
                entity_a_type,
                entity_a_value,
                entity_b_type,
                entity_b_value,
                normalized_keyword,
                min(search_frequency_rank) AS example_rank
            FROM pairs
            GROUP BY
                entity_a_type,
                entity_a_value,
                entity_b_type,
                entity_b_value,
                normalized_keyword
        ),
        ranked_examples AS (
            SELECT
                *,
                row_number() OVER (
                    PARTITION BY entity_a_type, entity_a_value, entity_b_type, entity_b_value
                    ORDER BY example_rank ASC NULLS LAST, normalized_keyword
                ) AS example_position
            FROM distinct_examples
        ),
        examples AS (
            SELECT
                entity_a_type,
                entity_a_value,
                entity_b_type,
                entity_b_value,
                string_agg(
                    normalized_keyword,
                    ' | '
                    ORDER BY example_position
                ) AS example_keywords
            FROM ranked_examples
            WHERE example_position <= 5
            GROUP BY
                entity_a_type,
                entity_a_value,
                entity_b_type,
                entity_b_value
        )
        SELECT
            metrics.entity_a_type,
            metrics.entity_a_value,
            metrics.entity_b_type,
            metrics.entity_b_value,
            metrics.keyword_count,
            metrics.best_rank,
            metrics.top_1000_count,
            examples.example_keywords
        FROM metrics
        LEFT JOIN examples
          ON metrics.entity_a_type = examples.entity_a_type
         AND metrics.entity_a_value = examples.entity_a_value
         AND metrics.entity_b_type = examples.entity_b_type
         AND metrics.entity_b_value = examples.entity_b_value
        ORDER BY
            metrics.best_rank ASC NULLS LAST,
            metrics.top_1000_count DESC,
            metrics.keyword_count DESC,
            metrics.entity_a_type,
            metrics.entity_a_value,
            metrics.entity_b_type,
            metrics.entity_b_value
        """
    )
    row_count = connection.execute(f"SELECT count(*) FROM {ENTITY_COOCCURRENCE_TABLE}").fetchone()[0]
    logger.info("Built %s with %s rows", ENTITY_COOCCURRENCE_TABLE, f"{row_count:,}")
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
    logger.info("Exporting knowledge graph CSVs to %s", display_path(output_dir))
    output_dir.mkdir(parents=True, exist_ok=True)

    exports = {
        "entity_master.csv": f"""
            SELECT *
            FROM {ENTITY_MASTER_TABLE}
            ORDER BY entity_type, canonical
        """,
        "keyword_entity_edges.csv": f"""
            SELECT *
            FROM {KEYWORD_ENTITY_EDGES_TABLE}
            ORDER BY keyword_id, entity_type, entity_value
        """,
        "entity_cooccurrence.csv": f"""
            SELECT *
            FROM {ENTITY_COOCCURRENCE_TABLE}
            ORDER BY
                best_rank ASC NULLS LAST,
                top_1000_count DESC,
                keyword_count DESC,
                entity_a_type,
                entity_a_value,
                entity_b_type,
                entity_b_value
        """,
        "top_entity_pairs.csv": f"""
            SELECT *
            FROM {ENTITY_COOCCURRENCE_TABLE}
            ORDER BY
                best_rank ASC NULLS LAST,
                top_1000_count DESC,
                keyword_count DESC,
                entity_a_type,
                entity_a_value,
                entity_b_type,
                entity_b_value
            LIMIT 1000
        """,
    }

    for file_name, query in exports.items():
        row_count = export_query_to_csv(connection, query, output_dir / file_name)
        logger.info("Exported %s with %s rows", file_name, f"{row_count:,}")


def log_summary(connection: duckdb.DuckDBPyConnection) -> None:
    logger.info("Knowledge graph summary")
    for table_name in [
        ENTITY_MASTER_TABLE,
        KEYWORD_ENTITY_EDGES_TABLE,
        ENTITY_COOCCURRENCE_TABLE,
    ]:
        row_count = connection.execute(f"SELECT count(*) FROM {table_name}").fetchone()[0]
        logger.info("  %s: %s rows", table_name, f"{row_count:,}")

    logger.info("Top entity pairs by rank:")
    rows = connection.execute(
        f"""
        SELECT
            entity_a_type,
            entity_a_value,
            entity_b_type,
            entity_b_value,
            keyword_count,
            best_rank,
            top_1000_count
        FROM {ENTITY_COOCCURRENCE_TABLE}
        ORDER BY best_rank ASC NULLS LAST, top_1000_count DESC, keyword_count DESC
        LIMIT 10
        """
    ).fetchall()
    for row in rows:
        logger.info(
            "  %s=%s + %s=%s | keywords=%s | best=%s | top_1000=%s",
            row[0],
            row[1],
            row[2],
            row[3],
            row[4],
            row[5],
            row[6],
        )


def build_knowledge_graph(
    database_path: Path,
    master_dir: Path,
    output_dir: Path,
    rebuild: bool,
) -> None:
    if not database_path.exists():
        raise FileNotFoundError(f"DuckDB database not found: {database_path}")

    with duckdb.connect(str(database_path)) as connection:
        validate_inputs(connection, master_dir)
        log_input_counts(connection)
        ensure_rebuild_allowed(connection, rebuild)
        if rebuild:
            drop_output_tables(connection)

        build_entity_master(connection, master_dir)
        build_keyword_entity_edges(connection)
        build_entity_cooccurrence(connection)
        export_reports(connection, output_dir)
        log_summary(connection)


def main() -> None:
    configure_logging()
    args = parse_args()
    logger.info("Starting Knowledge Graph build")
    build_knowledge_graph(
        database_path=args.database.resolve(),
        master_dir=args.master_dir.resolve(),
        output_dir=args.output_dir.resolve(),
        rebuild=args.rebuild,
    )
    logger.info("Knowledge Graph build complete")
    logger.info("Build log: %s", display_path(LOG_PATH))


if __name__ == "__main__":
    main()
