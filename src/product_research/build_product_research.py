"""CLI entrypoint for the product research import engine."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pandas as pd

from importer import OUTPUT_ROOT, build_historical_search_terms
from dashboard_builder import export_dashboard
from niche_aggregator import export_niche_outputs
from niche_classifier import classify_search_terms


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = PROJECT_ROOT / "logs"
LOG_PATH = LOG_DIR / "build_product_research.log"

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the product research historical search terms dataset."
    )
    parser.add_argument(
        "--product",
        required=True,
        help="Product folder name under data/product_research/raw/ and output/.",
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


def log_validation(frame: pd.DataFrame) -> None:
    total_search_terms = int(len(frame))
    matched = frame[frame["niche_id"].notna()].copy()
    matched_rows = int(len(matched))
    matched_niches = int(matched["niche_id"].nunique()) if not matched.empty else 0
    matched_categories = int(matched["category"].nunique()) if not matched.empty and "category" in matched.columns else 0

    logger.info("Total search terms: %s", f"{total_search_terms:,}")
    logger.info("Matched rows: %s", f"{matched_rows:,}")
    logger.info("Matched niches: %s", f"{matched_niches:,}")
    logger.info("Matched categories: %s", f"{matched_categories:,}")

    if matched.empty:
        logger.info("Top 20 niches by matched search terms: none")
        logger.info("Top 20 categories by matched search terms: none")
        return

    pattern_counts = (
        matched.groupby("matched_pattern", as_index=False)
        .agg(matched_rows=("search_term", "size"))
        .sort_values(["matched_rows", "matched_pattern"], ascending=[False, True], na_position="last")
        .head(30)
    )
    niche_counts = (
        matched.groupby(["category", "niche_id", "niche"], as_index=False)
        .agg(matched_rows=("search_term", "size"))
        .sort_values(["matched_rows", "category", "niche"], ascending=[False, True, True], na_position="last")
        .head(30)
    )
    category_counts = (
        matched.groupby("category", as_index=False)
        .agg(matched_rows=("search_term", "size"))
        .sort_values(["matched_rows", "category"], ascending=[False, True], na_position="last")
        .head(30)
    )

    logger.info("Top 30 matched_pattern values:\n%s", pattern_counts.to_string(index=False))
    logger.info("Matched rows per pattern:\n%s", pattern_counts.to_string(index=False))
    logger.info("Matched rows per niche:\n%s", niche_counts.to_string(index=False))
    logger.info("Matched rows per category:\n%s", category_counts.to_string(index=False))


def main() -> None:
    configure_logging()
    args = parse_args()

    output_dir = OUTPUT_ROOT / args.product
    output_dir.mkdir(parents=True, exist_ok=True)

    merged = build_historical_search_terms(args.product)

    historical_parquet_path = output_dir / "historical_search_terms.parquet"
    historical_csv_path = output_dir / "historical_search_terms.csv"
    niche_parquet_path = output_dir / "historical_search_terms_with_niche.parquet"

    merged.to_parquet(historical_parquet_path, index=False)
    merged.to_csv(historical_csv_path, index=False, encoding="utf-8")

    classified = classify_search_terms(merged, product=args.product, search_term_column="search_term")
    classified.to_parquet(niche_parquet_path, index=False)

    summary_path, monthly_path, detail_path = export_niche_outputs(classified, args.product)
    dashboard_path = export_dashboard(args.product)

    row_count = len(merged)
    logger.info("Wrote %s rows to %s", f"{row_count:,}", historical_parquet_path.relative_to(PROJECT_ROOT))
    logger.info("Wrote %s rows to %s", f"{row_count:,}", historical_csv_path.relative_to(PROJECT_ROOT))
    logger.info("Wrote %s rows to %s", f"{row_count:,}", niche_parquet_path.relative_to(PROJECT_ROOT))
    logger.info("Wrote niche summary to %s", summary_path.relative_to(PROJECT_ROOT))
    logger.info("Wrote niche monthly rollup to %s", monthly_path.relative_to(PROJECT_ROOT))
    logger.info("Wrote niche search-term detail to %s", detail_path.relative_to(PROJECT_ROOT))
    logger.info("Wrote dashboard dataset to %s", dashboard_path.relative_to(PROJECT_ROOT))
    log_validation(classified)


if __name__ == "__main__":
    main()
