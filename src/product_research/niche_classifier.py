"""Simple niche classifier for product research search terms."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TAXONOMY_DIR = PROJECT_ROOT / "config" / "product_research"
NON_ALNUM_PATTERN = re.compile(r"[^a-z0-9]+")
MULTISPACE_PATTERN = re.compile(r"\s+")


@dataclass(frozen=True)
class NichePattern:
    category: str
    niche_id: str
    niche: str
    priority: int
    pattern: str

    @property
    def normalized_pattern(self) -> str:
        return normalize_text(self.pattern)


def normalize_text(value: object) -> str:
    text = str(value).strip().lower()
    text = text.replace("&", " and ")
    text = NON_ALNUM_PATTERN.sub(" ", text)
    text = MULTISPACE_PATTERN.sub(" ", text).strip()
    return text


def taxonomy_path(product: str) -> Path:
    return TAXONOMY_DIR / f"{product}_niche_dictionary.csv"


def split_aliases(value: object) -> list[str]:
    values = []
    for alias in str(value).split(";"):
        cleaned = alias.strip()
        if cleaned:
            values.append(cleaned)
    return values


def load_niche_dictionary(product: str) -> list[NichePattern]:
    path = taxonomy_path(product)
    if not path.exists():
        raise FileNotFoundError(f"Missing niche dictionary: {path}")

    patterns: list[NichePattern] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required_columns = {"category", "niche_id", "niche", "aliases"}
        if reader.fieldnames is None or not required_columns.issubset(reader.fieldnames):
            raise RuntimeError(
                f"{path} must contain columns: category,niche_id,niche,aliases"
            )

        for priority, row in enumerate(reader, start=1):
            category = str(row.get("category", "")).strip()
            niche_id = str(row.get("niche_id", "")).strip()
            niche = str(row.get("niche", "")).strip()
            aliases = split_aliases(row.get("aliases", ""))
            if not category or not niche_id or not niche:
                continue
            for alias in aliases:
                pattern = normalize_text(alias)
                if not pattern:
                    continue
                patterns.append(
                    NichePattern(
                        category=category,
                        niche_id=niche_id,
                        niche=niche,
                        priority=priority,
                        pattern=alias,
                    )
                )

    return patterns


def ordered_patterns(patterns: Iterable[NichePattern]) -> list[NichePattern]:
    return sorted(
        patterns,
        key=lambda item: (
            item.priority,
            -len(item.normalized_pattern),
            item.category,
            item.niche_id,
            item.pattern,
        ),
    )


def classify_search_term(
    search_term: object,
    patterns: Iterable[NichePattern],
) -> dict[str, str | None]:
    normalized_search_term = normalize_text(search_term)
    ordered = ordered_patterns(patterns)

    for pattern in ordered:
        if normalized_search_term == pattern.normalized_pattern:
            return {
                "category": pattern.category,
                "niche_id": pattern.niche_id,
                "niche": pattern.niche,
                "matched_pattern": pattern.pattern,
                "match_type": "exact",
            }

    for pattern in ordered:
        if pattern.normalized_pattern and pattern.normalized_pattern in normalized_search_term:
            return {
                "category": pattern.category,
                "niche_id": pattern.niche_id,
                "niche": pattern.niche,
                "matched_pattern": pattern.pattern,
                "match_type": "substring",
            }

    return {
        "category": None,
        "niche_id": None,
        "niche": None,
        "matched_pattern": None,
        "match_type": "unmatched",
    }


def classify_search_terms(
    frame: pd.DataFrame,
    product: str = "ornament",
    search_term_column: str = "search_term",
    patterns: Iterable[NichePattern] | None = None,
) -> pd.DataFrame:
    classified = frame.copy()
    active_patterns = list(patterns) if patterns is not None else load_niche_dictionary(product)
    results = classified[search_term_column].map(lambda value: classify_search_term(value, active_patterns))
    result_frame = pd.DataFrame(list(results))
    for column in result_frame.columns:
        classified[column] = result_frame[column].values
    return classified
