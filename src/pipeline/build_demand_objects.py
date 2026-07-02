"""Build structured demand objects from normalized keyword research data."""

from __future__ import annotations

import argparse
import csv
import logging
import re
from dataclasses import dataclass
from pathlib import Path

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DUCKDB_PATH = PROJECT_ROOT / "data" / "output" / "aba.duckdb"
KNOWLEDGE_MASTER_DIR = PROJECT_ROOT / "knowledge" / "master"
KNOWLEDGE_REVIEW_DIR = PROJECT_ROOT / "knowledge" / "review"
LOG_DIR = PROJECT_ROOT / "logs"
LOG_PATH = LOG_DIR / "build_demand_objects.log"

SOURCE_TABLE = "normalized_keywords"
DEMAND_OBJECTS_TABLE = "demand_objects"
KNOWLEDGE_ALIASES_TABLE = "knowledge_aliases"

ENTITY_TYPES = [
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
UNKNOWN_COLUMNS = [
    "candidate",
    "entity_type",
    "raw_keyword_example",
    "keyword_count",
    "first_month",
    "last_month",
    "best_rank",
    "status",
    "notes",
]

NON_ALNUM_PATTERN = re.compile(r"[^a-z0-9']+")
UNDERSCORE_PATTERN = re.compile(r"_+")

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class KnowledgeAlias:
    entity_type: str
    canonical: str
    alias: str
    priority: int
    alias_length: int
    pattern: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build structured demand objects from normalized keyword data."
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Drop demand_objects before rebuilding it.",
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


def normalize_token(value: str) -> str:
    normalized = value.strip().lower()
    normalized = NON_ALNUM_PATTERN.sub(" ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def normalize_entity_type(value: str) -> str:
    normalized = value.strip().lower()
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized)
    normalized = UNDERSCORE_PATTERN.sub("_", normalized).strip("_")
    return normalized


def parse_active(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y", "active"}


def parse_priority(value: str) -> int:
    try:
        return int(value)
    except ValueError:
        return 0


def alias_pattern(alias: str) -> str:
    tokens = alias.split()
    phrase = r"\s+".join(re.escape(token) for token in tokens)
    return rf"(^|[^a-z0-9']){phrase}($|[^a-z0-9'])"


def alias_values(canonical: str, aliases: str) -> list[str]:
    values = [canonical]
    values.extend(part for part in aliases.split("|") if part.strip())

    normalized_values = []
    seen = set()
    for value in values:
        normalized = normalize_token(value)
        if normalized and normalized not in seen:
            normalized_values.append(normalized)
            seen.add(normalized)

    return normalized_values


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def semantic_knowledge_aliases() -> list[KnowledgeAlias]:
    semantic_rules = [
        ("recipient", "girl", "girl", 130, 4, r"(^|[^a-z0-9])((teenage|teen|little|baby|toddler)\s+)?girls?($|[^a-z0-9])"),
        ("recipient", "boy", "boy", 130, 3, r"(^|[^a-z0-9])((teenage|teen|little|baby|toddler)\s+)?boys?($|[^a-z0-9])"),
        ("recipient", "dog mom", "dog mom", 135, 7, r"(^|[^a-z0-9])dog\s+(mom|mama|mother)($|[^a-z0-9])"),
        ("recipient", "cat mom", "cat mom", 135, 7, r"(^|[^a-z0-9])cat\s+(mom|mama|mother)($|[^a-z0-9])"),
        ("pet", "dog", "dog", 130, 3, r"(^|[^a-z0-9])dogs?($|[^a-z0-9])"),
        ("pet", "dog", "dog parent", 130, 10, r"(^|[^a-z0-9])dog\s+(mom|mama|mother|dad|father|lover|person|parent)($|[^a-z0-9])"),
        ("pet", "cat", "cat", 130, 3, r"(^|[^a-z0-9])cats?($|[^a-z0-9])"),
        ("pet", "cat", "cat parent", 130, 10, r"(^|[^a-z0-9])cat\s+(mom|mama|mother|dad|father|lover|person|parent)($|[^a-z0-9])"),
    ]
    return [
        KnowledgeAlias(
            entity_type=entity_type,
            canonical=canonical,
            alias=alias,
            priority=priority,
            alias_length=alias_length,
            pattern=pattern,
        )
        for entity_type, canonical, alias, priority, alias_length, pattern in semantic_rules
    ]


def load_knowledge_base() -> list[KnowledgeAlias]:
    if not KNOWLEDGE_MASTER_DIR.exists():
        raise FileNotFoundError(f"Knowledge master directory not found: {KNOWLEDGE_MASTER_DIR}")

    csv_paths = sorted(KNOWLEDGE_MASTER_DIR.glob("*.csv"))
    logger.info("Loading %s knowledge file(s) from %s", len(csv_paths), KNOWLEDGE_MASTER_DIR)

    rules_by_key: dict[tuple[str, str, str], KnowledgeAlias] = {}

    for csv_path in csv_paths:
        logger.info("Loading knowledge file %s", csv_path.name)
        with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                logger.warning("Skipping empty knowledge file: %s", csv_path.name)
                continue

            missing_columns = [column for column in MASTER_COLUMNS if column not in reader.fieldnames]
            if missing_columns:
                logger.warning(
                    "Skipping %s because it is missing columns: %s",
                    csv_path.name,
                    ", ".join(missing_columns),
                )
                continue

            for row in reader:
                entity_type = normalize_entity_type(row["entity_type"])
                if entity_type not in ENTITY_TYPES:
                    continue
                if not parse_active(row["active"]):
                    continue

                canonical = normalize_token(row["canonical"])
                if not canonical:
                    continue

                priority = parse_priority(row["priority"])
                for alias in alias_values(canonical, row["aliases"]):
                    rule = KnowledgeAlias(
                        entity_type=entity_type,
                        canonical=canonical,
                        alias=alias,
                        priority=priority,
                        alias_length=len(alias),
                        pattern=alias_pattern(alias),
                    )
                    key = (rule.entity_type, rule.canonical, rule.alias)
                    existing = rules_by_key.get(key)
                    if existing is None or rule.priority > existing.priority:
                        rules_by_key[key] = rule

    rules = list(rules_by_key.values())
    rules.extend(semantic_knowledge_aliases())

    rules = sorted(
        rules,
        key=lambda item: (item.entity_type, -item.priority, -item.alias_length, item.canonical),
    )
    logger.info("Loaded %s active knowledge aliases", len(rules))
    return rules


def load_knowledge_aliases(
    connection: duckdb.DuckDBPyConnection,
    rules: list[KnowledgeAlias],
) -> None:
    connection.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE {KNOWLEDGE_ALIASES_TABLE} (
            entity_type VARCHAR,
            canonical VARCHAR,
            alias VARCHAR,
            priority INTEGER,
            alias_length INTEGER,
            pattern VARCHAR
        )
        """
    )

    if not rules:
        logger.warning("No active knowledge aliases loaded")
        return

    connection.executemany(
        f"""
        INSERT INTO {KNOWLEDGE_ALIASES_TABLE}
        (entity_type, canonical, alias, priority, alias_length, pattern)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            (
                rule.entity_type,
                rule.canonical,
                rule.alias,
                rule.priority,
                rule.alias_length,
                rule.pattern,
            )
            for rule in rules
        ],
    )


def ensure_source_table(connection: duckdb.DuckDBPyConnection) -> None:
    if not table_exists(connection, SOURCE_TABLE):
        raise RuntimeError(
            f"Required table not found: {SOURCE_TABLE}. Run build_research_model.py first."
        )


def drop_demand_objects(connection: duckdb.DuckDBPyConnection) -> None:
    logger.info("Dropping %s if it exists", DEMAND_OBJECTS_TABLE)
    connection.execute(f"DROP TABLE IF EXISTS {DEMAND_OBJECTS_TABLE}")


def entity_case_expression(entity_type: str, rules: list[KnowledgeAlias]) -> str:
    ordered_rules = sorted(
        [rule for rule in rules if rule.entity_type == entity_type],
        key=lambda item: (-item.priority, -item.alias_length, item.canonical),
    )

    if not ordered_rules:
        return f"NULL AS {entity_type}"

    when_clauses = "\n                ".join(
        (
            "WHEN regexp_matches(coalesce(normalized_search_term, ''), "
            f"{sql_literal(rule.pattern)}) THEN {sql_literal(rule.canonical)}"
        )
        for rule in ordered_rules
    )
    return f"CASE\n                {when_clauses}\n                ELSE NULL\n            END AS {entity_type}"


def build_demand_objects(
    connection: duckdb.DuckDBPyConnection,
    rules: list[KnowledgeAlias],
) -> int:
    ensure_source_table(connection)
    logger.info("Building %s from %s", DEMAND_OBJECTS_TABLE, SOURCE_TABLE)

    entity_columns = ",\n            ".join(
        entity_case_expression(entity_type, rules)
        for entity_type in ENTITY_TYPES
    )

    connection.execute(
        f"""
        CREATE OR REPLACE TABLE {DEMAND_OBJECTS_TABLE} AS
        SELECT
            row_number() OVER (
                ORDER BY month, search_frequency_rank, raw_search_term, normalized_search_term
            ) AS demand_id,
            raw_search_term AS raw_keyword,
            normalized_search_term AS normalized_keyword,
            {entity_columns},
            month,
            search_frequency_rank,
            reporting_date
        FROM {SOURCE_TABLE}
        """
    )

    row_count = connection.execute(f"SELECT count(*) FROM {DEMAND_OBJECTS_TABLE}").fetchone()[0]
    logger.info("Built %s with %s rows", DEMAND_OBJECTS_TABLE, f"{row_count:,}")
    return int(row_count)


def existing_review_candidates(path: Path) -> set[str]:
    if not path.exists() or path.stat().st_size == 0:
        return set()

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or "candidate" not in reader.fieldnames:
            return set()
        return {row["candidate"] for row in reader if row.get("candidate")}


def open_review_writer(path: Path) -> tuple[object, csv.writer]:
    needs_header = not path.exists() or path.stat().st_size == 0
    handle = path.open("a", encoding="utf-8", newline="")
    writer = csv.writer(handle)
    if needs_header:
        writer.writerow(UNKNOWN_COLUMNS)
    return handle, writer


def append_unknown_entities(connection: duckdb.DuckDBPyConnection) -> None:
    KNOWLEDGE_REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Appending unknown entity review candidates to %s", KNOWLEDGE_REVIEW_DIR)

    for entity_type in ENTITY_TYPES:
        review_path = KNOWLEDGE_REVIEW_DIR / f"unknown_{entity_type}.csv"
        existing_candidates = existing_review_candidates(review_path)
        handle, writer = open_review_writer(review_path)
        appended = 0

        try:
            cursor = connection.execute(
                f"""
                SELECT
                    normalized_keyword AS candidate,
                    min(raw_keyword) AS raw_keyword_example,
                    count(*) AS keyword_count,
                    min(month) AS first_month,
                    max(month) AS last_month,
                    min(search_frequency_rank) AS best_rank
                FROM {DEMAND_OBJECTS_TABLE}
                WHERE {entity_type} IS NULL
                  AND normalized_keyword IS NOT NULL
                GROUP BY normalized_keyword
                ORDER BY best_rank NULLS LAST, keyword_count DESC, normalized_keyword
                """
            )

            while True:
                rows = cursor.fetchmany(5000)
                if not rows:
                    break

                for row in rows:
                    candidate = row[0]
                    if candidate in existing_candidates:
                        continue
                    writer.writerow(
                        [
                            candidate,
                            entity_type,
                            row[1],
                            row[2],
                            row[3],
                            row[4],
                            row[5],
                            "pending",
                            f"No {entity_type} match in demand_objects",
                        ]
                    )
                    existing_candidates.add(candidate)
                    appended += 1
        finally:
            handle.close()

        logger.info("Appended %s unknown %s candidate(s)", f"{appended:,}", entity_type)


def main() -> None:
    configure_logging()
    args = parse_args()

    logger.info("Starting demand object build")
    rules = load_knowledge_base()

    with connect_db() as connection:
        if args.rebuild:
            drop_demand_objects(connection)

        load_knowledge_aliases(connection, rules)
        build_demand_objects(connection, rules)
        append_unknown_entities(connection)

    logger.info("Demand object build complete")
    logger.info("Build log: %s", LOG_PATH.relative_to(PROJECT_ROOT))


if __name__ == "__main__":
    main()
