"""Build transparent opportunity scoring outputs from existing CSV layers."""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "output" / "scoring"

INPUT_PATHS = {
    "segments": PROJECT_ROOT / "data" / "output" / "demand_segments" / "demand_segments.csv",
    "market_scorecard": PROJECT_ROOT / "data" / "output" / "decision" / "market_scorecard.csv",
    "research_candidates": PROJECT_ROOT / "data" / "output" / "decision" / "research_candidates.csv",
    "product_recommendation": PROJECT_ROOT
    / "data"
    / "output"
    / "decision"
    / "product_recommendation.csv",
    "customization_recommendation": PROJECT_ROOT
    / "data"
    / "output"
    / "decision"
    / "customization_recommendation.csv",
}

REQUIRED_COLUMNS = {
    "segments": {
        "parent_demand",
        "segment_name",
        "intent",
        "recipient",
        "profession",
        "interest",
        "pet",
        "holiday",
        "occasion",
        "theme",
        "lifestyle",
        "keyword_count",
        "best_rank",
        "median_rank",
        "active_months",
        "trend",
        "segment_strength",
        "evidence_keywords",
    },
    "market_scorecard": {
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
    },
    "research_candidates": {
        "parent_demand",
        "child_segment",
        "opportunity_score",
        "estimated_roi",
        "suggested_products",
        "suggested_customizations",
    },
    "product_recommendation": {
        "child_segment",
        "recommended_product",
        "confidence",
    },
    "customization_recommendation": {
        "child_segment",
        "customization",
        "confidence",
    },
}

OUTPUT_FILES = {
    "opportunity_scorecard": "opportunity_scorecard.csv",
    "product_fit_matrix": "product_fit_matrix.csv",
    "customization_fit_matrix": "customization_fit_matrix.csv",
    "research_reasoning": "research_reasoning.csv",
}

OPPORTUNITY_COLUMNS = [
    "parent_demand",
    "child_segment",
    "market_size_score",
    "growth_score",
    "competition_score",
    "expansion_score",
    "seasonality_score",
    "product_fit_score",
    "total_score",
    "recommended_priority",
    "explanation",
]

PRODUCT_COLUMNS = [
    "child_segment",
    "segment_label_source",
    "canonical_evidence_phrase",
    "observed_products",
    "card_score",
    "blanket_score",
    "mug_score",
    "tumbler_score",
    "shirt_score",
    "ornament_score",
    "canvas_score",
    "best_product",
    "explanation",
]

CUSTOMIZATION_COLUMNS = [
    "child_segment",
    "segment_label_source",
    "canonical_evidence_phrase",
    "observed_products",
    "photo",
    "name",
    "multiple_names",
    "birth_flower",
    "clipart",
    "line_art",
    "hand_drawing",
    "best_customization",
    "explanation",
]

REASONING_COLUMNS = [
    "child_segment",
    "strengths",
    "weaknesses",
    "risks",
    "opportunities",
    "why_now",
    "recommended_next_step",
]

SIZE_BASE_SCORE = {
    "Mega": 96.0,
    "Large": 84.0,
    "Mid": 68.0,
    "Small": 46.0,
    "Micro": 26.0,
}

TREND_SCORE = {
    "growing": 90.0,
    "emerging": 82.0,
    "stable": 64.0,
    "declining": 28.0,
}

COMPETITION_OPPORTUNITY_SCORE = {
    "Low": 88.0,
    "Medium": 68.0,
    "High": 46.0,
    "Unknown": 56.0,
    "": 56.0,
}

SEASONALITY_SCORE = {
    "Evergreen": 78.0,
    "Q4 Seasonal": 84.0,
    "Holiday Seasonal": 82.0,
    "Emerging": 70.0,
    "Declining": 36.0,
    "Insufficient Data": 46.0,
    "": 50.0,
}

CONFIDENCE_POINTS = {
    "High": 18,
    "Medium": 10,
    "Low": 4,
}

MONTHS = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build transparent opportunity scoring CSVs from existing outputs.",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Overwrite scoring outputs in data/output/scoring/.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Output folder for scoring CSVs.",
    )
    return parser.parse_args()


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def clean_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    text = str(value).strip()
    if text.lower() == "nan":
        return ""
    return text


def lower_text(value: object) -> str:
    return clean_text(value).lower()


def numeric(value: object, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, value))


def rank_score(rank: object, max_rank: float = 1_500_000.0) -> float:
    rank_value = max(1.0, numeric(rank, max_rank))
    return round(clamp(100.0 - (math.log10(rank_value) / math.log10(max_rank)) * 100.0), 2)


def active_month_score(active_months: object) -> float:
    months = numeric(active_months)
    if months >= 6:
        return 100.0
    if months >= 4:
        return 86.0
    if months >= 3:
        return 70.0
    if months >= 2:
        return 52.0
    if months >= 1:
        return 34.0
    return 15.0


def priority_from_score(score: float) -> str:
    if score >= 90:
        return "★★★★★"
    if score >= 80:
        return "★★★★☆"
    if score >= 70:
        return "★★★☆☆"
    if score >= 60:
        return "★★☆☆☆"
    return "★☆☆☆☆"


def read_required_csv(name: str) -> pd.DataFrame:
    path = INPUT_PATHS[name]
    if not path.exists():
        raise FileNotFoundError(f"Missing required input: {display_path(path)}")
    frame = pd.read_csv(path)
    missing = REQUIRED_COLUMNS[name] - set(frame.columns)
    if missing:
        missing_list = ", ".join(sorted(missing))
        raise ValueError(f"{display_path(path)} missing required columns: {missing_list}")
    print(f"Loaded {display_path(path)}: {len(frame):,} rows")
    return frame


def ensure_rebuild_allowed(output_dir: Path, rebuild: bool) -> None:
    existing = [output_dir / filename for filename in OUTPUT_FILES.values() if (output_dir / filename).exists()]
    if existing and not rebuild:
        names = ", ".join(display_path(path) for path in existing)
        raise FileExistsError(f"Scoring outputs already exist. Use --rebuild to replace: {names}")


def remove_scoring_outputs(output_dir: Path) -> None:
    for filename in OUTPUT_FILES.values():
        path = output_dir / filename
        if path.exists():
            path.unlink()


def context_text(segment: pd.Series) -> str:
    fields = [
        "segment_name",
        "parent_demand",
        "intent",
        "recipient",
        "profession",
        "interest",
        "pet",
        "holiday",
        "occasion",
        "theme",
        "lifestyle",
        "evidence_keywords",
        "canonical_evidence_phrase",
        "observed_products",
    ]
    return " ".join(lower_text(segment.get(field)) for field in fields)


def has_any(text: str, terms: list[str]) -> bool:
    return any(term in text for term in terms)


def has_semantic_specificity(segment: pd.Series) -> bool:
    for column in ["interest", "profession", "pet", "holiday", "occasion", "theme", "lifestyle"]:
        if clean_text(segment.get(column)):
            return True
    return False


def segment_specificity_score(segment: pd.Series) -> float:
    columns = ["interest", "profession", "pet", "holiday", "occasion", "theme", "lifestyle"]
    filled = sum(1 for column in columns if clean_text(segment.get(column)))
    if filled >= 3:
        return 100.0
    if filled == 2:
        return 82.0
    if filled == 1:
        return 66.0
    return 42.0


def confidence_boosts(
    recommendations: pd.DataFrame,
    segment_name: str,
    item_column: str,
) -> dict[str, int]:
    matches = recommendations[recommendations["child_segment"] == segment_name]
    boosts: dict[str, int] = {}
    for _, row in matches.iterrows():
        item = lower_text(row.get(item_column)).replace(" ", "_")
        boosts[item] = boosts.get(item, 0) + CONFIDENCE_POINTS.get(clean_text(row.get("confidence")), 0)
    return boosts


def score_product_fit(
    segment: pd.Series,
    product_recommendations: pd.DataFrame,
) -> dict[str, object]:
    segment_name = clean_text(segment["segment_name"])
    text = context_text(segment)
    scores = {
        "card": 42,
        "blanket": 44,
        "mug": 48,
        "tumbler": 46,
        "shirt": 40,
        "ornament": 38,
        "canvas": 38,
    }
    reasons: list[str] = []

    if has_any(text, ["gift", "present"]):
        scores["card"] += 6
        scores["blanket"] += 8
        scores["mug"] += 8
        scores["tumbler"] += 6
        scores["ornament"] += 5
        reasons.append("gift-led demand supports common POD gift products")

    if has_any(text, ["christmas", "holiday", "halloween", "thanksgiving", "valentine"]):
        scores["ornament"] += 34
        scores["card"] += 12
        scores["blanket"] += 14
        scores["mug"] += 10
        scores["canvas"] += 7
        reasons.append("seasonal language increases keepsake and ornament fit")

    if has_any(text, ["card", "cards", "thank you", "thanks", "appreciation"]):
        scores["card"] += 34
        scores["mug"] += 6
        scores["canvas"] += 6
        reasons.append("observed card or thank-you language supports greeting-card formats")

    if has_any(text, ["mom", "dad", "grandma", "grandpa", "wife", "husband", "daughter", "son", "family"]):
        scores["blanket"] += 20
        scores["mug"] += 14
        scores["canvas"] += 10
        scores["ornament"] += 8
        reasons.append("family recipient language fits emotional keepsake products")

    if has_any(text, ["teacher", "nurse", "doctor", "coach", "boss", "coworker"]):
        scores["mug"] += 24
        scores["tumbler"] += 20
        scores["shirt"] += 8
        reasons.append("profession segments fit daily-use drinkware")

    if has_any(text, ["dog", "cat", "pet", "memorial", "in memory", "remembrance"]):
        scores["blanket"] += 25
        scores["ornament"] += 18
        scores["mug"] += 16
        scores["canvas"] += 14
        reasons.append("pet and memorial language supports photo and keepsake products")

    observed_products = lower_text(segment.get("observed_products"))
    if "card" in observed_products:
        scores["card"] += 26
    if "ornament" in observed_products:
        scores["ornament"] += 26
    if "canvas" in observed_products:
        scores["canvas"] += 22

    if has_any(text, ["fishing", "hunting", "camping", "golf", "soccer", "baseball", "gaming"]):
        scores["tumbler"] += 25
        scores["mug"] += 15
        scores["shirt"] += 15
        scores["blanket"] += 8
        reasons.append("hobby segments fit portable drinkware and apparel")

    if has_any(text, ["coffee", "wine"]):
        scores["mug"] += 28
        scores["tumbler"] += 20
        reasons.append("beverage identity has direct drinkware fit")

    if has_any(text, ["decor", "wall art", "poster", "canvas"]):
        scores["canvas"] += 34
        scores["ornament"] += 6
        reasons.append("decor intent strongly supports wall-art formats")

    if has_any(text, ["apparel", "shirt", "tee", "matching", "funny", "retro", "vintage"]):
        scores["shirt"] += 22
        scores["mug"] += 8
        scores["canvas"] += 8
        reasons.append("style and apparel wording supports shirts and simple print designs")

    for product, boost in confidence_boosts(product_recommendations, segment_name, "recommended_product").items():
        if product in scores:
            scores[product] += boost

    capped = {product: int(round(clamp(score))) for product, score in scores.items()}
    best_product = max(capped, key=lambda product: (capped[product], product))
    explanation = "; ".join(reasons[:3]) if reasons else "General gift language creates moderate product fit."
    return {
        "child_segment": segment_name,
        "segment_label_source": clean_text(segment.get("segment_label_source")) or "observed_phrase",
        "canonical_evidence_phrase": clean_text(segment.get("canonical_evidence_phrase")),
        "observed_products": clean_text(segment.get("observed_products")),
        "card_score": capped["card"],
        "blanket_score": capped["blanket"],
        "mug_score": capped["mug"],
        "tumbler_score": capped["tumbler"],
        "shirt_score": capped["shirt"],
        "ornament_score": capped["ornament"],
        "canvas_score": capped["canvas"],
        "best_product": best_product.title(),
        "explanation": explanation,
    }


def score_customization_fit(
    segment: pd.Series,
    customization_recommendations: pd.DataFrame,
) -> dict[str, object]:
    segment_name = clean_text(segment["segment_name"])
    text = context_text(segment)
    scores = {
        "photo": 35,
        "name": 64,
        "multiple_names": 34,
        "birth_flower": 28,
        "clipart": 44,
        "line_art": 35,
        "hand_drawing": 30,
    }
    reasons: list[str] = []

    if has_any(text, ["gift", "present", "personalized", "custom"]):
        scores["name"] += 16
        scores["clipart"] += 8
        reasons.append("gift and personalization wording supports name customization")

    if has_any(text, ["mom", "dad", "grandma", "grandpa", "wife", "husband", "family", "kids"]):
        scores["multiple_names"] += 25
        scores["photo"] += 12
        scores["line_art"] += 8
        reasons.append("family recipient segments often need names and family details")

    if has_any(text, ["dog", "cat", "pet", "memorial", "in memory", "remembrance"]):
        scores["photo"] += 30
        scores["line_art"] += 28
        scores["hand_drawing"] += 25
        scores["name"] += 10
        reasons.append("pet and memorial language supports photo and drawing customization")

    if has_any(text, ["floral", "flower", "birth flower", "birthday", "mother", "mom", "grandma", "girl"]):
        scores["birth_flower"] += 30
        reasons.append("floral or family gifting language supports birth-flower variants")

    if has_any(text, ["teacher", "nurse", "doctor", "coach", "fishing", "camping", "hunting", "golf", "soccer"]):
        scores["clipart"] += 25
        scores["name"] += 8
        reasons.append("profession and hobby segments fit simple clipart systems")

    if has_any(text, ["christmas", "halloween", "thanksgiving", "valentine", "holiday"]):
        scores["clipart"] += 18
        scores["name"] += 10
        reasons.append("seasonal segments support themed clipart and names")

    if has_any(text, ["wedding", "anniversary", "couple", "matching"]):
        scores["multiple_names"] += 25
        scores["line_art"] += 20
        scores["photo"] += 18
        reasons.append("relationship occasions favor names, dates, and line-art systems")

    if has_any(text, ["funny", "retro", "vintage", "boho", "minimalist"]):
        scores["hand_drawing"] += 18
        scores["clipart"] += 12
        reasons.append("style-led segments can use reusable illustration systems")

    for customization, boost in confidence_boosts(
        customization_recommendations,
        segment_name,
        "customization",
    ).items():
        if customization in scores:
            scores[customization] += boost

    capped = {item: int(round(clamp(score))) for item, score in scores.items()}
    best_customization = max(capped, key=lambda item: (capped[item], item))
    explanation = "; ".join(reasons[:3]) if reasons else "Name customization is the broadest deterministic fit."
    output = {
        "child_segment": segment_name,
        "segment_label_source": clean_text(segment.get("segment_label_source")) or "observed_phrase",
        "canonical_evidence_phrase": clean_text(segment.get("canonical_evidence_phrase")),
        "observed_products": clean_text(segment.get("observed_products")),
        **capped,
    }
    output["best_customization"] = best_customization.replace("_", " ").title()
    output["explanation"] = explanation
    return output


def build_product_fit_matrix(
    segments: pd.DataFrame,
    product_recommendations: pd.DataFrame,
) -> pd.DataFrame:
    rows = [score_product_fit(segment, product_recommendations) for _, segment in segments.iterrows()]
    return pd.DataFrame(rows, columns=PRODUCT_COLUMNS).drop_duplicates("child_segment").reset_index(drop=True)


def build_customization_fit_matrix(
    segments: pd.DataFrame,
    customization_recommendations: pd.DataFrame,
) -> pd.DataFrame:
    rows = [score_customization_fit(segment, customization_recommendations) for _, segment in segments.iterrows()]
    return pd.DataFrame(rows, columns=CUSTOMIZATION_COLUMNS).drop_duplicates("child_segment").reset_index(drop=True)


def parent_lookup(scorecard: pd.DataFrame) -> pd.DataFrame:
    return scorecard.sort_values(
        ["overall_score", "expansion_score", "demand_name"],
        ascending=[False, False, True],
    ).drop_duplicates("demand_name", keep="first").set_index("demand_name")


def product_score_lookup(product_fit: pd.DataFrame) -> dict[str, float]:
    score_columns = [
        "card_score",
        "blanket_score",
        "mug_score",
        "tumbler_score",
        "shirt_score",
        "ornament_score",
        "canvas_score",
    ]
    return product_fit.set_index("child_segment")[score_columns].max(axis=1).to_dict()


def product_name_lookup(product_fit: pd.DataFrame) -> dict[str, str]:
    return product_fit.set_index("child_segment")["best_product"].to_dict()


def customization_name_lookup(customization_fit: pd.DataFrame) -> dict[str, str]:
    return customization_fit.set_index("child_segment")["best_customization"].to_dict()


def score_market_size(segment: pd.Series, parent: pd.Series) -> float:
    base = SIZE_BASE_SCORE.get(clean_text(parent.get("market_size")), 42.0)
    segment_rank = rank_score(segment.get("best_rank"))
    parent_overall = numeric(parent.get("overall_score"), base)
    return round(clamp(base * 0.55 + segment_rank * 0.35 + parent_overall * 0.10), 2)


def score_growth(segment: pd.Series, parent: pd.Series) -> float:
    trend = lower_text(segment.get("trend")) or lower_text(parent.get("growth_stage"))
    trend_component = TREND_SCORE.get(trend, 52.0)
    active_component = active_month_score(segment.get("active_months"))
    strength_component = clamp(numeric(segment.get("segment_strength")) * 2.6)
    return round(clamp(trend_component * 0.55 + active_component * 0.25 + strength_component * 0.20), 2)


def score_competition(segment: pd.Series, parent: pd.Series) -> float:
    competition = clean_text(parent.get("competition_level"))
    base = COMPETITION_OPPORTUNITY_SCORE.get(competition, 56.0)
    specificity_bonus = 12.0 if has_semantic_specificity(segment) else 0.0
    rank_penalty = 8.0 if numeric(segment.get("best_rank"), 999999) <= 5000 else 0.0
    return round(clamp(base + specificity_bonus - rank_penalty), 2)


def score_expansion(segment: pd.Series, parent: pd.Series) -> float:
    parent_expansion = numeric(parent.get("expansion_score"), 45.0)
    specificity = segment_specificity_score(segment)
    strength = clamp(numeric(segment.get("segment_strength")) * 2.4)
    return round(clamp(parent_expansion * 0.58 + specificity * 0.22 + strength * 0.20), 2)


def score_seasonality(segment: pd.Series, parent: pd.Series) -> float:
    seasonality = clean_text(parent.get("seasonality"))
    base = SEASONALITY_SCORE.get(seasonality, 50.0)
    text = context_text(segment)
    if has_any(text, ["christmas", "halloween", "thanksgiving", "valentine", "mother's day", "father's day"]):
        base = max(base, 84.0)
    if has_any(text, ["birthday", "anniversary", "wedding", "graduation", "retirement"]):
        base = max(base, 74.0)
    if lower_text(segment.get("trend")) == "declining":
        base -= 12.0
    return round(clamp(base * 0.75 + active_month_score(segment.get("active_months")) * 0.25), 2)


def opportunity_explanation(row: dict[str, object], segment: pd.Series, parent: pd.Series) -> str:
    score = numeric(row["total_score"])
    strongest = max(
        [
            ("market size", numeric(row["market_size_score"])),
            ("growth", numeric(row["growth_score"])),
            ("competition", numeric(row["competition_score"])),
            ("expansion", numeric(row["expansion_score"])),
            ("seasonality", numeric(row["seasonality_score"])),
            ("product fit", numeric(row["product_fit_score"])),
        ],
        key=lambda item: item[1],
    )
    weakest = min(
        [
            ("market size", numeric(row["market_size_score"])),
            ("growth", numeric(row["growth_score"])),
            ("competition", numeric(row["competition_score"])),
            ("expansion", numeric(row["expansion_score"])),
            ("seasonality", numeric(row["seasonality_score"])),
            ("product fit", numeric(row["product_fit_score"])),
        ],
        key=lambda item: item[1],
    )
    quality = "high" if score >= 80 else "moderate" if score >= 60 else "limited"
    return (
        f"{clean_text(segment['segment_name'])} has {quality} opportunity score. "
        f"Strongest signal is {strongest[0]} ({round(strongest[1], 1)}); "
        f"main constraint is {weakest[0]} ({round(weakest[1], 1)}). "
        f"Parent demand is {clean_text(parent.get('market_size'))} with "
        f"{clean_text(parent.get('competition_level')).lower()} inferred competition."
    )


def build_opportunity_scorecard(
    segments: pd.DataFrame,
    market_scorecard: pd.DataFrame,
    product_fit: pd.DataFrame,
) -> pd.DataFrame:
    parents = parent_lookup(market_scorecard)
    fit_scores = product_score_lookup(product_fit)
    rows = []
    for _, segment in segments.iterrows():
        parent_name = clean_text(segment.get("parent_demand"))
        if parent_name not in parents.index:
            continue
        parent = parents.loc[parent_name]
        child_segment = clean_text(segment["segment_name"])
        market_size_score = score_market_size(segment, parent)
        growth_score = score_growth(segment, parent)
        competition_score = score_competition(segment, parent)
        expansion_score = score_expansion(segment, parent)
        seasonality_score = score_seasonality(segment, parent)
        product_fit_score = numeric(fit_scores.get(child_segment), 50.0)
        total_score = round(
            market_size_score * 0.25
            + growth_score * 0.20
            + competition_score * 0.20
            + expansion_score * 0.15
            + seasonality_score * 0.10
            + product_fit_score * 0.10,
            2,
        )
        row = {
            "parent_demand": parent_name,
            "child_segment": child_segment,
            "market_size_score": market_size_score,
            "growth_score": growth_score,
            "competition_score": competition_score,
            "expansion_score": expansion_score,
            "seasonality_score": seasonality_score,
            "product_fit_score": product_fit_score,
            "total_score": total_score,
            "recommended_priority": priority_from_score(total_score),
        }
        row["explanation"] = opportunity_explanation(row, segment, parent)
        rows.append(row)

    output = pd.DataFrame(rows, columns=OPPORTUNITY_COLUMNS)
    return output.sort_values(
        ["total_score", "market_size_score", "growth_score", "child_segment"],
        ascending=[False, False, False, True],
    ).reset_index(drop=True)


def sentence_join(parts: list[str]) -> str:
    cleaned = [part for part in parts if part]
    return " ".join(cleaned) if cleaned else "No material signal available."


def build_research_reasoning(
    segments: pd.DataFrame,
    opportunity_scorecard: pd.DataFrame,
    product_fit: pd.DataFrame,
    customization_fit: pd.DataFrame,
    market_scorecard: pd.DataFrame,
) -> pd.DataFrame:
    parents = parent_lookup(market_scorecard)
    score_lookup = opportunity_scorecard.set_index("child_segment").to_dict("index")
    product_lookup = product_name_lookup(product_fit)
    customization_lookup = customization_name_lookup(customization_fit)

    rows = []
    for _, segment in segments.iterrows():
        child_segment = clean_text(segment["segment_name"])
        score = score_lookup.get(child_segment)
        if not score:
            continue
        parent_name = clean_text(segment.get("parent_demand"))
        parent = parents.loc[parent_name] if parent_name in parents.index else pd.Series(dtype=object)
        best_product = product_lookup.get(child_segment, "Mug")
        best_customization = customization_lookup.get(child_segment, "Name")
        total_score = numeric(score.get("total_score"))
        trend = lower_text(segment.get("trend"))
        seasonality = clean_text(parent.get("seasonality"))

        strengths = [
            f"{clean_text(parent.get('market_size'))} parent demand" if clean_text(parent.get("market_size")) else "",
            f"best rank {int(numeric(segment.get('best_rank'))):,}" if numeric(segment.get("best_rank")) else "",
            f"{trend} trend" if trend else "",
            f"{best_product} is the strongest product fit",
        ]
        weaknesses = [
            "Competition is inferred as high" if clean_text(parent.get("competition_level")) == "High" else "",
            "Segment score is below the top research threshold" if total_score < 80 else "",
            "Demand appears seasonal" if seasonality in {"Q4 Seasonal", "Holiday Seasonal"} else "",
            "Limited active-month history" if numeric(segment.get("active_months")) < 3 else "",
        ]
        risks = [
            "Validate differentiation before building broad designs"
            if clean_text(parent.get("competition_level")) == "High"
            else "",
            "Seasonal timing can compress launch windows" if seasonality in {"Q4 Seasonal", "Holiday Seasonal"} else "",
            "Declining rank signal should be confirmed in the next ABA import" if trend == "declining" else "",
            "Evidence is narrow; confirm related phrases manually" if numeric(segment.get("keyword_count")) < 10 else "",
        ]
        opportunities = [
            f"Test {best_product.lower()} designs first",
            f"Use {best_customization.lower()} customization as the default personalization angle",
            "Expand into adjacent child segments if early tests rank",
        ]
        if total_score >= 80:
            why_now = "Strong score and existing rank evidence make this ready for near-term research."
            next_step = f"Build a compact research brief around {best_product} and {best_customization} variants."
        elif seasonality in {"Q4 Seasonal", "Holiday Seasonal"}:
            why_now = "Seasonal evidence requires planning ahead of the peak selling window."
            next_step = "Map launch timing and validate seasonal phrase variants before design production."
        elif trend == "growing":
            why_now = "Growing rank signal justifies monitoring and small validation tests."
            next_step = "Validate the top evidence phrases and prepare a limited product test."
        else:
            why_now = "Current signal is useful but not urgent."
            next_step = "Monitor the next import and only research if rank or evidence improves."

        rows.append(
            {
                "child_segment": child_segment,
                "strengths": sentence_join(strengths),
                "weaknesses": sentence_join(weaknesses),
                "risks": sentence_join(risks),
                "opportunities": sentence_join(opportunities),
                "why_now": why_now,
                "recommended_next_step": next_step,
            }
        )

    output = pd.DataFrame(rows, columns=REASONING_COLUMNS)
    score_order = opportunity_scorecard[["child_segment", "total_score"]]
    output = output.merge(score_order, on="child_segment", how="left")
    output = output.sort_values(["total_score", "child_segment"], ascending=[False, True])
    return output[REASONING_COLUMNS].reset_index(drop=True)


def write_csv(frame: pd.DataFrame, output_dir: Path, key: str) -> None:
    path = output_dir / OUTPUT_FILES[key]
    frame.to_csv(path, index=False)
    print(f"Exported {display_path(path)}: {len(frame):,} rows")


def print_top_sections(
    opportunity_scorecard: pd.DataFrame,
    product_fit: pd.DataFrame,
    customization_fit: pd.DataFrame,
    reasoning: pd.DataFrame,
) -> None:
    print("\nTop 20 highest opportunity scores")
    print(
        opportunity_scorecard[
            [
                "parent_demand",
                "child_segment",
                "total_score",
                "recommended_priority",
                "product_fit_score",
            ]
        ]
        .head(20)
        .to_string(index=False)
    )

    print("\nTop 20 best product fits")
    product_display = product_fit.copy()
    product_display["best_product_score"] = product_display[
        [
            "card_score",
            "blanket_score",
            "mug_score",
            "tumbler_score",
            "shirt_score",
            "ornament_score",
            "canvas_score",
        ]
    ].max(axis=1)
    print(
        product_display[
            [
                "child_segment",
                "best_product",
                "best_product_score",
                "explanation",
            ]
        ]
        .sort_values(["best_product_score", "child_segment"], ascending=[False, True])
        .head(20)
        .to_string(index=False)
    )

    print("\nTop 20 customization recommendations")
    customization_display = customization_fit.copy()
    customization_display["best_customization_score"] = customization_display[
        [
            "photo",
            "name",
            "multiple_names",
            "birth_flower",
            "clipart",
            "line_art",
            "hand_drawing",
        ]
    ].max(axis=1)
    print(
        customization_display[
            [
                "child_segment",
                "best_customization",
                "best_customization_score",
                "explanation",
            ]
        ]
        .sort_values(["best_customization_score", "child_segment"], ascending=[False, True])
        .head(20)
        .to_string(index=False)
    )

    print("\nTop 20 research summaries")
    print(
        reasoning[
            [
                "child_segment",
                "strengths",
                "why_now",
                "recommended_next_step",
            ]
        ]
        .head(20)
        .to_string(index=False)
    )


def build_opportunity_scoring(output_dir: Path, rebuild: bool) -> None:
    ensure_rebuild_allowed(output_dir, rebuild)
    output_dir.mkdir(parents=True, exist_ok=True)
    if rebuild:
        remove_scoring_outputs(output_dir)

    segments = read_required_csv("segments")
    market_scorecard = read_required_csv("market_scorecard")
    research_candidates = read_required_csv("research_candidates")
    product_recommendations = read_required_csv("product_recommendation")
    customization_recommendations = read_required_csv("customization_recommendation")
    print(f"Validated decision candidate context: {len(research_candidates):,} rows")

    product_fit = build_product_fit_matrix(segments, product_recommendations)
    customization_fit = build_customization_fit_matrix(segments, customization_recommendations)
    opportunity_scorecard = build_opportunity_scorecard(segments, market_scorecard, product_fit)
    reasoning = build_research_reasoning(
        segments,
        opportunity_scorecard,
        product_fit,
        customization_fit,
        market_scorecard,
    )

    write_csv(opportunity_scorecard, output_dir, "opportunity_scorecard")
    write_csv(product_fit, output_dir, "product_fit_matrix")
    write_csv(customization_fit, output_dir, "customization_fit_matrix")
    write_csv(reasoning, output_dir, "research_reasoning")
    print_top_sections(opportunity_scorecard, product_fit, customization_fit, reasoning)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = parse_args()
    build_opportunity_scoring(output_dir=args.output_dir.resolve(), rebuild=args.rebuild)


if __name__ == "__main__":
    main()
