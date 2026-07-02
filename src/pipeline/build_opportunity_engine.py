"""Build Opportunity Engine V1 tables from composite demand outputs."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import duckdb
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DUCKDB_PATH = PROJECT_ROOT / "data" / "output" / "aba.duckdb"
OUTPUT_DIR = PROJECT_ROOT / "data" / "output" / "opportunity"
LOG_DIR = PROJECT_ROOT / "logs"
LOG_PATH = LOG_DIR / "build_opportunity_engine.log"

COMPOSITE_DEMANDS_TABLE = "composite_demands"
COMPOSITE_KEYWORDS_TABLE = "composite_keywords"
DEMAND_STRENGTH_V3_TABLE = "demand_strength_v3"
DEMAND_PROFILE_V2_TABLE = "demand_profile_v2"
MARKET_NODES_TABLE = "market_nodes"
INTENT_SUMMARY_TABLE = "intent_summary"

OPPORTUNITY_MASTER_TABLE = "opportunity_master"
RESEARCH_BACKLOG_TABLE = "research_backlog"

INPUT_TABLES = [
    COMPOSITE_DEMANDS_TABLE,
    COMPOSITE_KEYWORDS_TABLE,
    DEMAND_STRENGTH_V3_TABLE,
    DEMAND_PROFILE_V2_TABLE,
    MARKET_NODES_TABLE,
    INTENT_SUMMARY_TABLE,
]
OUTPUT_TABLES = [
    RESEARCH_BACKLOG_TABLE,
    OPPORTUNITY_MASTER_TABLE,
]

REQUIRED_COLUMNS = {
    COMPOSITE_DEMANDS_TABLE: {
        "demand_id",
        "demand_name",
        "intent",
        "recipient",
        "profession",
        "interest",
        "occasion",
        "holiday",
        "keyword_count",
        "best_rank",
        "p25_rank",
        "median_rank",
        "active_months",
        "trend",
    },
    COMPOSITE_KEYWORDS_TABLE: {
        "demand_id",
        "raw_keyword",
        "normalized_keyword",
        "month",
        "search_frequency_rank",
    },
    DEMAND_STRENGTH_V3_TABLE: {
        "demand_id",
        "demand_name",
        "intent",
        "recipient",
        "profession",
        "interest",
        "occasion",
        "holiday",
        "keyword_count",
        "best_rank",
        "p25_rank",
        "median_rank",
        "active_months",
        "trend",
        "strength_score",
    },
    DEMAND_PROFILE_V2_TABLE: {"demand_id", "dimension", "value", "best_rank"},
    MARKET_NODES_TABLE: {"demand", "pet", "best_rank", "strength_score"},
    INTENT_SUMMARY_TABLE: {"intent", "best_rank", "keyword_count"},
}

OPPORTUNITY_COLUMNS = [
    "opportunity_id",
    "demand_id",
    "demand_name",
    "intent",
    "recipient",
    "profession",
    "interest",
    "pet",
    "occasion",
    "holiday",
    "best_rank",
    "p25_rank",
    "median_rank",
    "keyword_count",
    "active_months",
    "trend",
    "demand_strength_score",
    "rank_quality_score",
    "trend_score",
    "active_month_score",
    "evidence_score",
    "competition_score",
    "product_gap_score",
    "internal_gap_score",
    "opportunity_score",
    "priority",
    "evidence_keywords",
    "recommendation_note",
]

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build Opportunity Engine V1 tables from composite demand outputs."
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Drop existing Opportunity V1 tables before rebuilding.",
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
        help="Folder for Opportunity Engine CSV reports.",
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
            f"{', '.join(missing_tables)}. Run the composite demand layer first."
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
            "Opportunity Engine tables already exist. Rerun with --rebuild to replace only "
            f"these tables: {', '.join(existing_tables)}"
        )


def drop_output_tables(connection: duckdb.DuckDBPyConnection) -> None:
    for table_name in OUTPUT_TABLES:
        logger.info("Dropping %s if it exists", table_name)
        connection.execute(f"DROP TABLE IF EXISTS {table_name}")


def build_keyword_stats_stage(connection: duckdb.DuckDBPyConnection) -> None:
    logger.info("Building opportunity keyword statistics stage")
    connection.execute("DROP TABLE IF EXISTS opportunity_keyword_stats_stage")
    connection.execute(
        f"""
        CREATE TEMP TABLE opportunity_keyword_stats_stage AS
        SELECT
            demand_id,
            count(*) AS evidence_row_count,
            sum(CASE WHEN search_frequency_rank <= 100 THEN 1 ELSE 0 END) AS top100_count,
            sum(CASE WHEN search_frequency_rank <= 500 THEN 1 ELSE 0 END) AS top500_count,
            sum(CASE WHEN search_frequency_rank <= 1000 THEN 1 ELSE 0 END) AS top1000_count,
            sum(CASE WHEN search_frequency_rank <= 5000 THEN 1 ELSE 0 END) AS top5000_count
        FROM {COMPOSITE_KEYWORDS_TABLE}
        GROUP BY demand_id
        """
    )


def build_keyword_examples_stage(connection: duckdb.DuckDBPyConnection) -> None:
    logger.info("Building opportunity keyword examples stage")
    connection.execute("DROP TABLE IF EXISTS opportunity_keyword_examples_stage")
    connection.execute(
        f"""
        CREATE TEMP TABLE opportunity_keyword_examples_stage AS
        WITH ranked_keywords AS (
            SELECT
                demand_id,
                normalized_keyword,
                row_number() OVER (
                    PARTITION BY demand_id
                    ORDER BY search_frequency_rank ASC NULLS LAST, normalized_keyword
                ) AS keyword_rank
            FROM {COMPOSITE_KEYWORDS_TABLE}
        )
        SELECT
            demand_id,
            string_agg(normalized_keyword, ' | ' ORDER BY keyword_rank) AS evidence_keywords
        FROM ranked_keywords
        WHERE keyword_rank <= 8
        GROUP BY demand_id
        """
    )


def build_market_pet_stage(connection: duckdb.DuckDBPyConnection) -> None:
    logger.info("Building market node pet enrichment stage")
    connection.execute("DROP TABLE IF EXISTS opportunity_market_pet_stage")
    connection.execute(
        f"""
        CREATE TEMP TABLE opportunity_market_pet_stage AS
        SELECT
            demand AS demand_name,
            min(pet) FILTER (WHERE pet IS NOT NULL AND trim(CAST(pet AS VARCHAR)) <> '') AS pet
        FROM {MARKET_NODES_TABLE}
        GROUP BY demand
        """
    )


def build_opportunity_master(connection: duckdb.DuckDBPyConnection) -> int:
    logger.info("Building %s", OPPORTUNITY_MASTER_TABLE)
    connection.execute(
        f"""
        CREATE TABLE {OPPORTUNITY_MASTER_TABLE} AS
        WITH max_rank AS (
            SELECT greatest(coalesce(max(search_frequency_rank), 1), 2) AS value
            FROM {COMPOSITE_KEYWORDS_TABLE}
        ),
        base AS (
            SELECT
                strength.demand_id,
                strength.demand_name,
                strength.intent,
                nullif(trim(CAST(strength.recipient AS VARCHAR)), '') AS recipient,
                nullif(trim(CAST(strength.profession AS VARCHAR)), '') AS profession,
                nullif(trim(CAST(strength.interest AS VARCHAR)), '') AS interest,
                CASE
                    WHEN lower(nullif(trim(CAST(strength.recipient AS VARCHAR)), '')) IN
                        ('dog', 'cat', 'horse', 'bird', 'fish')
                        THEN lower(nullif(trim(CAST(strength.recipient AS VARCHAR)), ''))
                    ELSE market_pet.pet
                END AS pet,
                nullif(trim(CAST(strength.occasion AS VARCHAR)), '') AS occasion,
                nullif(trim(CAST(strength.holiday AS VARCHAR)), '') AS holiday,
                strength.best_rank,
                strength.p25_rank,
                strength.median_rank,
                coalesce(keyword_stats.evidence_row_count, strength.keyword_count, 0) AS keyword_count,
                coalesce(strength.active_months, 0) AS active_months,
                coalesce(nullif(trim(CAST(strength.trend AS VARCHAR)), ''), 'unknown') AS trend,
                coalesce(strength.strength_score, 0.0) AS source_strength_score,
                coalesce(keyword_stats.top100_count, 0) AS top100_count,
                coalesce(keyword_stats.top500_count, 0) AS top500_count,
                coalesce(keyword_stats.top1000_count, 0) AS top1000_count,
                coalesce(keyword_stats.top5000_count, 0) AS top5000_count,
                coalesce(keyword_examples.evidence_keywords, '') AS evidence_keywords,
                max_rank.value AS max_rank_value
            FROM {DEMAND_STRENGTH_V3_TABLE} AS strength
            LEFT JOIN opportunity_keyword_stats_stage AS keyword_stats
              ON strength.demand_id = keyword_stats.demand_id
            LEFT JOIN opportunity_keyword_examples_stage AS keyword_examples
              ON strength.demand_id = keyword_examples.demand_id
            LEFT JOIN opportunity_market_pet_stage AS market_pet
              ON strength.demand_name = market_pet.demand_name
            CROSS JOIN max_rank
        ),
        raw_scored AS (
            SELECT
                *,
                (
                    0.50 * CASE
                        WHEN best_rank IS NULL THEN 0.0
                        ELSE least(
                            100.0,
                            greatest(
                                0.0,
                                100.0
                                * (
                                    1.0
                                    - (
                                        ln(greatest(CAST(best_rank AS DOUBLE), 1.0))
                                        / ln(CAST(max_rank_value AS DOUBLE))
                                    )
                                )
                            )
                        )
                    END
                    + 0.30 * CASE
                        WHEN p25_rank IS NULL THEN 0.0
                        ELSE least(
                            100.0,
                            greatest(
                                0.0,
                                100.0
                                * (
                                    1.0
                                    - (
                                        ln(greatest(CAST(p25_rank AS DOUBLE), 1.0))
                                        / ln(CAST(max_rank_value AS DOUBLE))
                                    )
                                )
                            )
                        )
                    END
                    + 0.20 * CASE
                        WHEN median_rank IS NULL THEN 0.0
                        ELSE least(
                            100.0,
                            greatest(
                                0.0,
                                100.0
                                * (
                                    1.0
                                    - (
                                        ln(greatest(CAST(median_rank AS DOUBLE), 1.0))
                                        / ln(CAST(max_rank_value AS DOUBLE))
                                    )
                                )
                            )
                        )
                    END
                ) AS raw_rank_quality_score,
                CAST(
                    CASE
                        WHEN trend = 'growing' THEN 100.0
                        WHEN trend = 'emerging' THEN 85.0
                        WHEN trend = 'stable' THEN 70.0
                        WHEN trend = 'declining' THEN 30.0
                        ELSE 50.0
                    END AS DOUBLE
                ) AS raw_trend_score,
                (
                    top100_count * 25.0
                    + greatest(top500_count - top100_count, 0) * 15.0
                    + greatest(top1000_count - top500_count, 0) * 10.0
                    + greatest(top5000_count - top1000_count, 0) * 4.0
                    + least(20.0, ln(greatest(CAST(keyword_count AS DOUBLE), 0.0) + 1.0) * 3.0)
                ) AS raw_evidence_score
            FROM base
        ),
        max_values AS (
            SELECT
                greatest(coalesce(max(source_strength_score), 0.0), 1.0) AS max_source_strength_score,
                greatest(coalesce(max(raw_rank_quality_score), 0.0), 1.0) AS max_rank_quality_score,
                greatest(coalesce(max(raw_evidence_score), 0.0), 1.0) AS max_evidence_score,
                greatest(coalesce(max(active_months), 0), 1) AS max_active_months
            FROM raw_scored
        ),
        component_scored AS (
            SELECT
                raw_scored.demand_id,
                raw_scored.demand_name,
                raw_scored.intent,
                raw_scored.recipient,
                raw_scored.profession,
                raw_scored.interest,
                raw_scored.pet,
                raw_scored.occasion,
                raw_scored.holiday,
                raw_scored.best_rank,
                raw_scored.p25_rank,
                raw_scored.median_rank,
                raw_scored.keyword_count,
                raw_scored.active_months,
                raw_scored.trend,
                round(
                    least(
                        100.0,
                        greatest(
                            0.0,
                            100.0
                            * raw_scored.source_strength_score
                            / max_values.max_source_strength_score
                        )
                    ),
                    2
                ) AS demand_strength_score,
                round(
                    least(
                        100.0,
                        greatest(
                            0.0,
                            100.0
                            * raw_scored.raw_rank_quality_score
                            / max_values.max_rank_quality_score
                        )
                    ),
                    2
                ) AS rank_quality_score,
                raw_scored.raw_trend_score AS trend_score,
                round(
                    least(
                        100.0,
                        greatest(
                            0.0,
                            100.0
                            * CAST(raw_scored.active_months AS DOUBLE)
                            / CAST(max_values.max_active_months AS DOUBLE)
                        )
                    ),
                    2
                ) AS active_month_score,
                round(
                    least(
                        100.0,
                        greatest(
                            0.0,
                            100.0
                            * raw_scored.raw_evidence_score
                            / max_values.max_evidence_score
                        )
                    ),
                    2
                ) AS evidence_score,
                raw_scored.evidence_keywords
            FROM raw_scored
            CROSS JOIN max_values
        ),
        opportunity_scored AS (
            SELECT
                *,
                CAST(0.0 AS DOUBLE) AS competition_score,
                CAST(0.0 AS DOUBLE) AS product_gap_score,
                CAST(0.0 AS DOUBLE) AS internal_gap_score,
                round(
                    (demand_strength_score * 0.40)
                    + (rank_quality_score * 0.20)
                    + (trend_score * 0.15)
                    + (active_month_score * 0.15)
                    + (evidence_score * 0.10),
                    2
                ) AS opportunity_score
            FROM component_scored
        ),
        opportunity_labeled AS (
            SELECT
                *,
                CASE
                    WHEN opportunity_score >= 85.0 THEN 'P1'
                    WHEN opportunity_score >= 70.0 THEN 'P2'
                    WHEN opportunity_score >= 55.0 THEN 'P3'
                    ELSE 'Watchlist'
                END AS priority,
                CASE
                    WHEN holiday IS NOT NULL
                      OR lower(coalesce(occasion, '')) IN (
                            'christmas',
                            'halloween',
                            'thanksgiving',
                            'easter',
                            'valentine',
                            'valentine''s day',
                            'mother''s day',
                            'father''s day',
                            'birthday',
                            'graduation',
                            'wedding',
                            'anniversary',
                            'retirement',
                            'housewarming'
                        )
                      OR lower(coalesce(intent, '')) IN (
                            'christmas',
                            'birthday',
                            'graduation',
                            'wedding',
                            'anniversary',
                            'retirement',
                            'housewarming'
                        )
                        THEN 'Seasonal opportunity; validate timing before research.'
                    WHEN trend IN ('growing', 'emerging') AND rank_quality_score >= 60.0
                        THEN 'Growing demand with strong best-rank signal.'
                    WHEN demand_strength_score >= 70.0 AND active_month_score >= 75.0
                        THEN 'High demand strength and consistent ranking across months.'
                    WHEN trend = 'declining'
                        THEN 'Demand has rank signal but is declining; validate before prioritizing.'
                    ELSE 'Qualified demand signal; review niche, product gap, and catalog fit.'
                END AS recommendation_note
            FROM opportunity_scored
        )
        SELECT
            'OP' || lpad(
                CAST(
                    row_number() OVER (
                        ORDER BY
                            opportunity_score DESC,
                            best_rank ASC NULLS LAST,
                            demand_id
                    ) AS VARCHAR
                ),
                6,
                '0'
            ) AS opportunity_id,
            demand_id,
            demand_name,
            intent,
            recipient,
            profession,
            interest,
            pet,
            occasion,
            holiday,
            best_rank,
            p25_rank,
            median_rank,
            keyword_count,
            active_months,
            trend,
            demand_strength_score,
            rank_quality_score,
            trend_score,
            active_month_score,
            evidence_score,
            competition_score,
            product_gap_score,
            internal_gap_score,
            opportunity_score,
            priority,
            evidence_keywords,
            recommendation_note
        FROM opportunity_labeled
        ORDER BY
            opportunity_score DESC,
            best_rank ASC NULLS LAST,
            demand_id
        """
    )
    row_count = connection.execute(f"SELECT count(*) FROM {OPPORTUNITY_MASTER_TABLE}").fetchone()[0]
    logger.info("Built %s with %s rows", OPPORTUNITY_MASTER_TABLE, f"{row_count:,}")
    return int(row_count)


def build_research_backlog(connection: duckdb.DuckDBPyConnection) -> int:
    logger.info("Building %s", RESEARCH_BACKLOG_TABLE)
    connection.execute(
        f"""
        CREATE TABLE {RESEARCH_BACKLOG_TABLE} AS
        SELECT
            opportunity_id,
            demand_id,
            demand_name,
            priority,
            opportunity_score,
            trend,
            intent,
            recipient,
            profession,
            pet,
            interest,
            occasion,
            holiday,
            best_rank,
            p25_rank,
            median_rank,
            keyword_count,
            active_months,
            evidence_keywords,
            recommendation_note,
            CASE
                WHEN priority = 'P1' THEN 'Research immediately'
                WHEN priority = 'P2' THEN 'Queue for near-term validation'
                WHEN priority = 'P3' THEN 'Review after P1/P2 opportunities'
                ELSE 'Monitor until stronger rank signal appears'
            END AS next_action,
            'new' AS research_status
        FROM {OPPORTUNITY_MASTER_TABLE}
        WHERE priority IN ('P1', 'P2', 'P3')
           OR trend IN ('growing', 'emerging')
           OR holiday IS NOT NULL
        ORDER BY
            CASE priority
                WHEN 'P1' THEN 1
                WHEN 'P2' THEN 2
                WHEN 'P3' THEN 3
                ELSE 4
            END,
            opportunity_score DESC,
            best_rank ASC NULLS LAST,
            demand_id
        """
    )
    row_count = connection.execute(f"SELECT count(*) FROM {RESEARCH_BACKLOG_TABLE}").fetchone()[0]
    logger.info("Built %s with %s rows", RESEARCH_BACKLOG_TABLE, f"{row_count:,}")
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
    logger.info("Exporting Opportunity Engine CSVs to %s", display_path(output_dir))
    output_dir.mkdir(parents=True, exist_ok=True)

    seasonal_filter = """
        holiday IS NOT NULL
        OR lower(coalesce(occasion, '')) IN (
            'christmas',
            'halloween',
            'thanksgiving',
            'easter',
            'valentine',
            'valentine''s day',
            'mother''s day',
            'father''s day',
            'birthday',
            'graduation',
            'wedding',
            'anniversary',
            'retirement',
            'housewarming'
        )
        OR lower(coalesce(intent, '')) IN (
            'christmas',
            'birthday',
            'graduation',
            'wedding',
            'anniversary',
            'retirement',
            'housewarming'
        )
    """

    exports = {
        "opportunity_master.csv": f"""
            SELECT {', '.join(OPPORTUNITY_COLUMNS)}
            FROM {OPPORTUNITY_MASTER_TABLE}
            ORDER BY opportunity_score DESC, best_rank ASC NULLS LAST, demand_id
        """,
        "research_backlog.csv": f"""
            SELECT *
            FROM {RESEARCH_BACKLOG_TABLE}
            ORDER BY
                CASE priority
                    WHEN 'P1' THEN 1
                    WHEN 'P2' THEN 2
                    WHEN 'P3' THEN 3
                    ELSE 4
                END,
                opportunity_score DESC,
                best_rank ASC NULLS LAST,
                demand_id
        """,
        "top_100_opportunities.csv": f"""
            SELECT {', '.join(OPPORTUNITY_COLUMNS)}
            FROM {OPPORTUNITY_MASTER_TABLE}
            ORDER BY opportunity_score DESC, best_rank ASC NULLS LAST, demand_id
            LIMIT 100
        """,
        "top_growing_opportunities.csv": f"""
            SELECT {', '.join(OPPORTUNITY_COLUMNS)}
            FROM {OPPORTUNITY_MASTER_TABLE}
            WHERE trend IN ('growing', 'emerging')
            ORDER BY opportunity_score DESC, best_rank ASC NULLS LAST, demand_id
        """,
        "top_seasonal_opportunities.csv": f"""
            SELECT {', '.join(OPPORTUNITY_COLUMNS)}
            FROM {OPPORTUNITY_MASTER_TABLE}
            WHERE {seasonal_filter}
            ORDER BY opportunity_score DESC, best_rank ASC NULLS LAST, demand_id
        """,
    }

    for file_name, query in exports.items():
        row_count = export_query_to_csv(connection, query, output_dir / file_name)
        logger.info("Exported %s with %s rows", file_name, f"{row_count:,}")


def log_summary(connection: duckdb.DuckDBPyConnection) -> None:
    logger.info("Opportunity Engine summary")
    for table_name in [OPPORTUNITY_MASTER_TABLE, RESEARCH_BACKLOG_TABLE]:
        row_count = connection.execute(f"SELECT count(*) FROM {table_name}").fetchone()[0]
        logger.info("  %s: %s rows", table_name, f"{row_count:,}")

    logger.info("Priority distribution:")
    for priority, count in connection.execute(
        f"""
        SELECT priority, count(*)
        FROM {OPPORTUNITY_MASTER_TABLE}
        GROUP BY priority
        ORDER BY
            CASE priority
                WHEN 'P1' THEN 1
                WHEN 'P2' THEN 2
                WHEN 'P3' THEN 3
                ELSE 4
            END
        """
    ).fetchall():
        logger.info("  %s: %s", priority, f"{count:,}")

    logger.info("Top opportunities:")
    for row in connection.execute(
        f"""
        SELECT
            opportunity_id,
            demand_name,
            opportunity_score,
            priority,
            best_rank,
            p25_rank,
            trend
        FROM {OPPORTUNITY_MASTER_TABLE}
        ORDER BY opportunity_score DESC, best_rank ASC NULLS LAST
        LIMIT 10
        """
    ).fetchall():
        logger.info(
            "  %s | %s | score=%s | %s | best=%s | p25=%s | %s",
            row[0],
            row[1],
            row[2],
            row[3],
            row[4],
            round(float(row[5]), 2) if row[5] is not None else None,
            row[6],
        )


def build_opportunity_engine(database_path: Path, output_dir: Path, rebuild: bool) -> None:
    if not database_path.exists():
        raise FileNotFoundError(f"DuckDB database not found: {database_path}")

    with duckdb.connect(str(database_path)) as connection:
        validate_inputs(connection)
        log_input_counts(connection)
        ensure_rebuild_allowed(connection, rebuild)
        if rebuild:
            drop_output_tables(connection)

        build_keyword_stats_stage(connection)
        build_keyword_examples_stage(connection)
        build_market_pet_stage(connection)
        build_opportunity_master(connection)
        build_research_backlog(connection)
        export_reports(connection, output_dir)
        log_summary(connection)


def main() -> None:
    configure_logging()
    args = parse_args()
    logger.info("Starting Opportunity Engine build")
    build_opportunity_engine(
        database_path=args.database.resolve(),
        output_dir=args.output_dir.resolve(),
        rebuild=args.rebuild,
    )
    logger.info("Opportunity Engine build complete")
    logger.info("Build log: %s", display_path(LOG_PATH))


if __name__ == "__main__":
    main()
