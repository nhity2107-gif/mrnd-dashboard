"""Build deterministic portfolio planning outputs from scoring CSVs."""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "output" / "portfolio"

INPUT_PATHS = {
    "opportunity_scorecard": PROJECT_ROOT
    / "data"
    / "output"
    / "scoring"
    / "opportunity_scorecard.csv",
    "product_fit_matrix": PROJECT_ROOT / "data" / "output" / "scoring" / "product_fit_matrix.csv",
    "customization_fit_matrix": PROJECT_ROOT
    / "data"
    / "output"
    / "scoring"
    / "customization_fit_matrix.csv",
    "research_reasoning": PROJECT_ROOT / "data" / "output" / "scoring" / "research_reasoning.csv",
    "segments": PROJECT_ROOT / "data" / "output" / "demand_segments" / "demand_segments.csv",
    "market_scorecard": PROJECT_ROOT / "data" / "output" / "decision" / "market_scorecard.csv",
}

REQUIRED_COLUMNS = {
    "opportunity_scorecard": {
        "parent_demand",
        "child_segment",
        "market_size_score",
        "growth_score",
        "competition_score",
        "expansion_score",
        "seasonality_score",
        "product_fit_score",
        "total_score",
    },
    "product_fit_matrix": {
        "child_segment",
        "blanket_score",
        "mug_score",
        "tumbler_score",
        "shirt_score",
        "ornament_score",
        "canvas_score",
        "best_product",
    },
    "customization_fit_matrix": {
        "child_segment",
        "photo",
        "name",
        "multiple_names",
        "birth_flower",
        "clipart",
        "line_art",
        "hand_drawing",
        "best_customization",
    },
    "research_reasoning": {
        "child_segment",
        "strengths",
        "weaknesses",
        "risks",
        "opportunities",
        "recommended_next_step",
    },
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
    },
    "market_scorecard": {
        "demand_name",
        "market_size",
        "growth_stage",
        "competition_level",
        "expansion_score",
        "seasonality",
        "overall_score",
        "research_priority",
        "recommended_action",
    },
}

OUTPUT_FILES = {
    "portfolio_master": "portfolio_master.csv",
    "portfolio_tree": "portfolio_tree.csv",
    "whitespace_analysis": "whitespace_analysis.csv",
    "portfolio_roadmap": "portfolio_roadmap.csv",
    "portfolio_summary": "portfolio_summary.csv",
}

PORTFOLIO_MASTER_COLUMNS = [
    "portfolio_id",
    "parent_demand",
    "market_size",
    "child_segment_count",
    "average_opportunity_score",
    "best_child_score",
    "expansion_potential",
    "portfolio_stage",
    "research_priority",
    "coverage_score",
    "investment_recommendation",
]

PORTFOLIO_TREE_COLUMNS = [
    "parent_demand",
    "child_segment",
    "recommended_product",
    "recommended_customization",
    "opportunity_score",
]

WHITESPACE_COLUMNS = [
    "parent_demand",
    "missing_child_segment",
    "candidate_source",
    "evidence_level",
    "match_type",
    "confidence_reason",
    "recommended_product",
    "recommended_customization",
    "confidence",
    "reason",
    "expected_value",
]

ROADMAP_COLUMNS = [
    "week",
    "parent_demand",
    "child_segment",
    "product",
    "customization",
    "priority",
    "reason",
]

SUMMARY_COLUMNS = [
    "parent_demand",
    "current_child_segments",
    "estimated_total_segments",
    "coverage_percent",
    "average_score",
    "best_products",
    "strongest_customization",
    "next_recommendation",
]

MARKET_POTENTIAL = {
    "Mega": 26,
    "Large": 20,
    "Mid": 14,
    "Small": 9,
    "Micro": 6,
}

PRIORITY_ORDER = {"P1": 1, "P2": 2, "P3": 3, "Watchlist": 4}
EVIDENCE_ORDER = {"Strong Evidence": 1, "Moderate Evidence": 2, "Hypothesis": 3}
POST_BASE_MODIFIERS = {
    "Appreciation",
    "Anniversary",
    "Birthday",
    "Graduation",
    "Retirement",
    "Wedding",
}

ALLOWED_EXPANSION_FAMILIES = {
    "Mom Gift": [
        "Dog Mom",
        "Cat Mom",
        "Gardening Mom",
        "Fishing Mom",
        "Camping Mom",
        "Coffee Lover Mom",
        "Reading Mom",
        "Funny Mom",
        "Christmas Mom",
        "Birthday Mom",
        "Mother's Day Mom",
    ],
    "Dad Gift": [
        "Dog Dad",
        "Cat Dad",
        "Fishing Dad",
        "Golf Dad",
        "Hunting Dad",
        "Camping Dad",
        "Coffee Lover Dad",
        "Funny Dad",
        "Christmas Dad",
        "Birthday Dad",
        "Father's Day Dad",
    ],
    "Teacher Gift": [
        "Teacher Appreciation",
        "Christmas Teacher",
        "Funny Teacher",
        "Teacher Birthday",
        "Teacher Retirement",
        "Math Teacher",
        "Music Teacher",
        "Science Teacher",
        "Kindergarten Teacher",
        "Preschool Teacher",
        "Back To School Teacher",
        "Graduation Teacher",
    ],
    "Grandma Gift": [
        "Grandma Birthday",
        "Christmas Grandma",
        "Gardening Grandma",
        "Cat Grandma",
        "Dog Grandma",
        "Grandma Memorial",
        "Grandma Mother's Day",
    ],
    "Grandpa Gift": [
        "Grandpa Birthday",
        "Christmas Grandpa",
        "Fishing Grandpa",
        "Golf Grandpa",
        "Hunting Grandpa",
        "Retired Grandpa",
    ],
    "Wife Gift": [
        "Wife Birthday",
        "Wife Anniversary",
        "Christmas Wife",
        "Wife Wedding",
        "Funny Wife",
    ],
    "Husband Gift": [
        "Husband Birthday",
        "Husband Anniversary",
        "Christmas Husband",
        "Funny Husband",
    ],
    "Dog Gift": [
        "Dog Memorial",
        "Christmas Dog",
        "Dog Lover",
        "Personalized Dog",
    ],
    "Cat Gift": [
        "Cat Memorial",
        "Christmas Cat",
        "Cat Lover",
        "Personalized Cat",
    ],
}

WHITESPACE_PATTERNS = [
    {
        "modifier": "Christmas",
        "score": 92,
        "products": ("Ornament", "Mug"),
        "customization": "Name",
        "reason": "Christmas is the strongest recurring seasonal expansion pattern.",
    },
    {
        "modifier": "Birthday",
        "score": 84,
        "products": ("Mug", "Blanket"),
        "customization": "Name",
        "reason": "Birthday variants create evergreen gifting extensions.",
    },
    {
        "modifier": "Appreciation",
        "score": 80,
        "products": ("Mug", "Tumbler"),
        "customization": "Name",
        "reason": "Appreciation language appears across profession and recipient markets.",
    },
    {
        "modifier": "Funny",
        "score": 78,
        "products": ("Mug", "Shirt"),
        "customization": "Clipart",
        "reason": "Funny themes are repeatable design systems across many markets.",
    },
    {
        "modifier": "Dog Lover",
        "score": 76,
        "products": ("Blanket", "Mug"),
        "customization": "Photo",
        "reason": "Dog-lover identity creates clear emotional gift angles.",
    },
    {
        "modifier": "Cat Lover",
        "score": 74,
        "products": ("Blanket", "Mug"),
        "customization": "Photo",
        "reason": "Cat-lover identity is a recurring child segment across gift markets.",
    },
    {
        "modifier": "Fishing",
        "score": 72,
        "products": ("Tumbler", "Mug"),
        "customization": "Clipart",
        "reason": "Fishing is a repeatable hobby niche with strong product fit.",
    },
    {
        "modifier": "Camping",
        "score": 70,
        "products": ("Tumbler", "Mug"),
        "customization": "Clipart",
        "reason": "Camping expands family and outdoor gift portfolios.",
    },
    {
        "modifier": "Coffee Lover",
        "score": 70,
        "products": ("Mug", "Tumbler"),
        "customization": "Name",
        "reason": "Coffee identity has direct product fit with drinkware.",
    },
    {
        "modifier": "Gardening",
        "score": 69,
        "products": ("Tumbler", "Mug"),
        "customization": "Clipart",
        "reason": "Gardening is a recurring hobby niche in gift demand.",
    },
    {
        "modifier": "Reading",
        "score": 68,
        "products": ("Mug", "Canvas"),
        "customization": "Name",
        "reason": "Reading and book-lover markets support giftable identity products.",
    },
    {
        "modifier": "Soccer",
        "score": 67,
        "products": ("Tumbler", "Shirt"),
        "customization": "Name",
        "reason": "Sports identity supports repeatable recipient-child niches.",
    },
    {
        "modifier": "Halloween",
        "score": 66,
        "products": ("Shirt", "Mug"),
        "customization": "Clipart",
        "reason": "Halloween creates a shorter but repeatable seasonal launch window.",
    },
    {
        "modifier": "Wedding",
        "score": 64,
        "products": ("Blanket", "Canvas"),
        "customization": "Multiple Names",
        "reason": "Wedding variants support relationship and keepsake products.",
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build portfolio intelligence CSVs from existing opportunity scoring outputs.",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Overwrite portfolio outputs in data/output/portfolio/.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Output directory for portfolio CSVs.",
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
        raise FileExistsError(f"Portfolio outputs already exist. Use --rebuild to replace: {names}")


def remove_portfolio_outputs(output_dir: Path) -> None:
    for filename in OUTPUT_FILES.values():
        path = output_dir / filename
        if path.exists():
            path.unlink()


def parent_base(parent_demand: str) -> tuple[str, str]:
    value = clean_text(parent_demand)
    for suffix in [" Gift", " Decor", " Matching", " Memorial", " Apparel"]:
        if value.endswith(suffix):
            return value[: -len(suffix)], suffix.strip()
    return value, ""


def child_segment_name(parent_demand: str, modifier: str) -> str:
    base, intent = parent_base(parent_demand)
    modifier_value = clean_text(modifier)
    if not base:
        return modifier_value
    if intent:
        if modifier_value in POST_BASE_MODIFIERS:
            return f"{base} {modifier_value} {intent}".strip()
        return f"{modifier_value} {base} {intent}".strip()
    return f"{modifier_value} {clean_text(parent_demand)}".strip()


def family_candidate_name(parent_demand: str, family_label: str) -> str:
    _, intent = parent_base(parent_demand)
    label = clean_text(family_label)
    if not label:
        return ""
    if intent:
        return f"{label} {intent}".strip()
    return label


def normalize_segment_key(value: object) -> str:
    text = lower_text(value)
    for old, new in {
        "'": "",
        "-": " ",
        "/": " ",
        "&": " ",
        ",": " ",
        ".": " ",
        "(": " ",
        ")": " ",
    }.items():
        text = text.replace(old, new)
    stop_words = {
        "a",
        "and",
        "for",
        "gift",
        "gifts",
        "present",
        "presents",
        "the",
        "to",
    }
    tokens = sorted({token for token in text.split() if token and token not in stop_words})
    return " ".join(tokens)


def allowed_family_keys(parent_demand: str) -> set[str]:
    keys = set()
    for label in ALLOWED_EXPANSION_FAMILIES.get(clean_text(parent_demand), []):
        keys.add(normalize_segment_key(label))
        keys.add(normalize_segment_key(family_candidate_name(parent_demand, label)))
    return keys


def infer_family_pattern(parent_demand: str, family_label: str) -> dict[str, object]:
    label = lower_text(family_label)
    product = "Mug"
    customization = "Name"
    score = 66
    reason = "Allowed expansion family for this parent demand."

    if "christmas" in label:
        product = "Ornament"
        score = 86
        reason = "Christmas is an approved seasonal expansion for this parent market."
    elif "birthday" in label:
        product = "Mug"
        score = 78
        reason = "Birthday is an approved evergreen gift expansion for this parent market."
    elif "appreciation" in label:
        product = "Mug"
        score = 80
        reason = "Appreciation is an approved buyer-intent expansion for this parent market."
    elif any(term in label for term in ["anniversary", "wedding"]):
        product = "Blanket"
        customization = "Multiple Names"
        score = 72
        reason = "Relationship occasions are approved keepsake expansions for this parent market."
    elif any(term in label for term in ["dog", "cat", "memorial"]):
        product = "Blanket"
        customization = "Photo"
        score = 74
        reason = "Pet and memorial language is an approved emotional-gift expansion."
    elif any(term in label for term in ["fishing", "golf", "hunting", "camping"]):
        product = "Tumbler"
        customization = "Clipart"
        score = 72
        reason = "Outdoor and hobby niches are approved expansions for this parent market."
    elif any(term in label for term in ["coffee", "reading"]):
        product = "Mug"
        score = 70
        reason = "Identity-led lifestyle niches are approved expansions for this parent market."
    elif any(term in label for term in ["math", "music", "science", "kindergarten", "preschool", "school"]):
        product = "Mug"
        customization = "Name"
        score = 72
        reason = "Teacher-specialty niches are approved expansions for Teacher Gift."
    elif "funny" in label:
        product = "Mug"
        customization = "Clipart"
        score = 72
        reason = "Funny themes are approved repeatable design expansions."

    return {
        "modifier": clean_text(family_label),
        "score": score,
        "products": (product,),
        "customization": customization,
        "reason": reason,
        "candidate": family_candidate_name(parent_demand, family_label),
    }


def whitespace_candidate_specs(parent_demand: str) -> list[dict[str, object]]:
    specs = []
    seen_keys: set[str] = set()

    for pattern in WHITESPACE_PATTERNS:
        candidate = child_segment_name(parent_demand, clean_text(pattern["modifier"]))
        key = normalize_segment_key(candidate)
        if key in seen_keys:
            continue
        spec = dict(pattern)
        spec["candidate"] = candidate
        specs.append(spec)
        seen_keys.add(key)

    for family_label in ALLOWED_EXPANSION_FAMILIES.get(clean_text(parent_demand), []):
        spec = infer_family_pattern(parent_demand, family_label)
        key = normalize_segment_key(spec["candidate"])
        if key in seen_keys:
            continue
        specs.append(spec)
        seen_keys.add(key)

    return specs


def build_segment_evidence_index(segments: pd.DataFrame) -> dict[str, object]:
    all_segment_keys: set[str] = set()
    keyword_keys: set[str] = set()
    parent_segment_keys: dict[str, set[str]] = {}

    for _, row in segments.iterrows():
        parent = clean_text(row.get("parent_demand"))
        segment_key = normalize_segment_key(row.get("segment_name"))
        if segment_key:
            all_segment_keys.add(segment_key)
            parent_segment_keys.setdefault(parent, set()).add(segment_key)

        for keyword in str(row.get("evidence_keywords", "")).split("|"):
            keyword_key = normalize_segment_key(keyword)
            if keyword_key:
                keyword_keys.add(keyword_key)

    return {
        "all_segment_keys": all_segment_keys,
        "keyword_keys": keyword_keys,
        "parent_segment_keys": parent_segment_keys,
    }


def classify_whitespace_candidate(
    parent_demand: str,
    candidate: str,
    evidence_index: dict[str, object],
) -> tuple[str, str, str]:
    candidate_key = normalize_segment_key(candidate)
    all_segment_keys = evidence_index["all_segment_keys"]
    keyword_keys = evidence_index["keyword_keys"]

    if candidate_key in all_segment_keys:
        return (
            "Strong Evidence",
            "Existing Segment Gap",
            "Accepted because the exact child segment already exists in demand_segments.csv.",
        )
    if candidate_key in keyword_keys:
        return (
            "Strong Evidence",
            "Existing Segment Gap",
            "Accepted because the exact phrase appears in segment evidence keywords.",
        )
    if candidate_key in allowed_family_keys(parent_demand):
        return (
            "Moderate Evidence",
            "Parent-Compatible Expansion",
            "Accepted because this child niche is in the allowed expansion family for the parent demand.",
        )
    return (
        "Hypothesis",
        "Cross-Market Hypothesis",
        "Downgraded because no exact segment, exact keyword evidence, or allowed family match was found.",
    )


def generated_occasion_label_requires_exact_evidence(candidate: str) -> bool:
    key = normalize_segment_key(candidate)
    occasion_tokens = {
        "appreciation",
        "anniversary",
        "birthday",
        "graduation",
        "retirement",
        "wedding",
    }
    return bool(occasion_tokens.intersection(key.split()))


def blocked_unless_exact(parent_demand: str, candidate: str, match_type: str) -> bool:
    if match_type == "Existing Segment Gap":
        return False
    if clean_text(parent_demand) != "Teacher Gift":
        return False
    key = normalize_segment_key(candidate)
    blocked_keys = {
        normalize_segment_key("Dog Lover Teacher Gift"),
        normalize_segment_key("Cat Lover Teacher Gift"),
        normalize_segment_key("Fishing Teacher Gift"),
        normalize_segment_key("Camping Teacher Gift"),
    }
    return key in blocked_keys


def market_lookup(market_scorecard: pd.DataFrame) -> pd.DataFrame:
    return market_scorecard.sort_values(
        ["overall_score", "expansion_score", "demand_name"],
        ascending=[False, False, True],
    ).drop_duplicates("demand_name", keep="first").set_index("demand_name")


def merge_scoring_context(
    opportunity_scorecard: pd.DataFrame,
    product_fit: pd.DataFrame,
    customization_fit: pd.DataFrame,
    reasoning: pd.DataFrame,
    segments: pd.DataFrame,
) -> pd.DataFrame:
    product_cols = [
        "child_segment",
        "best_product",
        "card_score",
        "blanket_score",
        "mug_score",
        "tumbler_score",
        "shirt_score",
        "ornament_score",
        "canvas_score",
    ]
    customization_cols = [
        "child_segment",
        "best_customization",
        "photo",
        "name",
        "multiple_names",
        "birth_flower",
        "clipart",
        "line_art",
        "hand_drawing",
    ]
    segment_cols = [
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
    ]
    product_cols = [column for column in product_cols if column in product_fit.columns]
    context = opportunity_scorecard.merge(product_fit[product_cols], on="child_segment", how="left")
    context = context.merge(customization_fit[customization_cols], on="child_segment", how="left")
    context = context.merge(reasoning[["child_segment", "recommended_next_step"]], on="child_segment", how="left")
    context = context.merge(
        segments[segment_cols],
        left_on=["parent_demand", "child_segment"],
        right_on=["parent_demand", "segment_name"],
        how="left",
    )
    return context.drop(columns=["segment_name"], errors="ignore")


def estimated_total_segments(child_count: int, market_size: str, parent_expansion: float, best_score: float) -> int:
    base = MARKET_POTENTIAL.get(clean_text(market_size), 8)
    expansion_bonus = int(round(parent_expansion / 20.0))
    strength_bonus = 3 if best_score >= 78 else 2 if best_score >= 70 else 1 if best_score >= 60 else 0
    return max(child_count, base + expansion_bonus + strength_bonus)


def portfolio_stage(
    child_count: int,
    coverage_score: float,
    average_score: float,
    best_child_score: float,
) -> str:
    if coverage_score >= 85 or child_count >= 18:
        return "Saturated"
    if average_score >= 69 and child_count >= 5 and best_child_score >= 72:
        return "Mature"
    if average_score >= 58 or child_count >= 3:
        return "Growing"
    return "Emerging"


def research_priority(best_child_score: float, average_score: float, expansion_potential: float) -> str:
    if best_child_score >= 80 or (average_score >= 73 and expansion_potential >= 72):
        return "P1"
    if best_child_score >= 72 or average_score >= 67:
        return "P2"
    if best_child_score >= 62 or average_score >= 58:
        return "P3"
    return "Watchlist"


def investment_recommendation(
    priority: str,
    stage: str,
    coverage_score: float,
    average_score: float,
    expansion_potential: float,
) -> str:
    if priority == "P1" and coverage_score < 75 and expansion_potential >= 65:
        return "Invest Aggressively"
    if priority in {"P1", "P2"} and coverage_score < 85:
        return "Expand"
    if stage in {"Mature", "Saturated"} and average_score >= 62:
        return "Maintain"
    if average_score >= 52:
        return "Monitor"
    return "Exit"


def build_portfolio_master(scoring_context: pd.DataFrame, market_scorecard: pd.DataFrame) -> pd.DataFrame:
    markets = market_lookup(market_scorecard)
    rows = []
    grouped = scoring_context.groupby("parent_demand", dropna=False)
    for parent_demand, group in grouped:
        parent = clean_text(parent_demand)
        if not parent:
            continue
        market = markets.loc[parent] if parent in markets.index else pd.Series(dtype=object)
        child_count = int(group["child_segment"].nunique())
        average_score = round(float(group["total_score"].mean()), 2)
        best_score = round(float(group["total_score"].max()), 2)
        parent_expansion = numeric(market.get("expansion_score"), group["expansion_score"].mean())
        market_size = clean_text(market.get("market_size")) or "Unknown"
        estimated_total = estimated_total_segments(child_count, market_size, parent_expansion, best_score)
        coverage_score = round(clamp((child_count / estimated_total) * 100.0), 2)
        expansion_potential = round(
            clamp(parent_expansion * 0.45 + (100.0 - coverage_score) * 0.30 + best_score * 0.25),
            2,
        )
        stage = portfolio_stage(child_count, coverage_score, average_score, best_score)
        priority = research_priority(best_score, average_score, expansion_potential)
        investment = investment_recommendation(priority, stage, coverage_score, average_score, expansion_potential)
        rows.append(
            {
                "parent_demand": parent,
                "market_size": market_size,
                "child_segment_count": child_count,
                "average_opportunity_score": average_score,
                "best_child_score": best_score,
                "expansion_potential": expansion_potential,
                "portfolio_stage": stage,
                "research_priority": priority,
                "coverage_score": coverage_score,
                "investment_recommendation": investment,
            }
        )

    output = pd.DataFrame(rows)
    output = output.sort_values(
        ["research_priority", "expansion_potential", "best_child_score", "parent_demand"],
        ascending=[True, False, False, True],
        key=lambda series: series.map(PRIORITY_ORDER) if series.name == "research_priority" else series,
    ).reset_index(drop=True)
    output.insert(0, "portfolio_id", [f"PF{index:06d}" for index in range(1, len(output) + 1)])
    return output[PORTFOLIO_MASTER_COLUMNS]


def build_portfolio_tree(scoring_context: pd.DataFrame) -> pd.DataFrame:
    output = scoring_context[
        [
            "parent_demand",
            "child_segment",
            "best_product",
            "best_customization",
            "total_score",
        ]
    ].copy()
    output = output.rename(
        columns={
            "best_product": "recommended_product",
            "best_customization": "recommended_customization",
            "total_score": "opportunity_score",
        }
    )
    return output.sort_values(
        ["parent_demand", "opportunity_score", "child_segment"],
        ascending=[True, False, True],
    ).drop_duplicates(["parent_demand", "child_segment"]).reset_index(drop=True)[PORTFOLIO_TREE_COLUMNS]


def modifier_is_relevant(parent_demand: str, modifier: str) -> bool:
    parent = lower_text(parent_demand)
    modifier_value = lower_text(modifier)
    if "decor" in parent and modifier_value in {"appreciation", "wedding", "birthday"}:
        return False
    if "matching" in parent and modifier_value in {"appreciation", "wedding"}:
        return False
    if "dog" in parent and modifier_value == "dog lover":
        return False
    if "cat" in parent and modifier_value == "cat lover":
        return False
    if "coffee" in parent and modifier_value == "coffee lover":
        return False
    if "christmas" in parent and modifier_value == "christmas":
        return False
    return True


def whitespace_reason(
    parent_demand: str,
    pattern: dict[str, object],
    market_size: str,
    coverage_score: float,
) -> str:
    return (
        f"{pattern['reason']} {parent_demand} is a {market_size.lower()} portfolio "
        f"with {round(coverage_score, 1)}% estimated coverage, leaving room for additional child niches."
    )


def build_whitespace_analysis(
    portfolio_master: pd.DataFrame,
    scoring_context: pd.DataFrame,
    segments: pd.DataFrame,
) -> pd.DataFrame:
    evidence_index = build_segment_evidence_index(segments)
    existing_by_parent = {
        parent: set(group["child_segment"].map(normalize_segment_key))
        for parent, group in scoring_context.groupby("parent_demand", dropna=False)
    }
    rows = []
    for _, portfolio in portfolio_master.iterrows():
        parent = clean_text(portfolio["parent_demand"])
        existing = existing_by_parent.get(parent, set())
        for pattern in whitespace_candidate_specs(parent):
            modifier = clean_text(pattern["modifier"])
            if not modifier_is_relevant(parent, modifier):
                continue
            candidate = clean_text(pattern["candidate"])
            candidate_key = normalize_segment_key(candidate)
            if not candidate or candidate_key in existing:
                continue
            evidence_level, match_type, confidence_reason = classify_whitespace_candidate(
                parent,
                candidate,
                evidence_index,
            )
            if generated_occasion_label_requires_exact_evidence(candidate) and match_type != "Existing Segment Gap":
                continue
            if blocked_unless_exact(parent, candidate, match_type):
                continue
            expected_value = round(
                clamp(
                    numeric(portfolio["best_child_score"]) * 0.40
                    + numeric(portfolio["average_opportunity_score"]) * 0.20
                    + numeric(pattern["score"]) * 0.25
                    + numeric(portfolio["expansion_potential"]) * 0.15,
                ),
                2,
            )
            confidence = round(
                clamp(
                    numeric(pattern["score"]) * 0.45
                    + numeric(portfolio["best_child_score"]) * 0.25
                    + (100.0 - numeric(portfolio["coverage_score"])) * 0.20
                    + numeric(portfolio["expansion_potential"]) * 0.10,
                ),
                2,
            )
            if evidence_level == "Strong Evidence":
                confidence = round(max(confidence, 82.0), 2)
                expected_value = round(max(expected_value, 70.0), 2)
            elif evidence_level == "Moderate Evidence":
                confidence = round(min(max(confidence, 62.0), 79.0), 2)
            else:
                confidence = round(min(confidence, 49.0), 2)
                expected_value = round(min(expected_value, 59.0), 2)

            products = pattern.get("products", ("",))
            recommended_product = clean_text(products[0] if products else "")
            rows.append(
                {
                    "parent_demand": parent,
                    "missing_child_segment": candidate,
                    "candidate_source": "expansion_candidate",
                    "evidence_level": evidence_level,
                    "match_type": match_type,
                    "confidence_reason": confidence_reason,
                    "recommended_product": recommended_product,
                    "recommended_customization": clean_text(pattern.get("customization")),
                    "confidence": confidence,
                    "reason": whitespace_reason(
                        parent,
                        pattern,
                        clean_text(portfolio["market_size"]),
                        numeric(portfolio["coverage_score"]),
                    ),
                    "expected_value": expected_value,
                }
            )

    output = pd.DataFrame(rows, columns=WHITESPACE_COLUMNS)
    if output.empty:
        return output
    output["_evidence_sort"] = output["evidence_level"].map(EVIDENCE_ORDER).fillna(99)
    return output.sort_values(
        ["_evidence_sort", "expected_value", "confidence", "parent_demand", "missing_child_segment"],
        ascending=[True, False, False, True, True],
    ).drop(columns=["_evidence_sort"]).drop_duplicates(
        ["parent_demand", "missing_child_segment"]
    ).reset_index(drop=True)


def score_priority(score: float) -> str:
    if score >= 80:
        return "P1"
    if score >= 70:
        return "P2"
    if score >= 60:
        return "P3"
    return "Watchlist"


def build_portfolio_roadmap(whitespace_analysis: pd.DataFrame) -> pd.DataFrame:
    if whitespace_analysis.empty:
        return pd.DataFrame(columns=ROADMAP_COLUMNS)

    candidates = whitespace_analysis[
        whitespace_analysis["evidence_level"].isin(["Strong Evidence", "Moderate Evidence"])
        & (whitespace_analysis["expected_value"] >= 70)
    ].copy()
    if candidates.empty:
        return pd.DataFrame(columns=ROADMAP_COLUMNS)

    candidates["priority"] = candidates["expected_value"].apply(score_priority)
    candidates = candidates.sort_values(
        ["priority", "expected_value", "confidence", "parent_demand", "missing_child_segment"],
        ascending=[True, False, False, True, True],
        key=lambda series: series.map(PRIORITY_ORDER) if series.name == "priority" else series,
    ).drop_duplicates("missing_child_segment")
    candidates = candidates.head(52).reset_index(drop=True)

    rows = []
    for index, row in candidates.iterrows():
        reason = (
            f"{clean_text(row['evidence_level'])}; expected value "
            f"{round(numeric(row['expected_value']), 2)}. {clean_text(row['confidence_reason'])}"
        )
        rows.append(
            {
                "week": f"Week {index + 1}",
                "parent_demand": clean_text(row["parent_demand"]),
                "child_segment": clean_text(row["missing_child_segment"]),
                "product": clean_text(row.get("recommended_product")),
                "customization": clean_text(row.get("recommended_customization")),
                "priority": clean_text(row["priority"]),
                "reason": reason,
            }
        )
    return pd.DataFrame(rows, columns=ROADMAP_COLUMNS)


def top_unique_values(group: pd.DataFrame, column: str, score_columns: list[str] | None = None) -> str:
    if group.empty or column not in group.columns:
        return ""
    values = group[column].map(clean_text)
    values = values[values != ""]
    if values.empty:
        return ""
    if score_columns:
        rows = []
        for value in sorted(values.unique()):
            matching = group[group[column].map(clean_text) == value]
            max_score = matching[score_columns].max(axis=1).max()
            count = len(matching)
            rows.append((value, count, numeric(max_score)))
        rows = sorted(rows, key=lambda item: (-item[2], -item[1], item[0]))
        return " | ".join(item[0] for item in rows[:3])
    counts = values.value_counts()
    return " | ".join(counts.head(3).index.tolist())


def build_portfolio_summary(
    portfolio_master: pd.DataFrame,
    scoring_context: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    for _, portfolio in portfolio_master.iterrows():
        parent = clean_text(portfolio["parent_demand"])
        group = scoring_context[scoring_context["parent_demand"] == parent]
        current = int(portfolio["child_segment_count"])
        coverage = numeric(portfolio["coverage_score"])
        estimated_total = current if coverage <= 0 else max(current, int(round(current / (coverage / 100.0))))
        best_products = top_unique_values(
            group,
            "best_product",
            [
                column
                for column in [
                    "card_score",
                    "blanket_score",
                    "mug_score",
                    "tumbler_score",
                    "shirt_score",
                    "ornament_score",
                    "canvas_score",
                ]
                if column in group.columns
            ],
        )
        strongest_customization = top_unique_values(
            group,
            "best_customization",
            ["photo", "name", "multiple_names", "birth_flower", "clipart", "line_art", "hand_drawing"],
        )
        if clean_text(portfolio["investment_recommendation"]) == "Invest Aggressively":
            next_recommendation = "Research the top child niches immediately and reserve capacity for whitespace tests."
        elif clean_text(portfolio["investment_recommendation"]) == "Expand":
            next_recommendation = "Expand through the highest scoring child segments before adding lower-evidence ideas."
        elif clean_text(portfolio["investment_recommendation"]) == "Maintain":
            next_recommendation = "Maintain active winners and refresh products only where fit scores are strongest."
        elif clean_text(portfolio["investment_recommendation"]) == "Exit":
            next_recommendation = "Do not allocate new research capacity unless future ABA evidence improves."
        else:
            next_recommendation = "Monitor the next import and keep only lightweight validation work."
        rows.append(
            {
                "parent_demand": parent,
                "current_child_segments": current,
                "estimated_total_segments": estimated_total,
                "coverage_percent": coverage,
                "average_score": numeric(portfolio["average_opportunity_score"]),
                "best_products": best_products,
                "strongest_customization": strongest_customization,
                "next_recommendation": next_recommendation,
            }
        )
    return pd.DataFrame(rows, columns=SUMMARY_COLUMNS)


def write_csv(frame: pd.DataFrame, output_dir: Path, key: str) -> None:
    path = output_dir / OUTPUT_FILES[key]
    frame.to_csv(path, index=False)
    print(f"Exported {display_path(path)}: {len(frame):,} rows")


def print_top_sections(
    portfolio_master: pd.DataFrame,
    whitespace_analysis: pd.DataFrame,
    portfolio_roadmap: pd.DataFrame,
) -> None:
    print("\nTop Portfolios")
    print(
        portfolio_master[
            [
                "portfolio_id",
                "parent_demand",
                "market_size",
                "child_segment_count",
                "average_opportunity_score",
                "best_child_score",
                "expansion_potential",
                "research_priority",
                "investment_recommendation",
            ]
        ]
        .head(20)
        .to_string(index=False)
    )

    accepted = whitespace_analysis[
        whitespace_analysis["evidence_level"].isin(["Strong Evidence", "Moderate Evidence"])
    ].copy()
    hypotheses = whitespace_analysis[whitespace_analysis["evidence_level"] == "Hypothesis"].copy()

    print("\nTop 20 accepted whitespace opportunities")
    print(
        accepted[
            [
                "parent_demand",
                "missing_child_segment",
                "evidence_level",
                "match_type",
                "confidence",
                "expected_value",
                "confidence_reason",
            ]
        ]
        .head(20)
        .to_string(index=False)
    )

    print("\nTop 20 hypothesis-only opportunities")
    print(
        hypotheses[
            [
                "parent_demand",
                "missing_child_segment",
                "evidence_level",
                "match_type",
                "confidence",
                "expected_value",
                "reason",
            ]
        ]
        .head(20)
        .to_string(index=False)
    )

    print("\nCount by evidence_level")
    print(whitespace_analysis["evidence_level"].value_counts().to_string())

    print("\nCount by match_type")
    print(whitespace_analysis["match_type"].value_counts().to_string())

    print("\nTop Weekly Research Plan")
    print(
        portfolio_roadmap[
            [
                "week",
                "parent_demand",
                "child_segment",
                "product",
                "customization",
                "priority",
                "reason",
            ]
        ]
        .head(20)
        .to_string(index=False)
    )


def build_portfolio_intelligence(output_dir: Path, rebuild: bool) -> None:
    ensure_rebuild_allowed(output_dir, rebuild)
    output_dir.mkdir(parents=True, exist_ok=True)
    if rebuild:
        remove_portfolio_outputs(output_dir)

    opportunity_scorecard = read_required_csv("opportunity_scorecard")
    product_fit = read_required_csv("product_fit_matrix")
    customization_fit = read_required_csv("customization_fit_matrix")
    reasoning = read_required_csv("research_reasoning")
    segments = read_required_csv("segments")
    market_scorecard = read_required_csv("market_scorecard")

    scoring_context = merge_scoring_context(
        opportunity_scorecard,
        product_fit,
        customization_fit,
        reasoning,
        segments,
    )
    portfolio_master = build_portfolio_master(scoring_context, market_scorecard)
    portfolio_tree = build_portfolio_tree(scoring_context)
    whitespace_analysis = build_whitespace_analysis(portfolio_master, scoring_context, segments)
    portfolio_roadmap = build_portfolio_roadmap(whitespace_analysis)
    portfolio_summary = build_portfolio_summary(portfolio_master, scoring_context)

    write_csv(portfolio_master, output_dir, "portfolio_master")
    write_csv(portfolio_tree, output_dir, "portfolio_tree")
    write_csv(whitespace_analysis, output_dir, "whitespace_analysis")
    write_csv(portfolio_roadmap, output_dir, "portfolio_roadmap")
    write_csv(portfolio_summary, output_dir, "portfolio_summary")
    print_top_sections(portfolio_master, whitespace_analysis, portfolio_roadmap)


def main() -> None:
    args = parse_args()
    build_portfolio_intelligence(output_dir=args.output_dir.resolve(), rebuild=args.rebuild)


if __name__ == "__main__":
    main()
