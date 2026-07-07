"""Build deterministic executive decision CSVs from market intelligence outputs."""

from __future__ import annotations

import argparse
import logging
import math
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "data" / "output" / "decision"
LOG_DIR = PROJECT_ROOT / "logs"
LOG_PATH = LOG_DIR / "build_decision_layer.log"

INPUT_PATHS = {
    "market_intelligence": PROJECT_ROOT
    / "data"
    / "output"
    / "intelligence"
    / "market_intelligence.csv",
    "expansion_tree": PROJECT_ROOT / "data" / "output" / "intelligence" / "expansion_tree.csv",
    "market_stage": PROJECT_ROOT / "data" / "output" / "intelligence" / "market_stage.csv",
    "demand_intelligence": PROJECT_ROOT
    / "data"
    / "output"
    / "intelligence"
    / "demand_intelligence.csv",
    "opportunity_master": PROJECT_ROOT
    / "data"
    / "output"
    / "opportunity"
    / "opportunity_master.csv",
    "demand_segments": PROJECT_ROOT
    / "data"
    / "output"
    / "demand_segments"
    / "demand_segments.csv",
    "demand_size_map": PROJECT_ROOT / "data" / "output" / "insights" / "demand_size_map.csv",
    "seasonality_map": PROJECT_ROOT / "data" / "output" / "insights" / "seasonality_map.csv",
}

OUTPUT_FILES = {
    "market_scorecard": "market_scorecard.csv",
    "research_candidates": "research_candidates.csv",
    "product_recommendation": "product_recommendation.csv",
    "customization_recommendation": "customization_recommendation.csv",
    "market_calendar": "market_calendar.csv",
}

REQUIRED_COLUMNS = {
    "market_intelligence": {
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
    },
    "expansion_tree": {"parent_demand", "child_segment", "relation_type", "segment_strength"},
    "market_stage": {"demand", "stage", "evidence", "recommendation"},
    "demand_intelligence": {"demand_id", "demand_name", "overall_score", "recommended_strategy"},
    "opportunity_master": {"demand_id", "demand_name", "opportunity_score", "priority", "best_rank"},
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
        "best_rank",
        "segment_strength",
    },
    "demand_size_map": {
        "demand_id",
        "demand_name",
        "best_rank",
        "trend",
        "active_months",
        "size_tier",
    },
    "seasonality_map": {
        "entity_type",
        "entity_id",
        "entity_name",
        "seasonality_type",
        "peak_month",
    },
}

MARKET_SCORECARD_COLUMNS = [
    "demand_id",
    "demand_name",
    "market_size",
    "growth_stage",
    "competition_level",
    "expansion_score",
    "seasonality",
    "maturity",
    "overall_score",
    "research_priority",
    "recommended_action",
]

SEGMENT_METADATA_COLUMNS = [
    "segment_signature",
    "segment_refinements",
    "primary_segment_type",
    "primary_segment_value",
]

RESEARCH_CANDIDATE_COLUMNS = [
    "priority",
    "parent_demand",
    "child_segment",
    *SEGMENT_METADATA_COLUMNS,
    "reason",
    "opportunity_score",
    "estimated_roi",
    "suggested_products",
    "suggested_customizations",
    "next_action",
]

PRODUCT_RECOMMENDATION_COLUMNS = [
    "child_segment",
    "recommended_product",
    "confidence",
    "reason",
]

CUSTOMIZATION_RECOMMENDATION_COLUMNS = [
    "child_segment",
    "customization",
    "confidence",
    "reason",
]

MARKET_CALENDAR_COLUMNS = [
    "demand",
    "research_month",
    "listing_month",
    "ads_month",
    "peak_month",
    "explanation",
]

SIZE_SCORE = {"Mega": 100.0, "Large": 82.0, "Mid": 62.0, "Small": 42.0, "Micro": 22.0}
TREND_SCORE = {
    "growing": 90.0,
    "emerging": 82.0,
    "stable": 62.0,
    "declining": 25.0,
}
SEASONALITY_SCORE = {
    "Evergreen": 72.0,
    "Q4 Seasonal": 88.0,
    "Holiday Seasonal": 80.0,
    "Emerging": 72.0,
    "Declining": 30.0,
    "Insufficient Data": 25.0,
}
PRIORITY_ORDER = {"P1": 1, "P2": 2, "P3": 3, "Watchlist": 4}
ROI_ORDER = {"High": 1, "Medium-High": 2, "Medium": 3, "Low": 4, "Unproven": 5}

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build deterministic executive decision CSVs from market intelligence outputs."
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Replace existing Decision Layer CSVs.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help="Folder for Decision Layer CSV outputs.",
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
        raise RuntimeError(f"Decision CSVs already exist. Rerun with --rebuild to replace: {names}")


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


def priority_from_score(score: float) -> str:
    if score >= 78:
        return "P1"
    if score >= 64:
        return "P2"
    if score >= 50:
        return "P3"
    return "Watchlist"


def recommended_action(
    priority: str,
    seasonality: str,
    maturity: str,
    market_size: str,
    growth_stage: str,
    expansion_score: float,
    overall_score: float,
) -> str:
    if seasonality in {"Q4 Seasonal", "Holiday Seasonal"} and priority in {"P1", "P2", "P3"}:
        return "Seasonal Preparation"
    if priority == "P1" or overall_score >= 78:
        return "Research Immediately"
    if expansion_score >= 65 and market_size in {"Mega", "Large", "Mid"}:
        return "Expand Existing Portfolio"
    if growth_stage == "Declining" and market_size in {"Small", "Micro"}:
        return "Archive"
    if maturity in {"Mature / Declining"} and overall_score < 45:
        return "Archive"
    return "Monitor"


def scorecard_reason(row: pd.Series) -> str:
    return (
        f"{row['market_size']} demand, {row['growth_stage'].lower()} growth stage, "
        f"{row['maturity'].lower()} maturity, expansion score {round(numeric(row['expansion_score']), 1)}."
    )


def build_market_scorecard(
    market_intelligence: pd.DataFrame,
    demand_size_map: pd.DataFrame,
) -> pd.DataFrame:
    scorecard = market_intelligence.merge(
        demand_size_map[["demand_id", "best_rank", "trend", "active_months"]],
        on="demand_id",
        how="left",
    )
    scorecard["seasonality"] = scorecard["seasonality_type"]
    scorecard["maturity"] = scorecard["market_stage"]
    scorecard["overall_score"] = scorecard.apply(
        lambda row: round(
            SIZE_SCORE.get(clean_text(row["market_size"]), 20.0) * 0.25
            + rank_score(row.get("best_rank")) * 0.25
            + TREND_SCORE.get(lower_text(row.get("trend")), 45.0) * 0.15
            + numeric(row.get("expansion_score")) * 0.20
            + SEASONALITY_SCORE.get(clean_text(row.get("seasonality")), 45.0) * 0.15,
            2,
        ),
        axis=1,
    )
    scorecard["research_priority"] = scorecard["overall_score"].apply(priority_from_score)
    scorecard["recommended_action"] = scorecard.apply(
        lambda row: recommended_action(
            clean_text(row["research_priority"]),
            clean_text(row["seasonality"]),
            clean_text(row["maturity"]),
            clean_text(row["market_size"]),
            clean_text(row["growth_stage"]),
            numeric(row["expansion_score"]),
            numeric(row["overall_score"]),
        ),
        axis=1,
    )
    scorecard = scorecard.sort_values(
        ["overall_score", "expansion_score", "demand_id"],
        ascending=[False, False, True],
        na_position="last",
    ).drop_duplicates("demand_name", keep="first")
    output = scorecard[MARKET_SCORECARD_COLUMNS].copy()
    return output.sort_values(
        ["research_priority", "overall_score", "expansion_score", "demand_name"],
        ascending=[True, False, False, True],
        key=lambda series: series.map(PRIORITY_ORDER) if series.name == "research_priority" else series,
        na_position="last",
    ).reset_index(drop=True)


def product_rules(segment: pd.Series) -> list[tuple[str, str, str]]:
    text = " ".join(
        lower_text(segment.get(column))
        for column in [
            "segment_name",
            "interest",
            "pet",
            "profession",
            "holiday",
            "occasion",
            "theme",
            "lifestyle",
        ]
    )
    recommendations: list[tuple[str, str, str]] = []

    def add(product: str, confidence: str, reason: str) -> None:
        if product not in [item[0] for item in recommendations]:
            recommendations.append((product, confidence, reason))

    if any(term in text for term in ["fishing", "hunting", "camping", "golf", "soccer", "gaming"]):
        add("Tumbler", "High", "Interest-led segments work well on practical drinkware.")
        add("Mug", "High", "Interest phrases are short enough for repeatable mug designs.")
        add("Blanket", "Medium", "Giftable niche designs can scale into cozy home products.")
    if any(term in text for term in ["coffee", "book lover", "reading", "teacher", "nurse"]):
        add("Mug", "High", "Profession and hobby segments have strong everyday-use fit.")
        add("Tumbler", "High", "Reusable drinkware supports names and simple icon systems.")
        add("Tote Bag", "Medium", "Functional carry products fit teacher, reader, and work niches.")
    if any(term in text for term in ["dog", "cat", "pet", "memorial"]):
        add("Blanket", "High", "Pet and memorial segments support emotional gift products.")
        add("Ornament", "Medium", "Pet identity and memorial designs fit seasonal keepsakes.")
        add("Mug", "Medium", "Pet-parent identity works on repeatable drinkware formats.")
    if any(term in text for term in ["christmas", "halloween", "thanksgiving"]):
        add("Ornament", "High", "Holiday segments fit keepsake and seasonal tree decor.")
        add("Mug", "Medium", "Holiday gift phrases can scale into drinkware.")
        add("Blanket", "Medium", "Seasonal family gifting can support cozy products.")
    if any(term in text for term in ["floral", "flower", "boho", "vintage", "funny"]):
        add("Poster", "Medium", "Theme-led designs can be tested as wall decor.")
        add("Mug", "Medium", "Visual themes transfer cleanly to drinkware.")
        add("Blanket", "Medium", "Style-led themes can work on larger print surfaces.")

    if not recommendations:
        add("Mug", "Medium", "Default POD gift format for short demand phrases.")
        add("Tumbler", "Medium", "Default practical product for personalized gift niches.")
        add("Blanket", "Low", "Use as a validation product when the emotional angle is clear.")

    return recommendations[:3]


def customization_rules(segment: pd.Series) -> list[tuple[str, str, str]]:
    text = " ".join(
        lower_text(segment.get(column))
        for column in [
            "segment_name",
            "interest",
            "pet",
            "profession",
            "holiday",
            "occasion",
            "theme",
            "lifestyle",
        ]
    )
    recommendations: list[tuple[str, str, str]] = []

    def add(customization: str, confidence: str, reason: str) -> None:
        if customization not in [item[0] for item in recommendations]:
            recommendations.append((customization, confidence, reason))

    add("Name", "High", "Name personalization is broadly applicable across gift segments.")
    if any(term in text for term in ["dog", "cat", "pet", "memorial"]):
        add("Photo", "High", "Pet and memorial demand benefits from photo-based personalization.")
        add("Line Art", "Medium", "Pet and memorial photos can be converted into clean line-art styles.")
    if any(term in text for term in ["mom", "dad", "grandma", "grandpa", "family", "kids"]):
        add("Multiple Kids", "Medium", "Family recipient segments often need multiple-name personalization.")
        add("Photo", "Medium", "Family gifting can support photo-based keepsakes.")
    if any(term in text for term in ["floral", "flower", "birthday", "mother"]):
        add("Birth Flower", "Medium", "Floral and birthday demand can support birth-flower variants.")
    if any(term in text for term in ["fishing", "camping", "hunting", "golf", "teacher", "nurse", "coffee"]):
        add("Clipart", "Medium", "Interest and profession segments benefit from reusable icon systems.")
    if any(term in text for term in ["funny", "vintage", "boho", "minimalist"]):
        add("Hand Drawing", "Low", "Style-led segments may justify drawn artwork variants.")

    return recommendations[:3]


def build_product_recommendation(segments: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, segment in segments.iterrows():
        for product, confidence, reason in product_rules(segment):
            rows.append(
                {
                    "child_segment": segment["segment_name"],
                    "recommended_product": product,
                    "confidence": confidence,
                    "reason": reason,
                }
            )
    return pd.DataFrame(rows, columns=PRODUCT_RECOMMENDATION_COLUMNS)


def build_customization_recommendation(segments: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, segment in segments.iterrows():
        for customization, confidence, reason in customization_rules(segment):
            rows.append(
                {
                    "child_segment": segment["segment_name"],
                    "customization": customization,
                    "confidence": confidence,
                    "reason": reason,
                }
            )
    return pd.DataFrame(rows, columns=CUSTOMIZATION_RECOMMENDATION_COLUMNS)


def recommended_values_from_rules(values: list[tuple[str, str, str]]) -> str:
    return " | ".join(value for value, _, _ in values[:3])


def segment_metadata(segment: pd.Series) -> dict[str, str]:
    return {column: clean_text(segment.get(column)) for column in SEGMENT_METADATA_COLUMNS}


def candidate_priority(parent_priority: str, segment_strength: float, opportunity_score: float) -> str:
    if parent_priority == "P1" and (segment_strength >= 25 or opportunity_score >= 75):
        return "P1"
    if parent_priority in {"P1", "P2"} and (segment_strength >= 18 or opportunity_score >= 60):
        return "P2"
    if parent_priority in {"P1", "P2", "P3"}:
        return "P3"
    return "Watchlist"


def estimated_roi(priority: str, opportunity_score: float, segment_strength: float) -> str:
    if priority == "P1" and opportunity_score >= 70 and segment_strength >= 25:
        return "High"
    if priority in {"P1", "P2"} and (opportunity_score >= 55 or segment_strength >= 20):
        return "Medium-High"
    if priority in {"P2", "P3"}:
        return "Medium"
    if priority == "Watchlist":
        return "Low"
    return "Unproven"


def build_research_candidates(
    market_scorecard: pd.DataFrame,
    segments: pd.DataFrame,
    opportunities: pd.DataFrame,
) -> pd.DataFrame:
    parent_lookup = market_scorecard.set_index("demand_name")
    opportunity_lookup = opportunities.groupby("demand_name")["opportunity_score"].max().to_dict()

    rows = []
    for _, segment in segments.iterrows():
        parent_demand = clean_text(segment["parent_demand"])
        if parent_demand not in parent_lookup.index:
            continue
        parent = parent_lookup.loc[parent_demand]
        opportunity_score = round(
            numeric(opportunity_lookup.get(parent_demand), 0.0) * 0.60
            + numeric(segment.get("segment_strength")) * 1.20,
            2,
        )
        priority = candidate_priority(
            clean_text(parent["research_priority"]),
            numeric(segment.get("segment_strength")),
            opportunity_score,
        )
        child_segment = clean_text(segment["segment_name"])
        products = recommended_values_from_rules(product_rules(segment))
        customizations = recommended_values_from_rules(customization_rules(segment))
        rows.append(
            {
                "priority": priority,
                "parent_demand": parent_demand,
                "child_segment": child_segment,
                **segment_metadata(segment),
                "reason": (
                    f"{child_segment} inherits {parent['market_size']} parent demand "
                    f"with segment strength {round(numeric(segment.get('segment_strength')), 2)}."
                ),
                "opportunity_score": opportunity_score,
                "estimated_roi": estimated_roi(
                    priority,
                    opportunity_score,
                    numeric(segment.get("segment_strength")),
                ),
                "suggested_products": products,
                "suggested_customizations": customizations,
                "next_action": (
                    "Create design/product tests for the top suggested products."
                    if priority in {"P1", "P2"}
                    else "Validate search language and evidence before product testing."
                ),
            }
        )

    output = pd.DataFrame(rows, columns=RESEARCH_CANDIDATE_COLUMNS)
    return output.sort_values(
        ["priority", "opportunity_score", "child_segment"],
        ascending=[True, False, True],
        key=lambda series: series.map(PRIORITY_ORDER) if series.name == "priority" else series,
        na_position="last",
    ).reset_index(drop=True)


def calendar_rule(demand: str, seasonality: str, peak_month: str) -> tuple[str, str, str, str, str]:
    demand_text = lower_text(demand)
    peak = clean_text(peak_month)
    if "christmas" in demand_text or seasonality == "Q4 Seasonal":
        return (
            "August",
            "September",
            "October",
            peak or "November",
            "Q4 demand needs products live before peak holiday browsing.",
        )
    if "halloween" in demand_text:
        return ("June", "July", "August", peak or "September", "Halloween demand should be prepared before October.")
    if "mother" in demand_text or "mom" in demand_text and seasonality == "Holiday Seasonal":
        return ("February", "March", "April", peak or "May", "Mother's Day demand peaks in spring.")
    if "father" in demand_text or "dad" in demand_text and seasonality == "Holiday Seasonal":
        return ("March", "April", "May", peak or "June", "Father's Day demand peaks in early summer.")
    if seasonality == "Holiday Seasonal":
        return (
            "Three months before peak",
            "Two months before peak",
            "One month before peak",
            peak or "Event Month",
            "Holiday and occasion demand requires pre-peak preparation.",
        )
    if seasonality in {"Emerging", "Insufficient Data"}:
        return (
            "Next Import",
            "After Validation",
            "After Listing",
            peak or "Unproven",
            "Timing is not reliable yet; validate after more evidence.",
        )
    return (
        "Any Month",
        "Rolling",
        "Always-on",
        peak or "Evergreen",
        "Evergreen demand can be researched and launched outside a fixed seasonal window.",
    )


def demand_peak_month(demand_id: str, seasonality_map: pd.DataFrame) -> str:
    rows = seasonality_map[
        (seasonality_map["entity_type"] == "Demand")
        & (seasonality_map["entity_id"].astype(str) == str(demand_id))
    ]
    if rows.empty or "peak_month" not in rows.columns:
        return ""
    values = rows["peak_month"].dropna().astype(str)
    return values.iloc[0] if not values.empty else ""


def build_market_calendar(market_scorecard: pd.DataFrame, seasonality_map: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, scorecard in market_scorecard.iterrows():
        peak_month = demand_peak_month(clean_text(scorecard["demand_id"]), seasonality_map)
        research_month, listing_month, ads_month, peak, explanation = calendar_rule(
            clean_text(scorecard["demand_name"]),
            clean_text(scorecard["seasonality"]),
            peak_month,
        )
        rows.append(
            {
                "demand": scorecard["demand_name"],
                "research_month": research_month,
                "listing_month": listing_month,
                "ads_month": ads_month,
                "peak_month": peak,
                "explanation": explanation,
            }
        )
    return pd.DataFrame(rows, columns=MARKET_CALENDAR_COLUMNS)


def write_csv(frame: pd.DataFrame, output_dir: Path, file_key: str) -> None:
    output_path = output_dir / OUTPUT_FILES[file_key]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_path, index=False)
    logger.info("Exported %s with %s rows", display_path(output_path), f"{len(frame):,}")


def print_top_sections(
    research_candidates: pd.DataFrame,
    market_scorecard: pd.DataFrame,
    product_recommendations: pd.DataFrame,
) -> None:
    print("\nTop 20 Research Candidates")
    print(
        research_candidates.head(20)[
            ["priority", "parent_demand", "child_segment", "opportunity_score", "estimated_roi"]
        ].to_string(index=False)
    )
    print("\nTop 20 Market Scorecards")
    print(
        market_scorecard.head(20)[
            ["demand_name", "market_size", "growth_stage", "overall_score", "research_priority", "recommended_action"]
        ].to_string(index=False)
    )
    print("\nTop Product Recommendations")
    print(product_recommendations.head(20).to_string(index=False))


def build_decision_layer(output_dir: Path, rebuild: bool) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    ensure_rebuild_allowed(output_dir, rebuild)
    if rebuild:
        remove_existing_outputs(output_dir)

    market_intelligence = read_required_csv("market_intelligence")
    expansion_tree = read_required_csv("expansion_tree")
    market_stage = read_required_csv("market_stage")
    demand_intelligence = read_required_csv("demand_intelligence")
    opportunities = read_required_csv("opportunity_master")
    segments = read_required_csv("demand_segments")
    demand_size_map = read_required_csv("demand_size_map")
    seasonality_map = read_required_csv("seasonality_map")

    logger.info("Validated market stage with %s rows", f"{len(market_stage):,}")
    logger.info("Validated demand intelligence with %s rows", f"{len(demand_intelligence):,}")
    logger.info("Validated expansion tree with %s rows", f"{len(expansion_tree):,}")

    market_scorecard = build_market_scorecard(market_intelligence, demand_size_map)
    product_recommendations = build_product_recommendation(segments)
    customization_recommendations = build_customization_recommendation(segments)
    research_candidates = build_research_candidates(
        market_scorecard,
        segments,
        opportunities,
    )
    market_calendar = build_market_calendar(market_scorecard, seasonality_map)

    write_csv(market_scorecard, output_dir, "market_scorecard")
    write_csv(research_candidates, output_dir, "research_candidates")
    write_csv(product_recommendations, output_dir, "product_recommendation")
    write_csv(customization_recommendations, output_dir, "customization_recommendation")
    write_csv(market_calendar, output_dir, "market_calendar")

    print_top_sections(research_candidates, market_scorecard, product_recommendations)
    logger.info("Decision Layer build complete")


def main() -> None:
    configure_logging()
    args = parse_args()
    logger.info("Starting Decision Layer build")
    build_decision_layer(output_dir=args.output_dir.resolve(), rebuild=args.rebuild)
    logger.info("Build log: %s", display_path(LOG_PATH))


if __name__ == "__main__":
    main()
