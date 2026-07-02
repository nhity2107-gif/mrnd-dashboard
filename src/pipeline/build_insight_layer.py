"""Build Insight Layer V1 CSVs from existing dashboard exports."""

from __future__ import annotations

import argparse
import logging
import math
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "data" / "output" / "insights"
LOG_DIR = PROJECT_ROOT / "logs"
LOG_PATH = LOG_DIR / "build_insight_layer.log"

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
    "intent_summary": PROJECT_ROOT
    / "data"
    / "output"
    / "intent_layer"
    / "intent_summary.csv",
}

OUTPUT_FILES = {
    "demand_size_map": "demand_size_map.csv",
    "segment_size_map": "segment_size_map.csv",
    "seasonality_map": "seasonality_map.csv",
    "growth_map": "growth_map.csv",
    "niche_direction_map": "niche_direction_map.csv",
    "research_opportunity_queue": "research_opportunity_queue.csv",
}

REQUIRED_COLUMNS = {
    "composite_demands": {"demand_id", "demand_name", "best_rank", "trend"},
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
        "parent_demand",
        "segment_name",
        "best_rank",
        "median_rank",
        "keyword_count",
        "active_months",
        "trend",
        "segment_strength",
    },
    "opportunity_master": {
        "opportunity_id",
        "demand_id",
        "demand_name",
        "best_rank",
        "active_months",
        "trend",
        "opportunity_score",
        "priority",
    },
    "intent_summary": {"intent", "active_months", "first_month", "last_month"},
}

DEMAND_SIZE_COLUMNS = [
    "demand_id",
    "demand_name",
    "size_tier",
    "best_rank",
    "p25_rank",
    "median_rank",
    "keyword_count",
    "active_months",
    "trend",
    "strength_score",
    "insight_note",
]

SEGMENT_SIZE_COLUMNS = [
    "segment_id",
    "parent_demand",
    "segment_name",
    "size_tier",
    "best_rank",
    "median_rank",
    "keyword_count",
    "active_months",
    "trend",
    "segment_strength",
    "insight_note",
]

SEASONALITY_COLUMNS = [
    "entity_type",
    "entity_id",
    "entity_name",
    "start_month",
    "peak_month",
    "last_month",
    "active_months",
    "seasonality_type",
    "seasonality_note",
    "research_start_recommendation",
]

GROWTH_COLUMNS = [
    "entity_type",
    "entity_id",
    "entity_name",
    "trend",
    "growth_signal",
    "rank_momentum",
    "active_months",
    "growth_note",
]

NICHE_DIRECTION_COLUMNS = [
    "parent_demand",
    "segment_name",
    "direction_type",
    "size_tier",
    "trend",
    "best_rank",
    "segment_strength",
    "potential_direction_note",
]

RESEARCH_QUEUE_COLUMNS = [
    "priority_rank",
    "opportunity_type",
    "parent_demand",
    "segment_name",
    "size_tier",
    "trend",
    "seasonality_type",
    "best_rank",
    "strength_score",
    "reason",
    "recommended_action",
]

SIZE_ORDER = {"Mega": 1, "Large": 2, "Mid": 3, "Small": 4, "Micro": 5}
SIZE_SCORE = {"Mega": 100.0, "Large": 80.0, "Mid": 60.0, "Small": 40.0, "Micro": 20.0}
TREND_SCORE = {"growing": 25.0, "emerging": 20.0, "stable": 10.0, "declining": -10.0}

Q4_PEAK_MONTHS = {
    "halloween": "October",
    "thanksgiving": "November",
    "christmas": "December",
    "new year": "January",
}

HOLIDAY_PEAK_MONTHS = {
    "valentine": "February",
    "valentine's day": "February",
    "easter": "April",
    "mother's day": "May",
    "father's day": "June",
    "teacher appreciation": "May",
    "appreciation": "May",
    "graduation": "May",
    "wedding": "June",
}

SEASONAL_RESEARCH_START = {
    "halloween": "Start research by July; validate listings by August.",
    "thanksgiving": "Start research by August; validate listings by September.",
    "christmas": "Start research by August; validate listings by September.",
    "new year": "Start research by October; validate listings by November.",
    "valentine": "Start research by November; validate listings by December.",
    "valentine's day": "Start research by November; validate listings by December.",
    "easter": "Start research by January; validate listings by February.",
    "mother's day": "Start research by February; validate listings by March.",
    "father's day": "Start research by March; validate listings by April.",
    "teacher appreciation": "Start research by February; validate listings by March.",
    "appreciation": "Start research by February; validate listings by March.",
    "graduation": "Start research by January; validate listings by February.",
    "wedding": "Start research by February; validate listings by March.",
}

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build Insight Layer V1 CSVs from existing dashboard exports."
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Replace existing Insight Layer CSVs.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help="Folder for Insight Layer CSV outputs.",
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
        raise RuntimeError(f"Insight CSVs already exist. Rerun with --rebuild to replace: {names}")


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
    max_rank = max(max_rank, 2.0)
    return max(0.0, min(100.0, 100.0 * (1.0 - (math.log(rank_value) / math.log(max_rank)))))


def demand_size_tier(row: pd.Series) -> str:
    best_rank = numeric(row.get("best_rank"), 9_999_999.0)
    p25_rank = numeric(row.get("p25_rank"), 9_999_999.0)
    median_rank = numeric(row.get("median_rank"), 9_999_999.0)
    strength = numeric(row.get("strength_score"), 0.0)
    active_months = numeric(row.get("active_months"), 0.0)

    if best_rank <= 1_000 or (strength >= 38.0 and active_months >= 3):
        return "Mega"
    if best_rank <= 5_000 or (strength >= 33.0 and p25_rank <= 400_000):
        return "Large"
    if best_rank <= 25_000 or strength >= 27.0 or median_rank <= 550_000:
        return "Mid"
    if best_rank <= 100_000 or strength >= 20.0:
        return "Small"
    return "Micro"


def segment_size_tier(row: pd.Series) -> str:
    best_rank = numeric(row.get("best_rank"), 9_999_999.0)
    median_rank = numeric(row.get("median_rank"), 9_999_999.0)
    strength = numeric(row.get("segment_strength"), 0.0)
    active_months = numeric(row.get("active_months"), 0.0)

    if best_rank <= 2_000 or (strength >= 36.0 and active_months >= 3):
        return "Mega"
    if best_rank <= 10_000 or strength >= 30.0:
        return "Large"
    if best_rank <= 50_000 or strength >= 24.0 or median_rank <= 450_000:
        return "Mid"
    if best_rank <= 200_000 or strength >= 15.0:
        return "Small"
    return "Micro"


def size_note(entity_name: str, size_tier: str, trend: str, best_rank: object, active_months: object) -> str:
    rank_text = int(numeric(best_rank)) if numeric(best_rank) else "unknown"
    months_text = int(numeric(active_months))
    if size_tier in {"Mega", "Large"}:
        return (
            f"{entity_name} has {size_tier.lower()} rank-based demand "
            f"with best rank {rank_text} across {months_text} active month(s); trend is {trend}."
        )
    if size_tier == "Mid":
        return (
            f"{entity_name} has a mid-size signal; validate niche specificity before research."
        )
    if size_tier == "Small":
        return f"{entity_name} is a smaller signal; useful as a supporting niche or watchlist item."
    return f"{entity_name} is micro-scale in current ABA evidence; monitor before research investment."


def build_demand_size_map(demand_strength: pd.DataFrame) -> pd.DataFrame:
    output = demand_strength.copy()
    output["size_tier"] = output.apply(demand_size_tier, axis=1)
    output["insight_note"] = output.apply(
        lambda row: size_note(
            clean_text(row["demand_name"]),
            row["size_tier"],
            lower_text(row.get("trend")) or "unknown",
            row.get("best_rank"),
            row.get("active_months"),
        ),
        axis=1,
    )
    output = output[DEMAND_SIZE_COLUMNS]
    return output.sort_values(
        ["size_tier", "best_rank"],
        key=lambda series: series.map(SIZE_ORDER) if series.name == "size_tier" else series,
        na_position="last",
    ).reset_index(drop=True)


def build_segment_size_map(segments: pd.DataFrame) -> pd.DataFrame:
    output = segments.copy()
    output["size_tier"] = output.apply(segment_size_tier, axis=1)
    output["insight_note"] = output.apply(
        lambda row: size_note(
            clean_text(row["segment_name"]),
            row["size_tier"],
            lower_text(row.get("trend")) or "unknown",
            row.get("best_rank"),
            row.get("active_months"),
        ),
        axis=1,
    )
    output = output[SEGMENT_SIZE_COLUMNS]
    return output.sort_values(
        ["size_tier", "best_rank"],
        key=lambda series: series.map(SIZE_ORDER) if series.name == "size_tier" else series,
        na_position="last",
    ).reset_index(drop=True)


def global_month_range(intent_summary: pd.DataFrame) -> tuple[str, str]:
    first_values = intent_summary["first_month"].dropna().astype(str)
    last_values = intent_summary["last_month"].dropna().astype(str)
    first_month = first_values.min() if not first_values.empty else ""
    last_month = last_values.max() if not last_values.empty else ""
    return first_month, last_month


def seasonal_terms(row: pd.Series, name_columns: list[str]) -> str:
    values = [
        row.get("intent"),
        row.get("holiday"),
        row.get("occasion"),
        row.get("trend"),
        *[row.get(column) for column in name_columns],
    ]
    return " ".join(lower_text(value) for value in values if clean_text(value))


def seasonality_marker(text: str) -> str:
    for marker in [*Q4_PEAK_MONTHS.keys(), *HOLIDAY_PEAK_MONTHS.keys()]:
        if marker in text:
            return marker
    return ""


def classify_seasonality(row: pd.Series, name_columns: list[str]) -> tuple[str, str, str, str]:
    text = seasonal_terms(row, name_columns)
    marker = seasonality_marker(text)
    trend = lower_text(row.get("trend"))
    active_months = numeric(row.get("active_months"), 0.0)

    if active_months < 2:
        return (
            "Insufficient Data",
            "",
            "Not enough active months to classify seasonality confidently.",
            "Collect more monthly data before prioritizing research.",
        )
    if marker in Q4_PEAK_MONTHS:
        return (
            "Q4 Seasonal",
            Q4_PEAK_MONTHS[marker],
            f"Seasonal marker '{marker}' suggests Q4 demand behavior.",
            SEASONAL_RESEARCH_START[marker],
        )
    if marker in HOLIDAY_PEAK_MONTHS:
        return (
            "Holiday Seasonal",
            HOLIDAY_PEAK_MONTHS[marker],
            f"Seasonal marker '{marker}' suggests holiday or event-driven demand.",
            SEASONAL_RESEARCH_START[marker],
        )
    if trend == "emerging":
        return (
            "Emerging",
            "",
            "Demand appears late or early in the observed import window.",
            "Review now and re-check after the next ABA import.",
        )
    if trend == "declining":
        return (
            "Declining",
            "",
            "Rank trend is weakening across the observed import window.",
            "Validate current market relevance before assigning research.",
        )
    return (
        "Evergreen",
        "",
        "No explicit holiday marker; demand can be researched outside a seasonal window.",
        "Research anytime; prioritize rank strength and product fit.",
    )


def seasonality_rows(
    frame: pd.DataFrame,
    entity_type: str,
    id_column: str,
    name_column: str,
    first_month: str,
    last_month: str,
) -> list[dict[str, object]]:
    rows = []
    for _, row in frame.iterrows():
        seasonality_type, peak_month, note, recommendation = classify_seasonality(
            row,
            [name_column, "parent_demand"],
        )
        rows.append(
            {
                "entity_type": entity_type,
                "entity_id": row.get(id_column),
                "entity_name": row.get(name_column),
                "start_month": first_month,
                "peak_month": peak_month,
                "last_month": last_month,
                "active_months": row.get("active_months"),
                "seasonality_type": seasonality_type,
                "seasonality_note": note,
                "research_start_recommendation": recommendation,
            }
        )
    return rows


def build_seasonality_map(
    demand_size: pd.DataFrame,
    segment_size: pd.DataFrame,
    opportunities: pd.DataFrame,
    intent_summary: pd.DataFrame,
) -> pd.DataFrame:
    first_month, last_month = global_month_range(intent_summary)
    rows = []
    rows.extend(seasonality_rows(demand_size, "Demand", "demand_id", "demand_name", first_month, last_month))
    rows.extend(seasonality_rows(segment_size, "Segment", "segment_id", "segment_name", first_month, last_month))
    rows.extend(
        seasonality_rows(
            opportunities,
            "Opportunity",
            "opportunity_id",
            "demand_name",
            first_month,
            last_month,
        )
    )
    return pd.DataFrame(rows, columns=SEASONALITY_COLUMNS)


def growth_signal(row: pd.Series) -> tuple[str, str, str]:
    trend = lower_text(row.get("trend")) or "unknown"
    active_months = int(numeric(row.get("active_months"), 0.0))
    best_rank = numeric(row.get("best_rank"), 9_999_999.0)

    if trend == "growing" and active_months >= 3 and best_rank <= 25_000:
        return (
            "Strong Growth",
            "Positive",
            "Rank trend is improving and the entity has a strong best-rank signal.",
        )
    if trend == "growing":
        return ("Growing", "Positive", "Rank trend is improving across the observed months.")
    if trend == "emerging":
        return ("Emerging", "Early Positive", "Entity appears late in the observed window.")
    if trend == "declining":
        return ("Declining", "Negative", "Rank trend is weakening; validate before research.")
    if trend == "stable":
        return ("Stable", "Neutral", "Rank trend is stable in the available evidence.")
    return ("Unknown", "Unknown", "Growth signal is not available from current exports.")


def growth_rows(frame: pd.DataFrame, entity_type: str, id_column: str, name_column: str) -> list[dict[str, object]]:
    rows = []
    for _, row in frame.iterrows():
        signal, momentum, note = growth_signal(row)
        rows.append(
            {
                "entity_type": entity_type,
                "entity_id": row.get(id_column),
                "entity_name": row.get(name_column),
                "trend": lower_text(row.get("trend")) or "unknown",
                "growth_signal": signal,
                "rank_momentum": momentum,
                "active_months": row.get("active_months"),
                "growth_note": note,
            }
        )
    return rows


def build_growth_map(
    demand_size: pd.DataFrame,
    segment_size: pd.DataFrame,
    opportunities: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    rows.extend(growth_rows(demand_size, "Demand", "demand_id", "demand_name"))
    rows.extend(growth_rows(segment_size, "Segment", "segment_id", "segment_name"))
    rows.extend(growth_rows(opportunities, "Opportunity", "opportunity_id", "demand_name"))
    return pd.DataFrame(rows, columns=GROWTH_COLUMNS)


def direction_type(row: pd.Series) -> str:
    trend = lower_text(row.get("trend"))
    text = seasonal_terms(row, ["segment_name", "parent_demand"])
    if trend == "emerging":
        return "Emerging Segment"
    if seasonality_marker(text):
        return "Seasonal Segment"
    if clean_text(row.get("lifestyle")):
        return "Lifestyle Segment"
    if clean_text(row.get("pet")):
        return "Pet Segment"
    if clean_text(row.get("interest")):
        return "Interest Segment"
    if clean_text(row.get("theme")):
        return "Theme Segment"
    return "Core Segment"


def direction_note(row: pd.Series) -> str:
    direction = row["direction_type"]
    segment = clean_text(row.get("segment_name"))
    parent = clean_text(row.get("parent_demand"))
    if direction == "Seasonal Segment":
        return f"{segment} is a seasonal direction under {parent}; validate timing and seasonal design windows."
    if direction == "Emerging Segment":
        return f"{segment} is emerging; monitor the next import before deep research."
    if direction == "Lifestyle Segment":
        return f"{segment} adds lifestyle context to {parent}; evaluate audience language and product fit."
    if direction == "Pet Segment":
        return f"{segment} adds pet identity to {parent}; review emotional and memorial angles."
    if direction == "Interest Segment":
        return f"{segment} adds an interest niche to {parent}; research designs and product formats."
    if direction == "Theme Segment":
        return f"{segment} adds a theme to {parent}; validate visual style and message fit."
    return f"{segment} is a core specialization of {parent}; use as a baseline research candidate."


def build_niche_direction_map(segments: pd.DataFrame, segment_size: pd.DataFrame) -> pd.DataFrame:
    size_lookup = segment_size[["segment_id", "size_tier"]].copy()
    output = segments.merge(size_lookup, on="segment_id", how="left")
    output["direction_type"] = output.apply(direction_type, axis=1)
    output["potential_direction_note"] = output.apply(direction_note, axis=1)
    output = output[
        [
            "parent_demand",
            "segment_name",
            "direction_type",
            "size_tier",
            "trend",
            "best_rank",
            "segment_strength",
            "potential_direction_note",
        ]
    ]
    return output.sort_values(
        ["size_tier", "best_rank", "segment_strength"],
        ascending=[True, True, False],
        key=lambda series: series.map(SIZE_ORDER) if series.name == "size_tier" else series,
        na_position="last",
    ).reset_index(drop=True)


def research_action(size_tier: str, trend: str, seasonality_type: str) -> str:
    if seasonality_type in {"Q4 Seasonal", "Holiday Seasonal"}:
        return "Plan seasonal research and validate timing before product work."
    if trend == "declining":
        return "Validate demand quality before assigning research."
    if trend == "emerging":
        return "Monitor next import and collect supporting evidence."
    if size_tier in {"Mega", "Large"}:
        return "Prioritize for near-term MRnD research."
    if size_tier == "Mid":
        return "Queue for research after higher-strength opportunities."
    return "Keep on watchlist until rank signal improves."


def queue_score(size_tier: str, trend: str, seasonality_type: str, best_rank: object, strength: object) -> float:
    seasonal_bonus = 10.0 if seasonality_type in {"Q4 Seasonal", "Holiday Seasonal"} else 0.0
    return (
        SIZE_SCORE.get(size_tier, 20.0) * 0.35
        + numeric(strength) * 0.35
        + rank_score(best_rank) * 0.15
        + TREND_SCORE.get(trend, 0.0)
        + seasonal_bonus
    )


def build_research_opportunity_queue(
    demand_size: pd.DataFrame,
    segment_size: pd.DataFrame,
    seasonality: pd.DataFrame,
    opportunities: pd.DataFrame,
    niche_direction: pd.DataFrame,
) -> pd.DataFrame:
    seasonality_lookup = seasonality[["entity_type", "entity_id", "seasonality_type"]].copy()
    rows = []

    demand_lookup = demand_size.set_index("demand_id")
    for _, opportunity in opportunities.iterrows():
        demand_id = opportunity.get("demand_id")
        if demand_id not in demand_lookup.index:
            continue
        demand_row = demand_lookup.loc[demand_id]
        seasonality_row = seasonality_lookup[
            (seasonality_lookup["entity_type"] == "Opportunity")
            & (seasonality_lookup["entity_id"] == opportunity.get("opportunity_id"))
        ]
        seasonality_type = (
            seasonality_row["seasonality_type"].iloc[0]
            if not seasonality_row.empty
            else "Evergreen"
        )
        size_tier = demand_row["size_tier"]
        trend = lower_text(opportunity.get("trend")) or lower_text(demand_row.get("trend")) or "unknown"
        strength = numeric(opportunity.get("opportunity_score"), numeric(demand_row.get("strength_score")))
        rows.append(
            {
                "opportunity_type": "Demand Opportunity",
                "parent_demand": opportunity.get("demand_name"),
                "segment_name": "",
                "size_tier": size_tier,
                "trend": trend,
                "seasonality_type": seasonality_type,
                "best_rank": opportunity.get("best_rank"),
                "strength_score": round(strength, 2),
                "reason": (
                    f"{opportunity.get('demand_name')} is a {size_tier.lower()} demand "
                    f"with {trend} trend and opportunity score {round(strength, 2)}."
                ),
                "recommended_action": research_action(size_tier, trend, seasonality_type),
                "_sort_score": queue_score(
                    size_tier,
                    trend,
                    seasonality_type,
                    opportunity.get("best_rank"),
                    strength,
                ),
            }
        )

    segment_lookup = segment_size.set_index("segment_id")
    direction_lookup = niche_direction.set_index("segment_name") if not niche_direction.empty else pd.DataFrame()
    for _, segment in segment_size.iterrows():
        segment_id = segment.get("segment_id")
        seasonality_row = seasonality_lookup[
            (seasonality_lookup["entity_type"] == "Segment")
            & (seasonality_lookup["entity_id"] == segment_id)
        ]
        seasonality_type = (
            seasonality_row["seasonality_type"].iloc[0]
            if not seasonality_row.empty
            else "Evergreen"
        )
        size_tier = segment["size_tier"]
        trend = lower_text(segment.get("trend")) or "unknown"
        strength = numeric(segment.get("segment_strength"))
        segment_name = segment.get("segment_name")
        direction = "Segment Opportunity"
        if isinstance(direction_lookup, pd.DataFrame) and not direction_lookup.empty and segment_name in direction_lookup.index:
            direction = direction_lookup.loc[segment_name]["direction_type"]
        rows.append(
            {
                "opportunity_type": direction,
                "parent_demand": segment.get("parent_demand"),
                "segment_name": segment_name,
                "size_tier": size_tier,
                "trend": trend,
                "seasonality_type": seasonality_type,
                "best_rank": segment.get("best_rank"),
                "strength_score": round(strength, 2),
                "reason": (
                    f"{segment_name} is a {size_tier.lower()} segment under "
                    f"{segment.get('parent_demand')} with {trend} trend."
                ),
                "recommended_action": research_action(size_tier, trend, seasonality_type),
                "_sort_score": queue_score(
                    size_tier,
                    trend,
                    seasonality_type,
                    segment.get("best_rank"),
                    strength,
                ),
            }
        )

    output = pd.DataFrame(rows)
    if output.empty:
        return pd.DataFrame(columns=RESEARCH_QUEUE_COLUMNS)

    output = output.sort_values(
        ["_sort_score", "best_rank"],
        ascending=[False, True],
        na_position="last",
    ).reset_index(drop=True)
    output.insert(0, "priority_rank", range(1, len(output) + 1))
    return output[RESEARCH_QUEUE_COLUMNS]


def write_csv(frame: pd.DataFrame, output_dir: Path, file_key: str) -> None:
    output_path = output_dir / OUTPUT_FILES[file_key]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_path, index=False)
    logger.info("Exported %s with %s rows", display_path(output_path), f"{len(frame):,}")


def build_insight_layer(output_dir: Path, rebuild: bool) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    ensure_rebuild_allowed(output_dir, rebuild)
    if rebuild:
        remove_existing_outputs(output_dir)

    composite_demands = read_required_csv("composite_demands")
    demand_strength = read_required_csv("demand_strength_v3")
    segments = read_required_csv("demand_segments")
    opportunities = read_required_csv("opportunity_master")
    intent_summary = read_required_csv("intent_summary")

    # composite_demands is validated as the canonical demand export; V1 sizing uses the
    # rank-based strength export as the metric source.
    logger.info("Validated canonical demand export with %s rows", f"{len(composite_demands):,}")

    demand_size = build_demand_size_map(demand_strength)
    segment_size = build_segment_size_map(segments)
    seasonality = build_seasonality_map(demand_size, segment_size, opportunities, intent_summary)
    growth = build_growth_map(demand_size, segment_size, opportunities)
    niche_direction = build_niche_direction_map(segments, segment_size)
    research_queue = build_research_opportunity_queue(
        demand_size,
        segment_size,
        seasonality,
        opportunities,
        niche_direction,
    )

    write_csv(demand_size, output_dir, "demand_size_map")
    write_csv(segment_size, output_dir, "segment_size_map")
    write_csv(seasonality, output_dir, "seasonality_map")
    write_csv(growth, output_dir, "growth_map")
    write_csv(niche_direction, output_dir, "niche_direction_map")
    write_csv(research_queue, output_dir, "research_opportunity_queue")

    logger.info("Insight Layer build complete")


def main() -> None:
    configure_logging()
    args = parse_args()
    logger.info("Starting Insight Layer build")
    build_insight_layer(output_dir=args.output_dir.resolve(), rebuild=args.rebuild)
    logger.info("Build log: %s", display_path(LOG_PATH))


if __name__ == "__main__":
    main()
