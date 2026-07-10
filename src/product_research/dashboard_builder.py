"""Build the final product-research dashboard dataset."""

from __future__ import annotations

import math
import logging
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_ROOT = PROJECT_ROOT / "data" / "product_research" / "output"
logger = logging.getLogger(__name__)

PUBLIC_COLUMNS = [
    "dashboard_rank",
    "niche",
    "demand_size",
    "trend",
    "peak_month",
    "key_insight",
]

DEMAND_SIZE_FORMULA = "rank_curve_v2_best_rank_log_power_decay"
POSITION_DECAY_EXPONENT = 0.35
RANK_CURVE_AUDIT_TOP_AVERAGES = [3, 5, 10]
RANK_CURVE_AUDIT_COLUMNS = [
    "niche",
    "demand_index",
    "demand_size",
    "top_1_best_rank",
    "top_3_average_rank",
    "top_5_average_rank",
    "top_10_average_rank",
    "search_term_count",
]


def _read_inputs(product: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    output_dir = OUTPUT_ROOT / product
    summary_path = output_dir / f"{product}_niche_summary.parquet"
    monthly_path = output_dir / f"{product}_niche_monthly.parquet"
    detail_path = output_dir / f"{product}_niche_search_terms.parquet"

    if not summary_path.exists():
        raise FileNotFoundError(f"Missing required input parquet: {summary_path}")
    if not monthly_path.exists():
        raise FileNotFoundError(f"Missing required input parquet: {monthly_path}")
    if not detail_path.exists():
        raise FileNotFoundError(f"Missing required input parquet: {detail_path}")

    summary = pd.read_parquet(summary_path)
    monthly = pd.read_parquet(monthly_path)
    detail = pd.read_parquet(detail_path)
    return summary, monthly, detail


def _rank_score(rank: object, cap: float = 1_000_000.0) -> float:
    value = pd.to_numeric(pd.Series([rank]), errors="coerce").iloc[0]
    if pd.isna(value) or value <= 0:
        return 0.0

    scaled = math.log10(min(float(value), cap)) / math.log10(cap)
    return max(0.0, min(1.0, 1.0 - scaled))


def _count_score(value: object, maximum: int) -> float:
    numeric_value = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric_value) or maximum <= 0:
        return 0.0

    numerator = math.log1p(float(max(0.0, numeric_value)))
    denominator = math.log1p(float(maximum))
    if denominator <= 0:
        return 0.0

    return max(0.0, min(1.0, numerator / denominator))


def _numeric_value(value: object, default: float = 0.0) -> float:
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric):
        return default
    return float(numeric)


def _min_max_normalize(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    valid = numeric.dropna()
    if valid.empty:
        return pd.Series([0.0] * len(series), index=series.index, dtype=float)

    minimum = float(valid.min())
    maximum = float(valid.max())
    if math.isclose(minimum, maximum):
        return pd.Series([0.0] * len(series), index=series.index, dtype=float)

    normalized = (numeric - minimum) / (maximum - minimum)
    return normalized.fillna(0.0).clip(0.0, 1.0)


def _position_weight(position: object) -> float:
    numeric = pd.to_numeric(pd.Series([position]), errors="coerce").iloc[0]
    if pd.isna(numeric) or float(numeric) <= 0:
        return 0.0
    return float(int(numeric) ** -POSITION_DECAY_EXPONENT)


def _rank_curve_search_term_metrics(detail: pd.DataFrame) -> pd.DataFrame:
    if detail.empty:
        return pd.DataFrame(
            columns=[
                "niche_id",
                "niche",
                "demand_index",
                "search_term_count",
                "top_1_best_rank",
                *[f"top_{position}_average_rank" for position in RANK_CURVE_AUDIT_TOP_AVERAGES],
            ]
        )

    ranked = detail.copy()
    ranked["search_frequency_rank"] = pd.to_numeric(ranked["search_frequency_rank"], errors="coerce")
    ranked = ranked[
        ranked["niche_id"].notna()
        & ranked["niche"].notna()
        & ranked["search_term"].notna()
        & ranked["search_frequency_rank"].notna()
        & (ranked["search_frequency_rank"] > 0)
    ].copy()
    if ranked.empty:
        return pd.DataFrame(
            columns=[
                "niche_id",
                "niche",
                "demand_index",
                "search_term_count",
                "top_1_best_rank",
                *[f"top_{position}_average_rank" for position in RANK_CURVE_AUDIT_TOP_AVERAGES],
            ]
        )

    if "month_index" in ranked.columns:
        ranked["month_index"] = pd.to_numeric(ranked["month_index"], errors="coerce")
    if "reporting_date" in ranked.columns:
        ranked["reporting_date"] = pd.to_datetime(ranked["reporting_date"], errors="coerce")
    if "month" in ranked.columns:
        ranked["month"] = ranked["month"].astype(str)

    term_sort_columns = [
        column
        for column in ["niche_id", "niche", "search_term", "month_index", "reporting_date", "month"]
        if column in ranked.columns
    ]
    ranked = ranked.sort_values(term_sort_columns, ascending=[True] * len(term_sort_columns), na_position="last")

    term_metrics = (
        ranked.groupby(["niche_id", "niche", "search_term"], as_index=False)
        .agg(
            best_rank=("search_frequency_rank", "min"),
            latest_rank=("search_frequency_rank", "last"),
        )
        .copy()
    )
    term_metrics = term_metrics.sort_values(
        ["niche_id", "best_rank", "latest_rank", "search_term"],
        ascending=[True, True, True, True],
        na_position="last",
    )
    term_metrics["term_position"] = term_metrics.groupby("niche_id").cumcount() + 1
    term_metrics["keyword_score"] = term_metrics["best_rank"].apply(_rank_score)
    term_metrics["position_weight"] = term_metrics["term_position"].apply(_position_weight)
    term_metrics["weighted_keyword_score"] = term_metrics["position_weight"] * term_metrics["keyword_score"]

    aggregated = (
        term_metrics.groupby(["niche_id", "niche"], as_index=False)
        .agg(
            search_term_count=("search_term", "nunique"),
            demand_index=("weighted_keyword_score", "sum"),
        )
        .copy()
    )

    top_1 = (
        term_metrics[term_metrics["term_position"] == 1][["niche_id", "niche", "best_rank"]]
        .rename(columns={"best_rank": "top_1_best_rank"})
        .copy()
    )
    aggregated = aggregated.merge(top_1, on=["niche_id", "niche"], how="left")

    for position in RANK_CURVE_AUDIT_TOP_AVERAGES:
        column = f"top_{position}_average_rank"
        top_average = (
            term_metrics[term_metrics["term_position"] <= position]
            .groupby(["niche_id", "niche"], as_index=False)
            .agg(**{column: ("best_rank", "mean")})
        )
        aggregated = aggregated.merge(top_average, on=["niche_id", "niche"], how="left")

    return aggregated


def _demand_size(summary: pd.DataFrame, detail: pd.DataFrame) -> pd.DataFrame:
    scored = summary.copy()
    term_metrics = _rank_curve_search_term_metrics(detail)

    if term_metrics.empty:
        scored["demand_index"] = 0.0
        scored["search_term_count"] = scored["total_search_terms"].fillna(0)
        scored["unique_search_terms"] = scored["search_term_count"]
        scored["top_1_best_rank"] = pd.NA
        for position in RANK_CURVE_AUDIT_TOP_AVERAGES:
            scored[f"top_{position}_average_rank"] = pd.NA
    else:
        scored = scored.merge(
            term_metrics,
            on=["niche_id", "niche"],
            how="left",
            suffixes=("", "_term"),
        )
        scored["demand_index"] = scored["demand_index"].fillna(0.0)
        scored["search_term_count"] = scored["search_term_count"].fillna(scored["total_search_terms"]).fillna(0)
        scored["unique_search_terms"] = scored["search_term_count"]
        if "top_1_best_rank" not in scored.columns:
            scored["top_1_best_rank"] = pd.NA
        for position in RANK_CURVE_AUDIT_TOP_AVERAGES:
            column = f"top_{position}_average_rank"
            if column not in scored.columns:
                scored[column] = pd.NA

    for column in ["search_term_count", "unique_search_terms", "month_count"]:
        scored[column] = pd.to_numeric(scored[column], errors="coerce").fillna(0).astype(int)
    scored["top_1_best_rank"] = pd.to_numeric(scored["top_1_best_rank"], errors="coerce")
    for position in RANK_CURVE_AUDIT_TOP_AVERAGES:
        column = f"top_{position}_average_rank"
        scored[column] = pd.to_numeric(scored[column], errors="coerce")

    scored["demand_index_norm"] = _min_max_normalize(scored["demand_index"])
    scored["demand_size"] = (scored["demand_index_norm"] * 100.0).round(2)
    scored["demand_strength"] = scored["demand_size"]
    scored["demand_strength_label"] = scored["demand_size"].apply(_label_strength)
    return scored


def _export_demand_size_audit(scored: pd.DataFrame, output_dir: Path) -> Path:
    legacy_audit_path = output_dir / "demand_size_audit.csv"
    rank_curve_audit_path = output_dir / "demand_size_rank_curve_audit.csv"
    rank_curve_v2_path = output_dir / "demand_size_rank_curve_v2.csv"
    legacy_columns = [
        "niche",
        "demand_index",
        "unique_search_terms",
        "month_count",
        "demand_size",
    ]
    legacy_available = [column for column in legacy_columns if column in scored.columns]
    sorted_scored = scored.sort_values(
        "demand_index",
        ascending=False,
        na_position="last",
    )
    legacy_audit = sorted_scored[legacy_available].copy()
    legacy_audit.to_csv(legacy_audit_path, index=False, encoding="utf-8")

    rank_curve_available = [column for column in RANK_CURVE_AUDIT_COLUMNS if column in scored.columns]
    rank_curve_audit = sorted_scored[rank_curve_available].copy()
    rank_curve_audit.to_csv(rank_curve_audit_path, index=False, encoding="utf-8")
    rank_curve_audit.to_csv(rank_curve_v2_path, index=False, encoding="utf-8")
    logger.info("Wrote demand size audit to %s", legacy_audit_path.relative_to(PROJECT_ROOT))
    logger.info("Wrote demand size rank curve audit to %s", rank_curve_audit_path.relative_to(PROJECT_ROOT))
    logger.info("Wrote demand size rank curve v2 audit to %s", rank_curve_v2_path.relative_to(PROJECT_ROOT))
    return rank_curve_v2_path


def _audit_demand_size(scored: pd.DataFrame) -> None:
    if scored.empty:
        logger.info("Demand Size formula: %s", DEMAND_SIZE_FORMULA)
        logger.info("Demand Size audit: no rows available")
        return

    audit_columns = [column for column in RANK_CURVE_AUDIT_COLUMNS if column in scored.columns]
    top_rows = scored.sort_values(
        "demand_index",
        ascending=False,
        na_position="last",
    )[audit_columns].head(20)
    logger.info("Demand Size formula: %s", DEMAND_SIZE_FORMULA)
    logger.info("Top 20 niches after Demand Size:\n%s", top_rows.to_string(index=False))


def _label_strength(value: object) -> str:
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric):
        return "Low"
    if numeric >= 80:
        return "Very High"
    if numeric >= 60:
        return "High"
    if numeric >= 40:
        return "Medium"
    return "Low"


def _monthly_history(monthly: pd.DataFrame, niche_id: object) -> pd.DataFrame:
    niche_monthly = monthly[monthly["niche_id"] == niche_id].copy()
    if niche_monthly.empty:
        return niche_monthly

    niche_monthly["month"] = niche_monthly["month"].astype(str)
    niche_monthly["best_rank"] = pd.to_numeric(niche_monthly["best_rank"], errors="coerce")
    niche_monthly["average_rank"] = pd.to_numeric(niche_monthly["average_rank"], errors="coerce")
    niche_monthly["search_term_count"] = pd.to_numeric(niche_monthly["search_term_count"], errors="coerce")
    return niche_monthly.sort_values("month", ascending=True, na_position="last")


def _trend_for_history(history: pd.DataFrame) -> str:
    if history.empty or len(history) < 3:
        return "Stable"

    ranks = history["best_rank"].dropna().tolist()
    if len(ranks) < 3:
        return "Stable"

    first_rank = float(ranks[0])
    last_rank = float(ranks[-1])
    if first_rank <= 0:
        return "Stable"

    change = (first_rank - last_rank) / first_rank

    step_signs: list[int] = []
    for previous, current in zip(ranks, ranks[1:]):
        if pd.isna(previous) or pd.isna(current):
            continue
        if current < previous:
            step_signs.append(1)
        elif current > previous:
            step_signs.append(-1)

    if not step_signs:
        return "Stable"

    positive_steps = sum(1 for sign in step_signs if sign > 0)
    negative_steps = sum(1 for sign in step_signs if sign < 0)
    total_steps = len(step_signs)
    dominant_consistency = max(positive_steps, negative_steps) / total_steps

    if change >= 0.30 and positive_steps == total_steps and dominant_consistency >= 0.75:
        return "Strong Up"
    if change >= 0.10 and positive_steps >= math.ceil(total_steps * 0.67):
        return "Up"
    if change <= -0.30 and negative_steps == total_steps and dominant_consistency >= 0.75:
        return "Strong Down"
    if change <= -0.10 and negative_steps >= math.ceil(total_steps * 0.67):
        return "Down"
    return "Stable"


def _is_seasonal(history: pd.DataFrame) -> bool:
    if history.empty or len(history) < 2:
        return False

    total_rows = float(history["search_term_count"].sum())
    if total_rows <= 0:
        return False

    peak_share = float(history["search_term_count"].max()) / total_rows
    return peak_share >= 0.50


def _key_insight(row: pd.Series, history: pd.DataFrame) -> str:
    month_count = int(_numeric_value(row.get("month_count"), 0.0))
    demand_size = _numeric_value(row.get("demand_size"), 0.0)
    trend = str(row.get("trend") or "Stable")

    if _is_seasonal(history):
        peak_month = str(history.sort_values(["search_term_count", "month"], ascending=[False, True]).iloc[0]["month"])
        return f"Seasonal niche concentrated in {peak_month}."

    if trend in {"Strong Up", "Up"} and month_count >= 3:
        if _coverage_is_expanding(history):
            return "Growing niche with expanding keyword coverage."
        return "Growing niche with improving search visibility."

    if demand_size >= 70 and trend in {"Down", "Strong Down"}:
        return "High demand but declining search visibility."

    if demand_size >= 70 and trend == "Stable" and month_count >= 3:
        return "Consistent high-demand niche across observed months."

    if _coverage_is_expanding(history):
        return "Growing niche with expanding keyword coverage."

    return "Stable niche with limited directional movement."


def _coverage_is_expanding(history: pd.DataFrame) -> bool:
    if history.empty or len(history) < 2:
        return False

    first_count = float(history.iloc[0]["search_term_count"])
    last_count = float(history.iloc[-1]["search_term_count"])
    if first_count <= 0:
        return False

    return last_count >= first_count * 1.20


def build_dashboard(product: str) -> pd.DataFrame:
    summary, monthly, detail = _read_inputs(product)
    if summary.empty:
        return pd.DataFrame(columns=PUBLIC_COLUMNS)

    scored = _build_scored_dashboard(summary, monthly, detail)
    dashboard = scored[PUBLIC_COLUMNS].copy()
    return dashboard


def _build_scored_dashboard(summary: pd.DataFrame, monthly: pd.DataFrame, detail: pd.DataFrame) -> pd.DataFrame:
    scored = _demand_size(summary, detail)
    _audit_demand_size(scored)
    trend_map: dict[object, str] = {}
    insight_map: dict[object, str] = {}

    for _, row in scored.iterrows():
        niche_id = row["niche_id"]
        history = _monthly_history(monthly, niche_id)
        trend = _trend_for_history(history)
        trend_map[niche_id] = trend
        insight_map[niche_id] = _key_insight(row, history)

    scored["trend"] = scored["niche_id"].map(trend_map).fillna("Stable")
    scored["key_insight"] = scored["niche_id"].map(insight_map).fillna("Stable niche with limited directional movement.")

    scored = scored.sort_values(
        "demand_index",
        ascending=False,
        na_position="last",
    ).reset_index(drop=True)
    scored.insert(0, "dashboard_rank", range(1, len(scored) + 1))
    return scored


def export_dashboard(product: str) -> Path:
    output_dir = OUTPUT_ROOT / product
    output_dir.mkdir(parents=True, exist_ok=True)

    summary, monthly, detail = _read_inputs(product)
    if summary.empty:
        dashboard = pd.DataFrame(columns=PUBLIC_COLUMNS)
        audit = pd.DataFrame(
            columns=[
                "niche",
                "demand_index",
                "demand_size",
                "top_1_best_rank",
                "top_3_average_rank",
                "top_5_average_rank",
                "top_10_average_rank",
                "search_term_count",
            ]
        )
    else:
        scored = _build_scored_dashboard(summary, monthly, detail)
        dashboard = scored[PUBLIC_COLUMNS].copy()
        audit = scored

    dashboard_path = output_dir / f"{product}_dashboard.parquet"
    audit_path = _export_demand_size_audit(audit, output_dir)
    dashboard.to_parquet(dashboard_path, index=False)
    return dashboard_path
