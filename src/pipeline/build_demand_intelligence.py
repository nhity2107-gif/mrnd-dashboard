"""Build Demand Intelligence V1 CSVs from demand, segment, opportunity, and insight exports."""

from __future__ import annotations

import argparse
import logging
import math
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "data" / "output" / "intelligence"
LOG_DIR = PROJECT_ROOT / "logs"
LOG_PATH = LOG_DIR / "build_demand_intelligence.log"

INPUT_PATHS = {
    "composite_demands": PROJECT_ROOT
    / "data"
    / "output"
    / "composite_demands"
    / "composite_demands.csv",
    "demand_strength_v3": PROJECT_ROOT
    / "data"
    / "output"
    / "composite_demands"
    / "demand_strength_v3.csv",
    "demand_segments": PROJECT_ROOT
    / "data"
    / "output"
    / "demand_segments"
    / "demand_segments.csv",
    "opportunity_master": PROJECT_ROOT
    / "data"
    / "output"
    / "opportunity"
    / "opportunity_master.csv",
    "demand_size_map": PROJECT_ROOT / "data" / "output" / "insights" / "demand_size_map.csv",
    "segment_size_map": PROJECT_ROOT / "data" / "output" / "insights" / "segment_size_map.csv",
    "seasonality_map": PROJECT_ROOT / "data" / "output" / "insights" / "seasonality_map.csv",
    "growth_map": PROJECT_ROOT / "data" / "output" / "insights" / "growth_map.csv",
    "niche_direction_map": PROJECT_ROOT
    / "data"
    / "output"
    / "insights"
    / "niche_direction_map.csv",
    "research_opportunity_queue": PROJECT_ROOT
    / "data"
    / "output"
    / "insights"
    / "research_opportunity_queue.csv",
}

OUTPUT_FILES = {
    "demand_intelligence": "demand_intelligence.csv",
    "expansion_graph": "expansion_graph.csv",
    "research_queue": "research_queue.csv",
    "executive_dashboard": "executive_dashboard.csv",
}

REQUIRED_COLUMNS = {
    "composite_demands": {"demand_id", "demand_name", "best_rank"},
    "demand_strength_v3": {
        "demand_id",
        "demand_name",
        "best_rank",
        "p25_rank",
        "median_rank",
        "keyword_count",
        "active_months",
        "trend",
        "strength_score",
    },
    "demand_segments": {
        "segment_id",
        "parent_demand_id",
        "parent_demand",
        "segment_name",
        "keyword_count",
        "best_rank",
        "active_months",
        "trend",
        "segment_strength",
    },
    "opportunity_master": {
        "opportunity_id",
        "demand_id",
        "demand_name",
        "keyword_count",
        "active_months",
        "trend",
        "opportunity_score",
        "priority",
        "evidence_score",
    },
    "demand_size_map": {"demand_id", "demand_name", "size_tier", "strength_score"},
    "segment_size_map": {"segment_id", "parent_demand", "segment_name", "size_tier"},
    "seasonality_map": {"entity_type", "entity_id", "entity_name", "seasonality_type"},
    "growth_map": {"entity_type", "entity_id", "entity_name", "growth_signal", "rank_momentum"},
    "niche_direction_map": {"parent_demand", "segment_name", "direction_type"},
    "research_opportunity_queue": {"priority_rank", "parent_demand", "recommended_action"},
}

DEMAND_INTELLIGENCE_COLUMNS = [
    "demand_id",
    "demand_name",
    "market_size_score",
    "expansion_score",
    "growth_score",
    "seasonality_score",
    "evidence_score",
    "overall_score",
    "market_size_tier",
    "expansion_tier",
    "research_priority",
    "recommended_strategy",
    "executive_summary",
]

EXPANSION_GRAPH_COLUMNS = [
    "parent_demand",
    "segment_count",
    "seasonal_segments",
    "interest_segments",
    "pet_segments",
    "profession_segments",
    "occasion_segments",
    "theme_segments",
    "expansion_score",
]

RESEARCH_QUEUE_COLUMNS = [
    "priority",
    "demand",
    "reason",
    "recommended_action",
    "next_step",
]

EXECUTIVE_DASHBOARD_COLUMNS = [
    "Total Demand",
    "P1",
    "P2",
    "P3",
    "Top Opportunity",
    "Largest Market",
    "Highest Expansion",
    "Fastest Growing",
    "Highest Seasonality",
]

SIZE_TIER_SCORE = {"Mega": 100.0, "Large": 82.0, "Mid": 62.0, "Small": 42.0, "Micro": 22.0}
TREND_SCORE = {"growing": 90.0, "emerging": 82.0, "stable": 65.0, "declining": 30.0}
GROWTH_SIGNAL_SCORE = {
    "Strong Growth": 95.0,
    "Growing": 85.0,
    "Emerging": 78.0,
    "Stable": 62.0,
    "Declining": 25.0,
    "Unknown": 45.0,
}
SEASONALITY_SCORE = {
    "Evergreen": 72.0,
    "Q4 Seasonal": 88.0,
    "Holiday Seasonal": 80.0,
    "Emerging": 76.0,
    "Declining": 35.0,
    "Insufficient Data": 30.0,
}

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build Demand Intelligence V1 CSVs from existing exports."
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Replace existing Demand Intelligence CSVs.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help="Folder for Demand Intelligence CSV outputs.",
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


def read_required_csv(name: str) -> pd.DataFrame:
    path = INPUT_PATHS[name]
    if not path.exists():
        raise FileNotFoundError(f"Missing required input CSV: {display_path(path)}")

    frame = pd.read_csv(path)
    missing = sorted(REQUIRED_COLUMNS[name] - set(frame.columns))
    if missing:
        raise RuntimeError(
            f"{display_path(path)} is missing required columns: {', '.join(missing)}"
        )
    logger.info("Input %s: %s rows", display_path(path), f"{len(frame):,}")
    return frame


def ensure_rebuild_allowed(output_dir: Path, rebuild: bool) -> None:
    existing = [output_dir / file_name for file_name in OUTPUT_FILES.values() if (output_dir / file_name).exists()]
    if existing and not rebuild:
        names = ", ".join(display_path(path) for path in existing)
        raise RuntimeError(
            "Demand Intelligence CSVs already exist. "
            f"Rerun with --rebuild to replace: {names}"
        )


def remove_existing_outputs(output_dir: Path) -> None:
    for file_name in OUTPUT_FILES.values():
        path = output_dir / file_name
        if path.exists():
            logger.info("Replacing %s", display_path(path))
            path.unlink()


def clean_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def lower_text(value: object) -> str:
    return clean_text(value).lower()


def numeric(value: object, default: float = 0.0) -> float:
    if pd.isna(value):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def rank_score(rank: object, max_rank: float = 1_500_000.0) -> float:
    rank_value = max(numeric(rank, max_rank), 1.0)
    return max(0.0, min(100.0, 100.0 * (1.0 - math.log(rank_value) / math.log(max(max_rank, 2.0)))))


def market_size_score(row: pd.Series) -> float:
    return round(
        rank_score(row.get("best_rank")) * 0.45
        + rank_score(row.get("p25_rank")) * 0.30
        + rank_score(row.get("median_rank")) * 0.25,
        2,
    )


def tier_from_score(score: float, strong_name: str = "High") -> str:
    if score >= 85:
        return "Very High" if strong_name == "High" else "Broad"
    if score >= 70:
        return strong_name
    if score >= 55:
        return "Medium"
    if score >= 40:
        return "Low"
    return "Limited"


def priority_from_score(score: float) -> str:
    if score >= 69:
        return "P1"
    if score >= 60:
        return "P2"
    if score >= 50:
        return "P3"
    return "Watchlist"


def strategy_from_components(
    market_size_tier: str,
    expansion_score: float,
    growth_score: float,
    seasonality_score: float,
    overall_score: float,
) -> str:
    if overall_score < 45:
        return "Low Priority"
    if market_size_tier in {"Mega", "Large"} and expansion_score >= 65 and growth_score >= 60:
        return "Core Market"
    if seasonality_score >= 80 and market_size_tier in {"Mega", "Large", "Mid"}:
        return "Seasonal Expansion"
    if growth_score >= 80 and overall_score >= 55:
        return "Emerging Opportunity"
    if expansion_score >= 65:
        return "Niche Expansion"
    if overall_score >= 50:
        return "Validate Further"
    return "Low Priority"


def segment_direction(row: pd.Series) -> str:
    if clean_text(row.get("holiday")):
        return "Seasonal Segment"
    if clean_text(row.get("pet")):
        return "Pet Segment"
    if clean_text(row.get("profession")):
        return "Profession Segment"
    if clean_text(row.get("occasion")):
        return "Occasion Segment"
    if clean_text(row.get("theme")):
        return "Theme Segment"
    if clean_text(row.get("lifestyle")):
        return "Lifestyle Segment"
    if clean_text(row.get("interest")):
        return "Interest Segment"
    return "Core Segment"


def build_expansion_graph(segments: pd.DataFrame) -> pd.DataFrame:
    if segments.empty:
        return pd.DataFrame(columns=EXPANSION_GRAPH_COLUMNS)

    working = segments.copy()
    working["direction_type"] = working.apply(segment_direction, axis=1)
    working["parent_demand_key"] = working["parent_demand"].astype(str)

    rows = []
    for parent_demand, group in working.groupby("parent_demand_key"):
        segment_count = len(group)
        seasonal_segments = int((group["direction_type"] == "Seasonal Segment").sum())
        interest_segments = int((group["direction_type"] == "Interest Segment").sum())
        pet_segments = int((group["direction_type"] == "Pet Segment").sum())
        profession_segments = int((group["direction_type"] == "Profession Segment").sum())
        occasion_segments = int((group["direction_type"] == "Occasion Segment").sum())
        theme_segments = int((group["direction_type"] == "Theme Segment").sum())
        segment_types = group["direction_type"].nunique()
        interest_diversity = group["interest"].dropna().astype(str).str.strip()
        interest_diversity = interest_diversity[interest_diversity != ""].nunique()
        occasion_diversity = group["occasion"].dropna().astype(str).str.strip()
        occasion_diversity = occasion_diversity[occasion_diversity != ""].nunique()
        strength_bonus = min(20.0, numeric(group["segment_strength"].max(), 0.0) * 0.45)

        expansion_score = round(
            min(
                100.0,
                min(segment_count, 20) * 3.0
                + segment_types * 7.0
                + min(interest_diversity, 8) * 3.0
                + min(occasion_diversity, 6) * 2.5
                + strength_bonus,
            ),
            2,
        )
        rows.append(
            {
                "parent_demand": parent_demand,
                "segment_count": segment_count,
                "seasonal_segments": seasonal_segments,
                "interest_segments": interest_segments,
                "pet_segments": pet_segments,
                "profession_segments": profession_segments,
                "occasion_segments": occasion_segments,
                "theme_segments": theme_segments,
                "expansion_score": expansion_score,
            }
        )

    return pd.DataFrame(rows, columns=EXPANSION_GRAPH_COLUMNS).sort_values(
        ["expansion_score", "segment_count"],
        ascending=[False, False],
        na_position="last",
    ).reset_index(drop=True)


def demand_seasonality_score(
    demand_id: str,
    demand_name: str,
    seasonality_map: pd.DataFrame,
    segments: pd.DataFrame,
) -> float:
    demand_rows = seasonality_map[
        (seasonality_map["entity_type"] == "Demand")
        & (seasonality_map["entity_id"].astype(str) == str(demand_id))
    ]
    score_values = []
    if not demand_rows.empty:
        score_values.extend(
            demand_rows["seasonality_type"].map(SEASONALITY_SCORE).fillna(45.0).tolist()
        )

    child_segments = segments[segments["parent_demand"].astype(str) == str(demand_name)]
    if not child_segments.empty:
        seasonal_count = (
            child_segments[["holiday", "occasion"]]
            .fillna("")
            .astype(str)
            .apply(lambda row: bool(row["holiday"].strip() or row["occasion"].strip()), axis=1)
            .sum()
        )
        if seasonal_count:
            score_values.append(min(100.0, 55.0 + seasonal_count * 5.0))

    if not score_values:
        return 45.0
    return round(max(score_values), 2)


def demand_growth_score(row: pd.Series, growth_map: pd.DataFrame) -> float:
    growth_rows = growth_map[
        (growth_map["entity_type"] == "Demand")
        & (growth_map["entity_id"].astype(str) == str(row.get("demand_id")))
    ]
    if not growth_rows.empty:
        base = GROWTH_SIGNAL_SCORE.get(clean_text(growth_rows.iloc[0].get("growth_signal")), 45.0)
    else:
        base = TREND_SCORE.get(lower_text(row.get("trend")), 45.0)

    active_bonus = min(10.0, numeric(row.get("active_months")) * 2.5)
    strength_bonus = min(12.0, numeric(row.get("strength_score")) * 0.20)
    return round(min(100.0, base * 0.75 + active_bonus + strength_bonus), 2)


def evidence_score(row: pd.Series, opportunities: pd.DataFrame, segments: pd.DataFrame) -> float:
    demand_id = str(row.get("demand_id"))
    demand_name = str(row.get("demand_name"))
    opportunity_rows = opportunities[opportunities["demand_id"].astype(str) == demand_id]
    opportunity_evidence = (
        numeric(opportunity_rows["evidence_score"].max(), 0.0) if not opportunity_rows.empty else 0.0
    )

    child_segments = segments[segments["parent_demand"].astype(str) == demand_name]
    keyword_coverage = rank_score(row.get("median_rank"))
    segment_consistency = min(30.0, len(child_segments) * 2.0)
    active_consistency = min(20.0, numeric(row.get("active_months")) * 5.0)
    return round(
        min(
            100.0,
            opportunity_evidence * 0.40
            + keyword_coverage * 0.25
            + segment_consistency
            + active_consistency,
        ),
        2,
    )


def executive_summary(
    demand_name: str,
    market_size_tier: str,
    expansion_tier: str,
    strategy: str,
    trend: str,
) -> str:
    size_text = market_size_tier.lower()
    expansion_text = expansion_tier.lower()
    trend_text = trend or "unknown"
    if strategy == "Core Market":
        return (
            f"{demand_name} is a {size_text} demand with {expansion_text} expansion "
            f"potential and {trend_text} ranking signals. Focus on scalable child niches."
        )
    if strategy == "Seasonal Expansion":
        return (
            f"{demand_name} has seasonal leverage with {size_text} rank signals. "
            "Plan research around timing-sensitive segments."
        )
    if strategy == "Emerging Opportunity":
        return (
            f"{demand_name} is showing emerging or improving momentum. Validate next-month "
            "rank durability before scaling research."
        )
    if strategy == "Niche Expansion":
        return (
            f"{demand_name} has useful child-segment breadth. Explore niche angles before "
            "committing to product concepts."
        )
    if strategy == "Validate Further":
        return (
            f"{demand_name} has some business signal but needs validation on expansion, "
            "seasonality, or evidence quality."
        )
    return f"{demand_name} is lower priority in current evidence; monitor until rank signals improve."


def build_demand_intelligence(
    demand_strength: pd.DataFrame,
    demand_size_map: pd.DataFrame,
    segments: pd.DataFrame,
    opportunities: pd.DataFrame,
    seasonality_map: pd.DataFrame,
    growth_map: pd.DataFrame,
    expansion_graph: pd.DataFrame,
) -> pd.DataFrame:
    size_lookup = demand_size_map[["demand_id", "size_tier"]].rename(
        columns={"size_tier": "market_size_tier"}
    )
    output = demand_strength.merge(size_lookup, on="demand_id", how="left")
    output["market_size_tier"] = output["market_size_tier"].fillna("Micro")
    output["market_size_score"] = output.apply(market_size_score, axis=1)

    expansion_lookup = expansion_graph[["parent_demand", "expansion_score"]].rename(
        columns={"parent_demand": "demand_name"}
    )
    output = output.merge(expansion_lookup, on="demand_name", how="left")
    output["expansion_score"] = output["expansion_score"].fillna(0.0)
    output["expansion_tier"] = output["expansion_score"].apply(lambda score: tier_from_score(score, "High"))

    output["growth_score"] = output.apply(lambda row: demand_growth_score(row, growth_map), axis=1)
    output["seasonality_score"] = output.apply(
        lambda row: demand_seasonality_score(
            str(row["demand_id"]),
            str(row["demand_name"]),
            seasonality_map,
            segments,
        ),
        axis=1,
    )
    output["evidence_score"] = output.apply(lambda row: evidence_score(row, opportunities, segments), axis=1)
    output["overall_score"] = (
        output["market_size_score"] * 0.30
        + output["expansion_score"] * 0.25
        + output["growth_score"] * 0.20
        + output["seasonality_score"] * 0.10
        + output["evidence_score"] * 0.15
    ).round(2)
    output["research_priority"] = output["overall_score"].apply(priority_from_score)
    output["recommended_strategy"] = output.apply(
        lambda row: strategy_from_components(
            row["market_size_tier"],
            numeric(row["expansion_score"]),
            numeric(row["growth_score"]),
            numeric(row["seasonality_score"]),
            numeric(row["overall_score"]),
        ),
        axis=1,
    )
    output["executive_summary"] = output.apply(
        lambda row: executive_summary(
            clean_text(row["demand_name"]),
            clean_text(row["market_size_tier"]),
            clean_text(row["expansion_tier"]),
            clean_text(row["recommended_strategy"]),
            lower_text(row.get("trend")),
        ),
        axis=1,
    )

    return output[DEMAND_INTELLIGENCE_COLUMNS].sort_values(
        ["overall_score", "market_size_score", "expansion_score"],
        ascending=[False, False, False],
        na_position="last",
    ).reset_index(drop=True)


def top_segment_examples(parent_demand: str, segments: pd.DataFrame, limit: int = 3) -> str:
    rows = segments[segments["parent_demand"].astype(str) == str(parent_demand)].copy()
    if rows.empty:
        return ""
    rows = rows.sort_values(["segment_strength", "best_rank"], ascending=[False, True], na_position="last")
    names = rows["segment_name"].head(limit).dropna().astype(str).tolist()
    return ", ".join(names)


def build_research_queue(demand_intelligence: pd.DataFrame, segments: pd.DataFrame) -> pd.DataFrame:
    queue_rows = []
    priority_rows = demand_intelligence[
        demand_intelligence["research_priority"].isin(["P1", "P2", "P3"])
    ].copy()
    priority_rows = priority_rows.sort_values(
        ["research_priority", "overall_score"],
        ascending=[True, False],
        key=lambda series: series.map({"P1": 1, "P2": 2, "P3": 3}) if series.name == "research_priority" else series,
    )

    for _, row in priority_rows.iterrows():
        demand_name = clean_text(row["demand_name"])
        examples = top_segment_examples(demand_name, segments)
        if examples:
            next_step = f"Research micro niches such as {examples}."
        else:
            next_step = "Validate demand language, audience fit, and product angles."

        if row["recommended_strategy"] == "Core Market":
            action = "Research scalable child niches and compare product formats."
            reason = f"{demand_name} is a {row['market_size_tier'].lower()} demand with strong rank and expansion signals."
        elif row["recommended_strategy"] == "Seasonal Expansion":
            action = "Plan seasonal research and validate timing windows."
            reason = f"{demand_name} has a strong seasonal opportunity profile."
        elif row["recommended_strategy"] == "Emerging Opportunity":
            action = "Monitor rank durability and validate niche language."
            reason = f"{demand_name} has improving or emerging demand momentum."
        elif row["recommended_strategy"] == "Niche Expansion":
            action = "Expand niche research from the strongest child segments."
            reason = f"{demand_name} has multiple expansion paths in child segments."
        else:
            action = "Validate evidence quality before assigning deeper research."
            reason = f"{demand_name} has enough signal for review but needs confirmation."

        queue_rows.append(
            {
                "priority": row["research_priority"],
                "demand": demand_name,
                "reason": reason,
                "recommended_action": action,
                "next_step": next_step,
            }
        )

    return pd.DataFrame(queue_rows, columns=RESEARCH_QUEUE_COLUMNS)


def top_name(frame: pd.DataFrame, sort_column: str, name_column: str = "demand_name") -> str:
    if frame.empty or sort_column not in frame.columns or name_column not in frame.columns:
        return ""
    ordered = frame.sort_values(sort_column, ascending=False, na_position="last")
    if ordered.empty:
        return ""
    return clean_text(ordered.iloc[0].get(name_column))


def build_executive_dashboard(
    demand_intelligence: pd.DataFrame,
    expansion_graph: pd.DataFrame,
    opportunities: pd.DataFrame,
) -> pd.DataFrame:
    priority_counts = demand_intelligence["research_priority"].value_counts()
    top_opportunity = ""
    if not opportunities.empty:
        top_opportunity = clean_text(
            opportunities.sort_values("opportunity_score", ascending=False, na_position="last")
            .iloc[0]
            .get("demand_name")
        )

    highest_expansion = ""
    if not expansion_graph.empty:
        highest_expansion = clean_text(
            expansion_graph.sort_values("expansion_score", ascending=False, na_position="last")
            .iloc[0]
            .get("parent_demand")
        )

    fastest = demand_intelligence.copy()
    fastest["_growth_sort"] = fastest["growth_score"]
    fastest_growing = top_name(fastest, "_growth_sort")

    seasonality = demand_intelligence.copy()
    seasonality["_seasonality_sort"] = seasonality["seasonality_score"]

    row = {
        "Total Demand": len(demand_intelligence),
        "P1": int(priority_counts.get("P1", 0)),
        "P2": int(priority_counts.get("P2", 0)),
        "P3": int(priority_counts.get("P3", 0)),
        "Top Opportunity": top_opportunity,
        "Largest Market": top_name(demand_intelligence, "market_size_score"),
        "Highest Expansion": highest_expansion,
        "Fastest Growing": fastest_growing,
        "Highest Seasonality": top_name(seasonality, "_seasonality_sort"),
    }
    return pd.DataFrame([row], columns=EXECUTIVE_DASHBOARD_COLUMNS)


def write_csv(frame: pd.DataFrame, output_dir: Path, file_key: str) -> None:
    output_path = output_dir / OUTPUT_FILES[file_key]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_path, index=False)
    logger.info("Exported %s with %s rows", display_path(output_path), f"{len(frame):,}")


def build_demand_intelligence_layer(output_dir: Path, rebuild: bool) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    ensure_rebuild_allowed(output_dir, rebuild)
    if rebuild:
        remove_existing_outputs(output_dir)

    composite_demands = read_required_csv("composite_demands")
    demand_strength = read_required_csv("demand_strength_v3")
    segments = read_required_csv("demand_segments")
    opportunities = read_required_csv("opportunity_master")
    demand_size_map = read_required_csv("demand_size_map")
    segment_size_map = read_required_csv("segment_size_map")
    seasonality_map = read_required_csv("seasonality_map")
    growth_map = read_required_csv("growth_map")
    niche_direction_map = read_required_csv("niche_direction_map")
    research_opportunity_queue = read_required_csv("research_opportunity_queue")

    logger.info("Validated canonical demand export with %s rows", f"{len(composite_demands):,}")
    logger.info("Validated insight queue with %s rows", f"{len(research_opportunity_queue):,}")
    logger.info("Validated niche direction map with %s rows", f"{len(niche_direction_map):,}")

    expansion_graph = build_expansion_graph(segments)
    demand_intelligence = build_demand_intelligence(
        demand_strength,
        demand_size_map,
        segments,
        opportunities,
        seasonality_map,
        growth_map,
        expansion_graph,
    )
    research_queue = build_research_queue(demand_intelligence, segments)
    executive_dashboard = build_executive_dashboard(
        demand_intelligence,
        expansion_graph,
        opportunities,
    )

    write_csv(demand_intelligence, output_dir, "demand_intelligence")
    write_csv(expansion_graph, output_dir, "expansion_graph")
    write_csv(research_queue, output_dir, "research_queue")
    write_csv(executive_dashboard, output_dir, "executive_dashboard")

    logger.info("Demand Intelligence build complete")


def main() -> None:
    configure_logging()
    args = parse_args()
    logger.info("Starting Demand Intelligence build")
    build_demand_intelligence_layer(output_dir=args.output_dir.resolve(), rebuild=args.rebuild)
    logger.info("Build log: %s", display_path(LOG_PATH))


if __name__ == "__main__":
    main()
