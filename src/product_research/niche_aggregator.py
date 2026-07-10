"""Aggregate classified product-research search terms by niche."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_ROOT = PROJECT_ROOT / "data" / "product_research" / "output"


def _ensure_month_order(frame: pd.DataFrame) -> pd.DataFrame:
    ordered = frame.copy()
    ordered["month"] = ordered["month"].astype(str)
    sort_columns = [column for column in ["category", "niche_id", "month", "search_term", "search_frequency_rank"] if column in ordered.columns]
    ordered = ordered.sort_values(sort_columns, na_position="last")
    return ordered


def _best_rank(value: pd.Series) -> float | int | None:
    if value.empty:
        return None
    best = value.min()
    if pd.isna(best):
        return None
    return best


def build_niche_outputs(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    classified = frame.copy()
    classified["month"] = classified["month"].astype(str)
    classified = classified[classified["niche_id"].notna()].copy()

    if classified.empty:
        empty_summary = pd.DataFrame(
            columns=[
                "category",
                "niche_id",
                "niche",
                "month_count",
                "latest_month",
                "latest_rank",
                "best_rank",
                "average_rank",
                "average_search_frequency_rank",
                "first_month_seen",
                "peak_month",
                "total_search_terms",
                "matched_search_terms",
            ]
        )
        empty_monthly = pd.DataFrame(
            columns=["category", "niche_id", "niche", "month", "best_rank", "average_rank", "search_term_count"]
        )
        empty_detail = frame.copy()
        return empty_summary, empty_monthly, empty_detail

    classified["search_frequency_rank"] = pd.to_numeric(classified["search_frequency_rank"], errors="coerce")

    monthly = (
        classified.groupby(["category", "niche_id", "niche", "month"], as_index=False)
        .agg(
            best_rank=("search_frequency_rank", "min"),
            average_rank=("search_frequency_rank", "mean"),
            search_term_count=("search_term", "nunique"),
        )
        .sort_values(["category", "niche_id", "month"], ascending=[True, True, True], na_position="last")
    )

    summary_rows: list[dict[str, object]] = []
    for (category, niche_id, niche), niche_rows in classified.groupby(["category", "niche_id", "niche"], sort=True):
        niche_rows = niche_rows.sort_values(["month", "search_frequency_rank", "search_term"], na_position="last")
        month_values = sorted({str(value) for value in niche_rows["month"].dropna().astype(str)})
        latest_month = month_values[-1] if month_values else None
        first_month_seen = month_values[0] if month_values else None

        latest_rows = niche_rows[niche_rows["month"] == latest_month] if latest_month is not None else niche_rows.iloc[0:0]
        latest_rank = _best_rank(latest_rows["search_frequency_rank"])

        best_rank = _best_rank(niche_rows["search_frequency_rank"])
        average_rank = (
            float(niche_rows["search_frequency_rank"].mean())
            if not niche_rows["search_frequency_rank"].dropna().empty
            else None
        )

        monthly_slice = monthly[monthly["niche_id"] == niche_id].copy()
        if monthly_slice.empty:
            peak_month = None
        else:
            monthly_slice = monthly_slice.sort_values(
                ["average_rank", "month"], ascending=[True, True], na_position="last"
            )
            peak_month = monthly_slice.iloc[0]["month"]

        summary_rows.append(
            {
                "category": category,
                "niche_id": niche_id,
                "niche": niche,
                "month_count": int(niche_rows["month"].nunique()),
                "latest_month": latest_month,
                "latest_rank": latest_rank,
                "best_rank": best_rank,
                "average_rank": average_rank,
                "average_search_frequency_rank": average_rank,
                "first_month_seen": first_month_seen,
                "peak_month": peak_month,
                "total_search_terms": int(niche_rows["search_term"].nunique()),
                "matched_search_terms": int(len(niche_rows)),
            }
        )

    summary = pd.DataFrame(summary_rows).sort_values(
        ["best_rank", "average_rank", "category", "niche_id"], ascending=[True, True, True, True], na_position="last"
    )

    detail = _ensure_month_order(frame)

    return summary.reset_index(drop=True), monthly.reset_index(drop=True), detail.reset_index(drop=True)


def export_niche_outputs(frame: pd.DataFrame, product: str) -> tuple[Path, Path, Path]:
    output_dir = OUTPUT_ROOT / product
    output_dir.mkdir(parents=True, exist_ok=True)

    summary, monthly, detail = build_niche_outputs(frame)

    summary_path = output_dir / f"{product}_niche_summary.parquet"
    monthly_path = output_dir / f"{product}_niche_monthly.parquet"
    detail_path = output_dir / f"{product}_niche_search_terms.parquet"

    summary.to_parquet(summary_path, index=False)
    monthly.to_parquet(monthly_path, index=False)
    detail.to_parquet(detail_path, index=False)

    return summary_path, monthly_path, detail_path
