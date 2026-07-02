"""Build Market Intelligence CSVs from existing demand intelligence exports."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "data" / "output" / "intelligence"
LOG_DIR = PROJECT_ROOT / "logs"
LOG_PATH = LOG_DIR / "build_market_intelligence.log"

INPUT_PATHS = {
    "demand_intelligence": OUTPUT_DIR / "demand_intelligence.csv",
    "expansion_graph": OUTPUT_DIR / "expansion_graph.csv",
    "demand_size_map": PROJECT_ROOT / "data" / "output" / "insights" / "demand_size_map.csv",
    "seasonality_map": PROJECT_ROOT / "data" / "output" / "insights" / "seasonality_map.csv",
    "growth_map": PROJECT_ROOT / "data" / "output" / "insights" / "growth_map.csv",
    "demand_segments": PROJECT_ROOT / "data" / "output" / "demand_segments" / "demand_segments.csv",
    "opportunity_master": PROJECT_ROOT / "data" / "output" / "opportunity" / "opportunity_master.csv",
}

OUTPUT_FILES = {
    "market_intelligence": "market_intelligence.csv",
    "research_portfolio": "research_portfolio.csv",
    "expansion_tree": "expansion_tree.csv",
    "market_stage": "market_stage.csv",
}

REQUIRED_COLUMNS = {
    "demand_intelligence": {
        "demand_id",
        "demand_name",
        "market_size_score",
        "expansion_score",
        "growth_score",
        "seasonality_score",
        "overall_score",
        "market_size_tier",
        "research_priority",
        "recommended_strategy",
    },
    "expansion_graph": {
        "parent_demand",
        "segment_count",
        "seasonal_segments",
        "interest_segments",
        "pet_segments",
        "profession_segments",
        "occasion_segments",
        "theme_segments",
        "expansion_score",
    },
    "demand_size_map": {
        "demand_id",
        "demand_name",
        "size_tier",
        "best_rank",
        "active_months",
        "trend",
        "strength_score",
    },
    "seasonality_map": {"entity_type", "entity_id", "entity_name", "seasonality_type"},
    "growth_map": {"entity_type", "entity_id", "entity_name", "growth_signal", "active_months"},
    "demand_segments": {
        "segment_id",
        "parent_demand",
        "segment_name",
        "interest",
        "pet",
        "profession",
        "holiday",
        "occasion",
        "theme",
        "lifestyle",
        "segment_strength",
    },
    "opportunity_master": {
        "demand_id",
        "demand_name",
        "opportunity_score",
        "priority",
        "best_rank",
    },
}

MARKET_INTELLIGENCE_COLUMNS = [
    "demand_id",
    "demand_name",
    "market_size",
    "growth_stage",
    "market_stage",
    "expansion_score",
    "competition_level",
    "seasonality_type",
    "research_priority",
    "recommendation",
    "top_child_segments",
]

RESEARCH_PORTFOLIO_COLUMNS = [
    "priority",
    "demand",
    "reason",
    "next_action",
    "estimated_roi",
]

EXPANSION_TREE_COLUMNS = [
    "parent_demand",
    "child_segment",
    "relation_type",
    "segment_strength",
]

MARKET_STAGE_COLUMNS = [
    "demand",
    "stage",
    "evidence",
    "recommendation",
]

SIZE_ORDER = {"Mega": 1, "Large": 2, "Mid": 3, "Small": 4, "Micro": 5}
PORTFOLIO_PRIORITY_ORDER = {"P1": 1, "P2": 2, "P3": 3, "Watchlist": 4}

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build Market Intelligence CSVs from existing demand intelligence outputs."
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Replace existing Market Intelligence CSVs.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help="Folder for Market Intelligence CSV outputs.",
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
            "Market Intelligence CSVs already exist. "
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


def first_nonempty(values: list[object], default: str = "") -> str:
    for value in values:
        text = clean_text(value)
        if text:
            return text
    return default


def relation_type(row: pd.Series) -> str:
    if clean_text(row.get("holiday")):
        return "Seasonal"
    if clean_text(row.get("occasion")):
        return "Occasion"
    if clean_text(row.get("pet")):
        return "Pet"
    if clean_text(row.get("profession")):
        return "Profession"
    if clean_text(row.get("lifestyle")):
        return "Lifestyle"
    if clean_text(row.get("theme")):
        return "Theme"
    if clean_text(row.get("interest")):
        return "Interest"
    return "Core"


def build_expansion_tree(segments: pd.DataFrame) -> pd.DataFrame:
    output = segments.copy()
    output["relation_type"] = output.apply(relation_type, axis=1)
    output = output.rename(
        columns={
            "segment_name": "child_segment",
        }
    )
    output = output[
        ["parent_demand", "child_segment", "relation_type", "segment_strength"]
    ].sort_values(
        ["parent_demand", "segment_strength", "child_segment"],
        ascending=[True, False, True],
        na_position="last",
    )
    return output.reset_index(drop=True)


def growth_stage(row: pd.Series, growth_map: pd.DataFrame) -> str:
    growth_rows = growth_map[
        (growth_map["entity_type"] == "Demand")
        & (growth_map["entity_id"].astype(str) == str(row.get("demand_id")))
    ]
    growth_signal = clean_text(growth_rows.iloc[0]["growth_signal"]) if not growth_rows.empty else ""
    trend = lower_text(row.get("trend"))
    active_months = numeric(row.get("active_months"), 0.0)

    if growth_signal == "Strong Growth" or trend == "growing":
        return "Growing"
    if growth_signal == "Emerging" or trend == "emerging":
        return "Emerging"
    if growth_signal == "Declining" or trend == "declining":
        return "Declining"
    if active_months >= 3:
        return "Established"
    return "Unproven"


def market_stage(
    size_tier: str,
    trend: str,
    active_months: float,
    segment_count: float,
    expansion_score: float,
) -> str:
    if active_months < 2:
        return "Early Signal"
    if trend == "declining":
        return "Mature / Declining"
    if size_tier in {"Mega", "Large"} and segment_count >= 8 and trend == "growing":
        return "Scale Market"
    if size_tier in {"Mega", "Large"} and active_months >= 3:
        return "Established Market"
    if expansion_score >= 65 and segment_count >= 5:
        return "Expansion Market"
    if trend in {"growing", "emerging"}:
        return "Growth Market"
    return "Validation Market"


def competition_level(size_tier: str, opportunity_score: float, segment_count: float) -> str:
    if size_tier == "Mega" or opportunity_score >= 85:
        return "High"
    if size_tier == "Large" or segment_count >= 10 or opportunity_score >= 70:
        return "Medium"
    if size_tier == "Mid" or segment_count >= 4:
        return "Low-Medium"
    return "Low"


def seasonality_for_demand(demand_id: str, seasonality_map: pd.DataFrame) -> str:
    rows = seasonality_map[
        (seasonality_map["entity_type"] == "Demand")
        & (seasonality_map["entity_id"].astype(str) == str(demand_id))
    ]
    if rows.empty:
        return "Unknown"
    return first_nonempty(rows["seasonality_type"].tolist(), "Unknown")


def top_child_segments(parent_demand: str, segments: pd.DataFrame, limit: int = 5) -> str:
    rows = segments[segments["parent_demand"].astype(str) == str(parent_demand)].copy()
    if rows.empty:
        return ""
    rows = rows.sort_values(["segment_strength", "best_rank"], ascending=[False, True], na_position="last")
    return " | ".join(rows["segment_name"].head(limit).dropna().astype(str).tolist())


def recommendation(
    stage: str,
    size_tier: str,
    segment_count: float,
    seasonality_type: str,
    top_segments: str,
) -> str:
    if stage == "Scale Market":
        return "Research child segments first; use parent demand as the umbrella market."
    if stage == "Established Market" and segment_count >= 3:
        return "Research best child segments before broad parent-demand product work."
    if seasonality_type in {"Q4 Seasonal", "Holiday Seasonal"}:
        return "Research seasonal segments and validate timing windows."
    if stage == "Growth Market":
        return "Validate ranking durability and research focused child niches."
    if size_tier in {"Mega", "Large"}:
        return "Research parent demand positioning, then segment into niches."
    if top_segments:
        return "Research child segments; parent demand is too broad for direct action."
    return "Validate further before assigning research."


def estimated_roi(priority: str, market_size: str, expansion_score: float, stage: str) -> str:
    if priority == "P1" and market_size in {"Mega", "Large"} and expansion_score >= 70:
        return "High"
    if priority in {"P1", "P2"} and stage in {"Scale Market", "Expansion Market", "Growth Market"}:
        return "Medium-High"
    if priority in {"P2", "P3"}:
        return "Medium"
    if stage == "Early Signal":
        return "Unproven"
    return "Low"


def build_market_intelligence(
    demand_intelligence: pd.DataFrame,
    expansion_graph: pd.DataFrame,
    demand_size_map: pd.DataFrame,
    seasonality_map: pd.DataFrame,
    growth_map: pd.DataFrame,
    segments: pd.DataFrame,
    opportunities: pd.DataFrame,
) -> pd.DataFrame:
    demand_metrics = demand_size_map[
        ["demand_id", "demand_name", "size_tier", "active_months", "trend", "best_rank"]
    ].rename(columns={"size_tier": "market_size"})
    output = demand_intelligence.merge(
        demand_metrics,
        on=["demand_id", "demand_name"],
        how="left",
    )
    output = output.merge(
        expansion_graph[["parent_demand", "segment_count", "expansion_score"]],
        left_on="demand_name",
        right_on="parent_demand",
        how="left",
        suffixes=("", "_graph"),
    )
    output["segment_count"] = output["segment_count"].fillna(0)
    output["expansion_score"] = output["expansion_score_graph"].fillna(output["expansion_score"])
    output = output.drop(columns=["parent_demand", "expansion_score_graph"], errors="ignore")

    opportunity_lookup = opportunities.groupby("demand_id", as_index=False).agg(
        opportunity_score=("opportunity_score", "max")
    )
    output = output.merge(opportunity_lookup, on="demand_id", how="left")
    output["opportunity_score"] = output["opportunity_score"].fillna(0.0)

    output["growth_stage"] = output.apply(lambda row: growth_stage(row, growth_map), axis=1)
    output["market_stage"] = output.apply(
        lambda row: market_stage(
            clean_text(row.get("market_size")),
            lower_text(row.get("trend")),
            numeric(row.get("active_months")),
            numeric(row.get("segment_count")),
            numeric(row.get("expansion_score")),
        ),
        axis=1,
    )
    output["competition_level"] = output.apply(
        lambda row: competition_level(
            clean_text(row.get("market_size")),
            numeric(row.get("opportunity_score")),
            numeric(row.get("segment_count")),
        ),
        axis=1,
    )
    output["seasonality_type"] = output["demand_id"].apply(
        lambda demand_id: seasonality_for_demand(str(demand_id), seasonality_map)
    )
    output["top_child_segments"] = output["demand_name"].apply(
        lambda demand_name: top_child_segments(str(demand_name), segments)
    )
    output["recommendation"] = output.apply(
        lambda row: recommendation(
            clean_text(row.get("market_stage")),
            clean_text(row.get("market_size")),
            numeric(row.get("segment_count")),
            clean_text(row.get("seasonality_type")),
            clean_text(row.get("top_child_segments")),
        ),
        axis=1,
    )

    output = output[MARKET_INTELLIGENCE_COLUMNS]
    return output.sort_values(
        ["research_priority", "expansion_score", "demand_name"],
        ascending=[True, False, True],
        key=lambda series: series.map(PORTFOLIO_PRIORITY_ORDER) if series.name == "research_priority" else series,
        na_position="last",
    ).reset_index(drop=True)


def stage_evidence(row: pd.Series, expansion_graph: pd.DataFrame) -> str:
    graph_rows = expansion_graph[expansion_graph["parent_demand"].astype(str) == str(row["demand_name"])]
    segment_count = int(graph_rows.iloc[0]["segment_count"]) if not graph_rows.empty else 0
    return (
        f"Market size {row['market_size']}; trend stage {row['growth_stage']}; "
        f"{segment_count} child segment(s); seasonality {row['seasonality_type']}."
    )


def build_market_stage(market_intelligence: pd.DataFrame, expansion_graph: pd.DataFrame) -> pd.DataFrame:
    output = pd.DataFrame(
        {
            "demand": market_intelligence["demand_name"],
            "stage": market_intelligence["market_stage"],
            "evidence": market_intelligence.apply(lambda row: stage_evidence(row, expansion_graph), axis=1),
            "recommendation": market_intelligence["recommendation"],
        }
    )
    return output.sort_values(["stage", "demand"]).reset_index(drop=True)


def portfolio_reason(row: pd.Series) -> str:
    if clean_text(row["top_child_segments"]):
        return (
            f"{row['market_size']} {row['market_stage'].lower()} with "
            f"{row['growth_stage'].lower()} signal and child segments available."
        )
    return f"{row['market_size']} {row['market_stage'].lower()} with {row['growth_stage'].lower()} signal."


def portfolio_next_action(row: pd.Series) -> str:
    if "child segments" in lower_text(row["recommendation"]) and clean_text(row["top_child_segments"]):
        return f"Start with: {row['top_child_segments']}."
    return row["recommendation"]


def build_research_portfolio(market_intelligence: pd.DataFrame) -> pd.DataFrame:
    candidates = market_intelligence[
        market_intelligence["research_priority"].isin(["P1", "P2", "P3"])
    ].copy()
    if candidates.empty:
        candidates = market_intelligence.head(25).copy()

    candidates["reason"] = candidates.apply(portfolio_reason, axis=1)
    candidates["next_action"] = candidates.apply(portfolio_next_action, axis=1)
    candidates["estimated_roi"] = candidates.apply(
        lambda row: estimated_roi(
            clean_text(row["research_priority"]),
            clean_text(row["market_size"]),
            numeric(row["expansion_score"]),
            clean_text(row["market_stage"]),
        ),
        axis=1,
    )
    output = candidates.rename(
        columns={
            "research_priority": "priority",
            "demand_name": "demand",
        }
    )[["priority", "demand", "reason", "next_action", "estimated_roi"]]
    return output.sort_values(
        ["priority", "estimated_roi", "demand"],
        ascending=[True, True, True],
        key=lambda series: series.map(PORTFOLIO_PRIORITY_ORDER) if series.name == "priority" else series,
    ).reset_index(drop=True)


def write_csv(frame: pd.DataFrame, output_dir: Path, file_key: str) -> None:
    output_path = output_dir / OUTPUT_FILES[file_key]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_path, index=False)
    logger.info("Exported %s with %s rows", display_path(output_path), f"{len(frame):,}")


def build_market_intelligence_layer(output_dir: Path, rebuild: bool) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    ensure_rebuild_allowed(output_dir, rebuild)
    if rebuild:
        remove_existing_outputs(output_dir)

    demand_intelligence = read_required_csv("demand_intelligence")
    existing_expansion_graph = read_required_csv("expansion_graph")
    demand_size_map = read_required_csv("demand_size_map")
    seasonality_map = read_required_csv("seasonality_map")
    growth_map = read_required_csv("growth_map")
    segments = read_required_csv("demand_segments")
    opportunities = read_required_csv("opportunity_master")

    expansion_tree = build_expansion_tree(segments)
    market_intelligence = build_market_intelligence(
        demand_intelligence,
        existing_expansion_graph,
        demand_size_map,
        seasonality_map,
        growth_map,
        segments,
        opportunities,
    )
    research_portfolio = build_research_portfolio(market_intelligence)
    market_stage_frame = build_market_stage(market_intelligence, existing_expansion_graph)

    write_csv(market_intelligence, output_dir, "market_intelligence")
    write_csv(research_portfolio, output_dir, "research_portfolio")
    write_csv(expansion_tree, output_dir, "expansion_tree")
    write_csv(market_stage_frame, output_dir, "market_stage")

    logger.info("Market Intelligence build complete")


def main() -> None:
    configure_logging()
    args = parse_args()
    logger.info("Starting Market Intelligence build")
    build_market_intelligence_layer(output_dir=args.output_dir.resolve(), rebuild=args.rebuild)
    logger.info("Build log: %s", display_path(LOG_PATH))


if __name__ == "__main__":
    main()
