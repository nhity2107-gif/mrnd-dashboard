"""Streamlit Demand Decision Dashboard for MRnD intelligence outputs."""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Iterable

import altair as alt
import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_ROOT = PROJECT_ROOT / "data" / "output"

CSV_FILES = {
    "market_intelligence": OUTPUT_ROOT / "intelligence" / "market_intelligence.csv",
    "demand_intelligence": OUTPUT_ROOT / "intelligence" / "demand_intelligence.csv",
    "market_scorecard": OUTPUT_ROOT / "decision" / "market_scorecard.csv",
    "research_candidates": OUTPUT_ROOT / "decision" / "research_candidates.csv",
    "product_recommendation": OUTPUT_ROOT / "decision" / "product_recommendation.csv",
    "customization_recommendation": OUTPUT_ROOT / "decision" / "customization_recommendation.csv",
    "market_calendar": OUTPUT_ROOT / "decision" / "market_calendar.csv",
    "opportunity_scorecard": OUTPUT_ROOT / "scoring" / "opportunity_scorecard.csv",
    "product_fit_matrix": OUTPUT_ROOT / "scoring" / "product_fit_matrix.csv",
    "customization_fit_matrix": OUTPUT_ROOT / "scoring" / "customization_fit_matrix.csv",
    "research_reasoning": OUTPUT_ROOT / "scoring" / "research_reasoning.csv",
    "portfolio_master": OUTPUT_ROOT / "portfolio" / "portfolio_master.csv",
    "portfolio_summary": OUTPUT_ROOT / "portfolio" / "portfolio_summary.csv",
    "portfolio_roadmap": OUTPUT_ROOT / "portfolio" / "portfolio_roadmap.csv",
    "portfolio_tree": OUTPUT_ROOT / "portfolio" / "portfolio_tree.csv",
    "opportunity_master": OUTPUT_ROOT / "opportunity" / "opportunity_master.csv",
    "demand_segments": OUTPUT_ROOT / "demand_segments" / "demand_segments.csv",
    "top_200_segments": OUTPUT_ROOT / "demand_segments" / "top_200_segments.csv",
    "composite_demands": OUTPUT_ROOT / "composite_demands" / "composite_demands.csv",
    "demand_strength_v3": OUTPUT_ROOT / "composite_demands" / "demand_strength_v3.csv",
    "top_composite_demands": OUTPUT_ROOT / "composite_demands" / "top_composite_demands.csv",
    "market_nodes": OUTPUT_ROOT / "market_nodes" / "market_nodes.csv",
    "demand_evidence_light": OUTPUT_ROOT / "evidence_light" / "demand_evidence_light.csv",
    "segment_evidence_light": OUTPUT_ROOT / "evidence_light" / "segment_evidence_light.csv",
    "market_node_evidence_light": OUTPUT_ROOT / "evidence_light" / "market_node_evidence_light.csv",
}

CORE_FILES = {
    "market_scorecard",
    "research_candidates",
    "opportunity_scorecard",
    "product_fit_matrix",
    "customization_fit_matrix",
    "portfolio_master",
    "portfolio_summary",
    "portfolio_roadmap",
}

RANK_COLUMNS = [
    "best_rank",
    "p25_rank",
    "median_rank",
    "average_rank",
    "search_frequency_rank",
]

SCORE_COLUMNS = [
    "market_size_score",
    "growth_score",
    "competition_score",
    "expansion_score",
    "seasonality_score",
    "product_fit_score",
    "total_score",
    "opportunity_score",
    "overall_score",
    "coverage_score",
    "expansion_potential",
    "average_opportunity_score",
    "best_child_score",
]

PRIORITY_ORDER = {
    "P1": 1,
    "P2": 2,
    "P3": 3,
    "Watchlist": 4,
    "★★★★★": 1,
    "★★★★☆": 2,
    "★★★☆☆": 3,
    "★★☆☆☆": 4,
    "★☆☆☆☆": 5,
}


st.set_page_config(
    page_title="MRnD Executive Intelligence",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)


st.markdown(
    """
    <style>
    :root {
        --mrd-bg: #0f172a;
        --mrd-card: #111827;
        --mrd-table: #0b1220;
        --mrd-accent: #38bdf8;
        --mrd-positive: #22c55e;
        --mrd-warning: #f59e0b;
        --mrd-danger: #ef4444;
        --mrd-text: #e5e7eb;
        --mrd-muted: #9ca3af;
        --mrd-border: rgba(148, 163, 184, 0.22);
    }

    html, body, .stApp {
        background: var(--mrd-bg) !important;
        color: var(--mrd-text) !important;
    }

    .block-container {
        padding-top: 1.25rem;
        padding-bottom: 2rem;
        max-width: 1500px;
    }

    [data-testid="stSidebar"] {
        background: #0b1220 !important;
        border-right: 1px solid var(--mrd-border);
    }

    [data-testid="stSidebar"] * {
        color: var(--mrd-text);
    }

    h1, h2, h3, h4, h5, h6, p, span, label {
        color: var(--mrd-text) !important;
    }

    .mrd-muted, .mrd-muted * {
        color: var(--mrd-muted) !important;
    }

    .mrd-page-title {
        margin-bottom: 0.15rem;
    }

    .mrd-subtitle {
        color: var(--mrd-muted);
        margin-bottom: 1.2rem;
        font-size: 0.96rem;
    }

    .mrd-card {
        background: var(--mrd-card);
        border: 1px solid var(--mrd-border);
        border-radius: 12px;
        padding: 1rem 1.05rem;
        min-height: 104px;
        box-shadow: 0 14px 30px rgba(0, 0, 0, 0.16);
    }

    .mrd-card-label {
        color: var(--mrd-muted);
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-bottom: 0.45rem;
    }

    .mrd-card-value {
        color: var(--mrd-text);
        font-size: 1.8rem;
        line-height: 1.15;
        font-weight: 700;
    }

    .mrd-card-note {
        color: var(--mrd-muted);
        font-size: 0.82rem;
        margin-top: 0.35rem;
    }

    .mrd-accent {
        color: var(--mrd-accent) !important;
    }

    .mrd-badge {
        display: inline-block;
        border-radius: 999px;
        padding: 0.18rem 0.58rem;
        font-size: 0.76rem;
        font-weight: 700;
        border: 1px solid var(--mrd-border);
    }

    .mrd-badge-p1 {
        color: var(--mrd-positive);
        background: rgba(34, 197, 94, 0.12);
        border-color: rgba(34, 197, 94, 0.35);
    }

    .mrd-badge-p2 {
        color: var(--mrd-accent);
        background: rgba(56, 189, 248, 0.12);
        border-color: rgba(56, 189, 248, 0.35);
    }

    .mrd-badge-p3 {
        color: var(--mrd-warning);
        background: rgba(245, 158, 11, 0.12);
        border-color: rgba(245, 158, 11, 0.35);
    }

    .mrd-badge-watch {
        color: var(--mrd-danger);
        background: rgba(239, 68, 68, 0.12);
        border-color: rgba(239, 68, 68, 0.35);
    }

    .mrd-tone-green {
        --mrd-tone: #22c55e;
        --mrd-tone-soft: rgba(34, 197, 94, 0.12);
        --mrd-tone-border: rgba(34, 197, 94, 0.38);
    }

    .mrd-tone-blue {
        --mrd-tone: #38bdf8;
        --mrd-tone-soft: rgba(56, 189, 248, 0.12);
        --mrd-tone-border: rgba(56, 189, 248, 0.38);
    }

    .mrd-tone-amber {
        --mrd-tone: #f59e0b;
        --mrd-tone-soft: rgba(245, 158, 11, 0.12);
        --mrd-tone-border: rgba(245, 158, 11, 0.38);
    }

    .mrd-tone-red {
        --mrd-tone: #ef4444;
        --mrd-tone-soft: rgba(239, 68, 68, 0.12);
        --mrd-tone-border: rgba(239, 68, 68, 0.4);
    }

    .mrd-tone-purple {
        --mrd-tone: #a78bfa;
        --mrd-tone-soft: rgba(167, 139, 250, 0.13);
        --mrd-tone-border: rgba(167, 139, 250, 0.4);
    }

    .mrd-tone-teal {
        --mrd-tone: #2dd4bf;
        --mrd-tone-soft: rgba(45, 212, 191, 0.12);
        --mrd-tone-border: rgba(45, 212, 191, 0.38);
    }

    .mrd-tone-gray {
        --mrd-tone: #94a3b8;
        --mrd-tone-soft: rgba(148, 163, 184, 0.11);
        --mrd-tone-border: rgba(148, 163, 184, 0.28);
    }

    .mrd-portfolio-legend {
        display: inline-block;
        margin: 0.15rem 0 0.75rem;
        padding: 0.55rem 0.7rem;
        border: 1px solid rgba(148, 163, 184, 0.18);
        border-radius: 8px;
        background: rgba(15, 23, 42, 0.55);
        color: var(--mrd-muted);
        font-size: 0.78rem;
        line-height: 1.45;
    }

    .mrd-portfolio-legend strong {
        color: var(--mrd-text);
        font-size: 0.76rem;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }

    .mrd-portfolio-legend ul {
        margin: 0.25rem 0 0;
        padding-left: 1.05rem;
    }

    .mrd-portfolio-card {
        min-height: 218px;
        padding: 0.78rem 0.85rem;
        border: 1px solid var(--mrd-tone-border);
        border-left: 3px solid var(--mrd-tone);
        border-radius: 10px;
        background:
            linear-gradient(145deg, var(--mrd-tone-soft), rgba(17, 24, 39, 0.1)),
            rgba(17, 24, 39, 0.88);
        box-shadow: 0 10px 22px rgba(0, 0, 0, 0.14);
    }

    .mrd-portfolio-top {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 0.5rem;
        margin-bottom: 0.52rem;
    }

    .mrd-portfolio-rank {
        color: var(--mrd-muted) !important;
        font-size: 0.78rem;
        font-weight: 700;
    }

    .mrd-portfolio-badge,
    .mrd-signal-chip {
        display: inline-flex;
        align-items: center;
        gap: 0.32rem;
        border: 1px solid var(--mrd-tone-border);
        background: var(--mrd-tone-soft);
        color: var(--mrd-tone) !important;
        border-radius: 999px;
        font-weight: 700;
        white-space: nowrap;
    }

    .mrd-portfolio-badge {
        padding: 0.16rem 0.52rem;
        font-size: 0.72rem;
    }

    .mrd-portfolio-title {
        color: var(--mrd-text);
        font-size: 1.02rem;
        line-height: 1.25;
        font-weight: 800;
        margin-bottom: 0.5rem;
    }

    .mrd-signal-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.35rem;
        margin-bottom: 0.58rem;
    }

    .mrd-signal-chip {
        padding: 0.13rem 0.45rem;
        font-size: 0.7rem;
    }

    .mrd-signal-label {
        color: var(--mrd-muted) !important;
        font-weight: 700;
    }

    .mrd-portfolio-metrics {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 0.45rem;
        margin-bottom: 0.58rem;
    }

    .mrd-portfolio-metric {
        border: 1px solid rgba(148, 163, 184, 0.16);
        border-radius: 8px;
        background: rgba(15, 23, 42, 0.52);
        padding: 0.46rem 0.5rem;
    }

    .mrd-portfolio-metric span {
        display: block;
        color: var(--mrd-muted) !important;
        font-size: 0.68rem;
        line-height: 1.15;
        margin-bottom: 0.22rem;
    }

    .mrd-portfolio-metric strong {
        color: var(--mrd-text);
        font-size: 0.98rem;
        line-height: 1.1;
    }

    .mrd-portfolio-action {
        color: var(--mrd-text);
        font-size: 0.79rem;
        line-height: 1.35;
    }

    .mrd-portfolio-action span {
        color: var(--mrd-muted) !important;
        font-weight: 700;
    }

    .mrd-research-card {
        background: var(--mrd-card);
        border: 1px solid var(--mrd-border);
        border-radius: 12px;
        padding: 1rem 1.05rem;
        min-height: 270px;
        box-shadow: 0 14px 30px rgba(0, 0, 0, 0.16);
    }

    .mrd-research-title {
        color: var(--mrd-text);
        font-size: 1.05rem;
        font-weight: 700;
        margin-top: 0.58rem;
        margin-bottom: 0.28rem;
    }

    .mrd-research-meta {
        color: var(--mrd-muted);
        font-size: 0.82rem;
        margin-bottom: 0.62rem;
    }

    .mrd-research-line {
        color: var(--mrd-text);
        font-size: 0.84rem;
        margin-top: 0.38rem;
    }

    .mrd-section {
        margin-top: 1.25rem;
        padding-top: 1rem;
        border-top: 1px solid var(--mrd-border);
    }

    div[data-testid="stMetric"] {
        background: var(--mrd-card);
        border: 1px solid var(--mrd-border);
        border-radius: 12px;
        padding: 0.85rem 0.95rem;
    }

    div[data-testid="stMetricLabel"] p {
        color: var(--mrd-muted) !important;
        font-size: 0.82rem;
    }

    div[data-testid="stDataFrame"] {
        background: var(--mrd-table);
        border: 1px solid var(--mrd-border);
        border-radius: 10px;
        overflow: hidden;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 0.4rem;
    }

    .stTabs [data-baseweb="tab"] {
        background: var(--mrd-card);
        border: 1px solid var(--mrd-border);
        border-radius: 10px 10px 0 0;
        padding: 0.55rem 0.85rem;
    }

    .stTabs [aria-selected="true"] {
        color: var(--mrd-accent) !important;
        border-color: rgba(56, 189, 248, 0.55);
    }

    div[data-baseweb="select"] > div,
    div[data-baseweb="input"] > div,
    textarea {
        background: var(--mrd-table) !important;
        color: var(--mrd-text) !important;
        border-color: var(--mrd-border) !important;
    }

    .stAlert {
        background: var(--mrd-card);
        border: 1px solid var(--mrd-border);
        border-radius: 10px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def file_signature(path: Path) -> tuple[str, float | None]:
    if not path.exists():
        return str(path), None
    return str(path), path.stat().st_mtime


@st.cache_data(show_spinner=False)
def read_csv_cached(path_text: str, modified_time: float | None) -> pd.DataFrame:
    if modified_time is None:
        return pd.DataFrame()
    try:
        return pd.read_csv(path_text)
    except (OSError, pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError):
        return pd.DataFrame()


@st.cache_data(show_spinner=False)
def count_csv_rows_cached(path_text: str, modified_time: float | None) -> int | None:
    if modified_time is None:
        return None
    try:
        row_count = 0
        with open(path_text, "rb") as file:
            for row_count, _ in enumerate(file, start=1):
                pass
        return max(row_count - 1, 0)
    except OSError:
        return None


def load_csv(name: str) -> pd.DataFrame:
    path = CSV_FILES[name]
    path_text, modified_time = file_signature(path)
    return read_csv_cached(path_text, modified_time).copy()


def csv_row_count(name: str) -> int | None:
    path = CSV_FILES[name]
    path_text, modified_time = file_signature(path)
    return count_csv_rows_cached(path_text, modified_time)


def loaded_data_files_frame() -> pd.DataFrame:
    rows = []
    for name, path in CSV_FILES.items():
        exists = path.exists()
        rows.append(
            {
                "file": name,
                "path": str(path.relative_to(PROJECT_ROOT)),
                "exists": exists,
                "rows": csv_row_count(name) if exists else None,
                "core": name in CORE_FILES,
            }
        )
    return pd.DataFrame(rows)


def missing_core_files() -> list[Path]:
    return [CSV_FILES[name] for name in sorted(CORE_FILES) if not CSV_FILES[name].exists()]


def existing_columns(df: pd.DataFrame, columns: Iterable[str]) -> list[str]:
    return [column for column in columns if column in df.columns]


def clean_text(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if text.lower() == "nan":
        return ""
    return text


def numeric(value: object, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def format_int(value: object) -> str:
    try:
        return f"{int(round(float(value))):,}"
    except (TypeError, ValueError):
        return "0"


def format_score(value: object) -> str:
    try:
        return f"{float(value):,.2f}"
    except (TypeError, ValueError):
        return ""


def format_rank(value: object) -> str:
    if pd.isna(value):
        return ""
    try:
        return f"{int(round(float(value))):,}"
    except (TypeError, ValueError):
        return str(value)


def priority_sort_key(series: pd.Series) -> pd.Series:
    return series.map(PRIORITY_ORDER).fillna(99)


def sort_by_available(
    df: pd.DataFrame,
    columns: list[str],
    ascending: list[bool],
) -> pd.DataFrame:
    sort_columns = [column for column in columns if column in df.columns]
    if not sort_columns:
        return df
    sort_ascending = [ascending[columns.index(column)] for column in sort_columns]
    return df.sort_values(
        sort_columns,
        ascending=sort_ascending,
        na_position="last",
        key=lambda series: priority_sort_key(series) if series.name in {"priority", "research_priority"} else series,
    )


def clean_options(series: pd.Series) -> list[str]:
    values = series.dropna().astype(str).str.strip()
    values = values[values != ""]
    return sorted(values.unique().tolist())


def split_pipe_values(value: object) -> list[str]:
    return [item.strip() for item in clean_text(value).split("|") if item.strip()]


def pipe_options(series: pd.Series) -> list[str]:
    values: set[str] = set()
    for value in series.dropna():
        values.update(split_pipe_values(value))
    return sorted(values)


def filter_multiselect(
    df: pd.DataFrame,
    column: str,
    label: str,
    key: str,
) -> pd.DataFrame:
    if df.empty or column not in df.columns:
        return df
    options = clean_options(df[column])
    if not options:
        return df
    selected = st.multiselect(label, options, key=key)
    if selected:
        return df[df[column].astype(str).isin(selected)]
    return df


def filter_pipe_multiselect(
    df: pd.DataFrame,
    column: str,
    label: str,
    key: str,
) -> pd.DataFrame:
    if df.empty or column not in df.columns:
        return df
    options = pipe_options(df[column])
    if not options:
        return df
    selected = st.multiselect(label, options, key=key)
    if not selected:
        return df
    selected_set = set(selected)
    return df[df[column].apply(lambda value: bool(selected_set.intersection(split_pipe_values(value))))]


def display_table(df: pd.DataFrame, columns: list[str] | None = None, height: int = 520) -> None:
    if df.empty:
        st.info("No rows available for the selected view.")
        return
    view = df.copy()
    if columns is not None:
        selected_columns = existing_columns(view, columns)
        if not selected_columns:
            st.info("No display columns are available for this data.")
            return
        view = view[selected_columns].copy()

    for column in RANK_COLUMNS:
        if column in view.columns:
            view[column] = view[column].map(format_rank)
    for column in SCORE_COLUMNS:
        if column in view.columns:
            view[column] = view[column].map(format_score)

    st.dataframe(view, use_container_width=True, hide_index=True, height=height)


def page_header(title: str, subtitle: str) -> None:
    st.markdown(f'<h1 class="mrd-page-title">{title}</h1>', unsafe_allow_html=True)
    st.markdown(f'<div class="mrd-subtitle">{subtitle}</div>', unsafe_allow_html=True)


def section_break() -> None:
    st.markdown('<div class="mrd-section"></div>', unsafe_allow_html=True)


def metric_cards(metrics: list[tuple[str, object, str | None]]) -> None:
    columns = st.columns(len(metrics))
    for column, (label, value, note) in zip(columns, metrics):
        display_value = clean_text(value) if isinstance(value, str) else format_int(value)
        with column:
            st.markdown(
                f"""
                <div class="mrd-card">
                    <div class="mrd-card-label">{safe(label)}</div>
                    <div class="mrd-card-value">{safe(display_value)}</div>
                    <div class="mrd-card-note">{safe(note or "")}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def badge_class(priority: object) -> str:
    value = clean_text(priority)
    if value == "P1":
        return "mrd-badge-p1"
    if value == "P2":
        return "mrd-badge-p2"
    if value == "P3":
        return "mrd-badge-p3"
    return "mrd-badge-watch"


def safe(value: object) -> str:
    return escape(clean_text(value))


def portfolio_investment_tone(value: object) -> str:
    text = clean_text(value).lower()
    if "invest aggressively" in text or text == "p1":
        return "green"
    if "expand" in text or text == "p2":
        return "blue"
    if "monitor" in text or "watch" in text or text == "p3":
        return "amber"
    if any(keyword in text for keyword in ["avoid", "declining", "decline", "exit", "archive"]):
        return "red"
    return "amber"


def portfolio_market_size_tone(value: object) -> str:
    text = clean_text(value).lower()
    if "mega" in text:
        return "purple"
    if "large" in text:
        return "blue"
    if "mid" in text or "medium" in text:
        return "amber"
    if "small" in text:
        return "gray"
    return "gray"


def portfolio_growth_tone(value: object) -> str:
    text = clean_text(value).lower()
    if "growing" in text:
        return "green"
    if "evergreen" in text:
        return "teal"
    if "declining" in text or "decline" in text:
        return "red"
    return "gray"


def portfolio_competition_tone(value: object) -> str:
    text = clean_text(value).lower()
    if "low" in text:
        return "green"
    if "medium" in text or "moderate" in text:
        return "amber"
    if "high" in text:
        return "red"
    return "gray"


def portfolio_signal_chip(label: str, value: object, tone: str) -> str:
    display_value = clean_text(value) or "Unknown"
    return (
        f'<span class="mrd-signal-chip mrd-tone-{safe(tone)}">'
        f'<span class="mrd-signal-label">{safe(label)}</span>{safe(display_value)}</span>'
    )


def portfolio_card_html(row: pd.Series, rank: int | None = None, default_investment: str = "Monitor") -> str:
    investment = clean_text(row.get("Investment")) or default_investment
    tone = portfolio_investment_tone(investment)
    rank_label = f"#{rank}" if rank is not None else ""
    market_size = row.get("Market Size")
    growth = row.get("Growth")
    competition = row.get("Competition")
    chips = "".join(
        [
            portfolio_signal_chip("Size", market_size, portfolio_market_size_tone(market_size)),
            portfolio_signal_chip("Growth", growth, portfolio_growth_tone(growth)),
            portfolio_signal_chip("Comp", competition, portfolio_competition_tone(competition)),
        ]
    )
    return f"""
    <div class="mrd-portfolio-card mrd-tone-{safe(tone)}">
        <div class="mrd-portfolio-top">
            <span class="mrd-portfolio-rank">{safe(rank_label)}</span>
            <span class="mrd-portfolio-badge mrd-tone-{safe(tone)}">{safe(investment)}</span>
        </div>
        <div class="mrd-portfolio-title">{safe(row.get('Parent Market'))}</div>
        <div class="mrd-signal-row">{chips}</div>
        <div class="mrd-portfolio-metrics">
            <div class="mrd-portfolio-metric">
                <span>Detected Segment Coverage</span>
                <strong>{safe(format_score(row.get('Coverage')))}%</strong>
            </div>
            <div class="mrd-portfolio-metric">
                <span>Expansion Potential</span>
                <strong>{safe(format_score(row.get('Expansion Potential')))} / 100</strong>
            </div>
        </div>
        <div class="mrd-portfolio-action">
            <span>Action:</span> {safe(market_recommended_action(row))}
        </div>
    </div>
    """


def month_number(month: object) -> int:
    value = clean_text(month).lower()
    months = {
        "january": 1,
        "february": 2,
        "march": 3,
        "april": 4,
        "may": 5,
        "june": 6,
        "july": 7,
        "august": 8,
        "september": 9,
        "october": 10,
        "november": 11,
        "december": 12,
    }
    return months.get(value, 99)


def first_existing_value(row: pd.Series, columns: list[str], default: str = "") -> str:
    for column in columns:
        if column in row.index:
            value = clean_text(row.get(column))
            if value:
                return value
    return default


def first_pipe_value(value: object) -> str:
    values = split_pipe_values(value)
    return values[0] if values else ""


def build_research_queue() -> pd.DataFrame:
    candidates = load_csv("research_candidates")
    scores = load_csv("opportunity_scorecard")

    if candidates.empty and scores.empty:
        return pd.DataFrame()

    if candidates.empty:
        queue = scores.copy()
        queue["priority"] = queue.get("recommended_priority", "")
        queue["opportunity_score"] = queue.get("total_score", 0)
        queue["product_recommendation"] = ""
        queue["customization_recommendation"] = ""
        queue["next_action"] = queue.get("explanation", "")
        return queue

    queue = candidates.copy()
    queue = queue.rename(
        columns={
            "suggested_products": "product_recommendation",
            "suggested_customizations": "customization_recommendation",
        }
    )

    if not scores.empty:
        score_columns = [
            "parent_demand",
            "child_segment",
            "total_score",
            "recommended_priority",
            "explanation",
        ]
        queue = queue.merge(
            scores[existing_columns(scores, score_columns)],
            on=["parent_demand", "child_segment"],
            how="left",
        )
        queue["decision_opportunity_score"] = queue.get("opportunity_score")
        queue["opportunity_score"] = queue["total_score"].combine_first(queue["decision_opportunity_score"])

    queue["primary_product"] = queue.get("product_recommendation", "").apply(first_pipe_value)
    queue["primary_customization"] = queue.get("customization_recommendation", "").apply(first_pipe_value)
    return sort_by_available(queue, ["priority", "opportunity_score"], [True, False])


def portfolio_market_view(portfolio_master: pd.DataFrame, market_intelligence: pd.DataFrame) -> pd.DataFrame:
    if portfolio_master.empty:
        return pd.DataFrame()
    view = portfolio_master.copy()
    if not market_intelligence.empty and "demand_name" in market_intelligence.columns:
        market_columns = ["demand_name", "seasonality_type", "growth_stage", "market_stage"]
        view = view.merge(
            market_intelligence[existing_columns(market_intelligence, market_columns)],
            left_on="parent_demand",
            right_on="demand_name",
            how="left",
        )
    view["Parent Market"] = view["parent_demand"]
    view["Market Size"] = view.get("market_size", "")
    view["Coverage"] = view.get("coverage_score", 0)
    view["Expansion Potential"] = view.get("expansion_potential", 0)
    view["Investment"] = view.get("investment_recommendation", "")
    view["Seasonality"] = view.get("seasonality_type", "")
    view["Growth"] = view.get("growth_stage", "")
    view["Portfolio Stage"] = view.get("portfolio_stage", "")
    return view[
        [
            "Parent Market",
            "Market Size",
            "Coverage",
            "Expansion Potential",
            "Investment",
            "Seasonality",
            "Growth",
            "Portfolio Stage",
        ]
    ]


def horizontal_bar_chart(df: pd.DataFrame, label: str, value: str, title: str) -> None:
    if df.empty or label not in df.columns or value not in df.columns:
        st.info(f"No data available for {title}.")
        return
    chart_data = df[[label, value]].copy()
    chart_data[value] = pd.to_numeric(chart_data[value], errors="coerce").fillna(0)
    chart = (
        alt.Chart(chart_data)
        .mark_bar(color="#38bdf8")
        .encode(
            x=alt.X(f"{value}:Q", title=value),
            y=alt.Y(f"{label}:N", sort="-x", title=None),
            tooltip=[label, alt.Tooltip(f"{value}:Q", format=".2f")],
        )
        .properties(height=max(320, len(chart_data) * 24), title=title)
    )
    st.altair_chart(chart, use_container_width=True)


def pie_chart(df: pd.DataFrame, label: str, value: str, title: str) -> None:
    if df.empty or label not in df.columns or value not in df.columns:
        st.info(f"No data available for {title}.")
        return
    chart = (
        alt.Chart(df)
        .mark_arc(innerRadius=55)
        .encode(
            theta=alt.Theta(f"{value}:Q", title=None),
            color=alt.Color(f"{label}:N", title=None),
            tooltip=[label, alt.Tooltip(f"{value}:Q", format=".0f")],
        )
        .properties(height=360, title=title)
    )
    st.altair_chart(chart, use_container_width=True)


def investment_counts(portfolio_master: pd.DataFrame) -> dict[str, int]:
    if portfolio_master.empty or "investment_recommendation" not in portfolio_master.columns:
        return {"Invest Aggressively": 0, "Expand": 0, "Monitor": 0, "Avoid": 0}
    values = portfolio_master["investment_recommendation"].fillna("").astype(str)
    return {
        "Invest Aggressively": int((values == "Invest Aggressively").sum()),
        "Expand": int((values == "Expand").sum()),
        "Monitor": int((values == "Monitor").sum()),
        "Avoid": int(values.isin(["Avoid", "Exit", "Archive"]).sum()),
    }


def research_card(row: pd.Series) -> None:
    priority = first_existing_value(row, ["priority", "recommended_priority"], "Priority")
    st.markdown(
        f"""
        <div class="mrd-research-card">
            <span class="mrd-badge {badge_class(priority)}">{safe(priority)}</span>
            <div class="mrd-research-title">{safe(row.get("child_segment"))}</div>
            <div class="mrd-research-meta">{safe(row.get("parent_demand"))} | Score {format_score(row.get("opportunity_score", row.get("total_score")))}</div>
            <div class="mrd-research-line"><b>Product:</b> {safe(first_existing_value(row, ["primary_product", "product_recommendation"]))}</div>
            <div class="mrd-research-line"><b>Customization:</b> {safe(first_existing_value(row, ["primary_customization", "customization_recommendation"]))}</div>
            <div class="mrd-research-line"><b>Reason:</b> {safe(row.get("reason"))}</div>
            <div class="mrd-research-line"><b>Action:</b> {safe(row.get("next_action"))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_research_cards(rows: pd.DataFrame, limit: int = 20) -> None:
    if rows.empty:
        st.info("No research candidates available.")
        return
    top_rows = rows.head(limit).reset_index(drop=True)
    for start in range(0, len(top_rows), 2):
        columns = st.columns(2)
        for column, (_, row) in zip(columns, top_rows.iloc[start : start + 2].iterrows()):
            with column:
                research_card(row)


def seasonal_timeline(market_intelligence: pd.DataFrame, market_calendar: pd.DataFrame) -> pd.DataFrame:
    if market_intelligence.empty:
        return pd.DataFrame()
    timeline = market_intelligence.copy()
    if not market_calendar.empty and {"demand", "research_month"}.issubset(market_calendar.columns):
        timeline = timeline.merge(market_calendar, left_on="demand_name", right_on="demand", how="left")
    if "research_start_month" not in timeline.columns:
        timeline["research_start_month"] = timeline.get("research_month", "")
    timeline["Research"] = timeline["research_start_month"].where(
        timeline["research_start_month"].astype(str).str.strip() != "",
        timeline.get("research_month", ""),
    )
    timeline["Design"] = timeline.get("listing_month", "")
    timeline["Upload"] = timeline.get("listing_month", "")
    timeline["Ads"] = timeline.get("ads_month", "")
    timeline["Peak"] = timeline.get("peak_month", "")
    seasonality = timeline.get("seasonality_type", pd.Series("", index=timeline.index)).fillna("").astype(str)
    name = timeline.get("demand_name", pd.Series("", index=timeline.index)).fillna("").astype(str)
    seasonal_mask = (
        (seasonality != "Evergreen")
        | name.str.contains("christmas|halloween|valentine|mother|father|thanksgiving", case=False, regex=True)
    )
    timeline = timeline[seasonal_mask].copy()
    timeline["_month_order"] = timeline["Research"].map(month_number)
    return timeline.sort_values(["_month_order", "demand_name"]).rename(
        columns={"demand_name": "Opportunity", "seasonality_type": "Seasonality", "growth_stage": "Growth"}
    )


def coverage_breakdown(
    portfolio_master: pd.DataFrame,
    portfolio_summary: pd.DataFrame,
    market_intelligence: pd.DataFrame,
) -> pd.DataFrame:
    if "current_child_segments" in portfolio_summary.columns:
        covered = numeric(portfolio_summary["current_child_segments"].sum())
    elif "child_segment_count" in portfolio_master.columns:
        covered = numeric(portfolio_master["child_segment_count"].sum())
    else:
        covered = 0
    total = numeric(portfolio_summary["estimated_total_segments"].sum()) if "estimated_total_segments" in portfolio_summary.columns else covered
    missing = max(total - covered, 0)
    investment = portfolio_master.get("investment_recommendation", pd.Series(dtype=str)).fillna("").astype(str)
    expandable = int(investment.isin(["Invest Aggressively", "Expand"]).sum())
    seasonality = market_intelligence.get("seasonality_type", pd.Series(dtype=str)).fillna("").astype(str)
    seasonal = int((seasonality != "Evergreen").sum())
    evergreen = int((seasonality == "Evergreen").sum())
    return pd.DataFrame(
        {
            "Category": ["Covered", "Missing", "Expandable", "Seasonal", "Evergreen"],
            "Count": [covered, missing, expandable, seasonal, evergreen],
        }
    )


def mode_pipe_value(series: pd.Series) -> str:
    values: list[str] = []
    for value in series.dropna():
        values.extend(split_pipe_values(value))
    if not values:
        return ""
    return pd.Series(values).value_counts().index[0]


def executive_insights(
    portfolio_master: pd.DataFrame,
    market_intelligence: pd.DataFrame,
    research_queue: pd.DataFrame,
    product_fit: pd.DataFrame,
    customization_fit: pd.DataFrame,
) -> list[tuple[str, str, str]]:
    insights: list[tuple[str, str, str]] = []
    if not portfolio_master.empty:
        largest = sort_by_available(portfolio_master, ["best_child_score", "expansion_potential"], [False, False]).head(1)
        under = sort_by_available(portfolio_master, ["coverage_score", "expansion_potential"], [True, False]).head(1)
        if not largest.empty:
            row = largest.iloc[0]
            insights.append(("Largest Market", clean_text(row.get("parent_demand")), f"{clean_text(row.get('market_size'))} | best child {format_score(row.get('best_child_score'))}"))
        if not under.empty:
            row = under.iloc[0]
            insights.append(("Most Under-Covered", clean_text(row.get("parent_demand")), f"Coverage {format_score(row.get('coverage_score'))}%"))
    if not market_intelligence.empty:
        growing = market_intelligence[market_intelligence.get("growth_stage", "").astype(str).str.lower() == "growing"]
        if not growing.empty:
            row = growing.iloc[0]
            insights.append(("Fastest Growing", clean_text(row.get("demand_name")), clean_text(row.get("recommendation"))))
        seasonal = market_intelligence[market_intelligence.get("seasonality_type", "").astype(str) != "Evergreen"]
        evergreen = market_intelligence[market_intelligence.get("seasonality_type", "").astype(str) == "Evergreen"]
        if not seasonal.empty:
            insights.append(("Top Seasonal", clean_text(seasonal.iloc[0].get("demand_name")), clean_text(seasonal.iloc[0].get("seasonality_type"))))
        if not evergreen.empty:
            insights.append(("Top Evergreen", clean_text(evergreen.iloc[0].get("demand_name")), clean_text(evergreen.iloc[0].get("growth_stage"))))
    if not research_queue.empty:
        top = sort_by_available(research_queue, ["opportunity_score"], [False]).head(1)
        if not top.empty:
            row = top.iloc[0]
            insights.append(("Highest Opportunity", clean_text(row.get("child_segment")), f"Score {format_score(row.get('opportunity_score'))}"))
        confident = research_queue[research_queue.get("priority", "").astype(str) == "P1"].head(1)
        if not confident.empty:
            row = confident.iloc[0]
            insights.append(("Highest Confidence", clean_text(row.get("child_segment")), "P1 research candidate"))
        product = mode_pipe_value(research_queue.get("product_recommendation", pd.Series(dtype=str)))
        customization = mode_pipe_value(research_queue.get("customization_recommendation", pd.Series(dtype=str)))
        if product:
            insights.append(("Top Product", product, "Most common research recommendation"))
        if customization:
            insights.append(("Top Customization", customization, "Most common personalization path"))
    if len(insights) < 8 and not product_fit.empty and "best_product" in product_fit.columns:
        insights.append(("Product Fit Leader", clean_text(product_fit["best_product"].mode().iloc[0]), "Best-product mode"))
    if len(insights) < 8 and not customization_fit.empty and "best_customization" in customization_fit.columns:
        insights.append(("Customization Leader", clean_text(customization_fit["best_customization"].mode().iloc[0]), "Best-customization mode"))
    return insights[:9]


def executive_intelligence() -> None:
    page_header(
        "Executive Intelligence",
        "Executive dashboard for market size, investment, weekly research, seasonality, coverage, and insights.",
    )
    portfolio_master = load_csv("portfolio_master")
    portfolio_summary = load_csv("portfolio_summary")
    market_intelligence = load_csv("market_intelligence")
    market_calendar = load_csv("market_calendar")
    research_queue = build_research_queue()
    product_fit = load_csv("product_fit_matrix")
    customization_fit = load_csv("customization_fit_matrix")

    p1_count = int((research_queue["priority"] == "P1").sum()) if "priority" in research_queue.columns else 0
    metric_cards(
        [
            ("Parent Markets", len(portfolio_master), "Portfolio intelligence rows"),
            ("Research Candidates", len(research_queue), "Child niches in queue"),
            ("P1 This Week", p1_count, "Immediate research priorities"),
            (
                "Avg Coverage",
                f"{numeric(portfolio_master['coverage_score'].mean() if 'coverage_score' in portfolio_master.columns else 0):.1f}%",
                "Portfolio coverage",
            ),
        ]
    )

    section_break()
    st.subheader("1. Where is the biggest market?")
    markets = portfolio_market_view(portfolio_master, market_intelligence)
    top_markets = sort_by_available(markets, ["Expansion Potential", "Coverage"], [False, False]).head(15)
    left_chart, right_chart = st.columns(2)
    with left_chart:
        horizontal_bar_chart(top_markets, "Parent Market", "Expansion Potential", "Top 15 by Expansion Potential")
    with right_chart:
        horizontal_bar_chart(top_markets, "Parent Market", "Coverage", "Top 15 by Coverage")
    with st.expander("Top 15 Parent Markets", expanded=False):
        display_table(top_markets, height=360)

    section_break()
    st.subheader("2. Where should we invest?")
    counts = investment_counts(portfolio_master)
    metric_cards(
        [
            ("Invest Aggressively", counts["Invest Aggressively"], "Highest portfolio commitment"),
            ("Expand", counts["Expand"], "Scale existing portfolio"),
            ("Monitor", counts["Monitor"], "Watch next import"),
            ("Avoid", counts["Avoid"], "Do not allocate new work"),
        ]
    )

    section_break()
    st.subheader("3. What should the team research this week?")
    render_research_cards(research_queue, 20)

    section_break()
    st.subheader("4. Upcoming seasonal opportunities")
    timeline = seasonal_timeline(market_intelligence, market_calendar)
    display_table(
        timeline.head(30),
        ["Opportunity", "Seasonality", "Growth", "Research", "Design", "Upload", "Ads", "Peak"],
        height=420,
    )

    section_break()
    st.subheader("5. Portfolio Coverage")
    coverage = coverage_breakdown(portfolio_master, portfolio_summary, market_intelligence)
    pie_chart(coverage, "Category", "Count", "Coverage Mix")

    section_break()
    st.subheader("6. Top Executive Insights")
    insights = executive_insights(portfolio_master, market_intelligence, research_queue, product_fit, customization_fit)
    for start in range(0, len(insights), 3):
        columns = st.columns(3)
        for column, (label, value, note) in zip(columns, insights[start : start + 3]):
            with column:
                metric_cards([(label, value, note)])


def mapped_score(value: object, mapping: dict[str, float], default: float = 50.0) -> float:
    text = clean_text(value).lower()
    if not text:
        return default
    for label, score in mapping.items():
        if label in text:
            return score
    return default


def market_size_score(value: object) -> float:
    return mapped_score(
        value,
        {
            "mega": 100,
            "large": 82,
            "mid": 62,
            "small": 38,
            "micro": 18,
        },
        50,
    )


def growth_axis_score(value: object) -> float:
    return mapped_score(
        value,
        {
            "declining": 1,
            "stable": 2,
            "mature": 2.4,
            "emerging": 3,
            "growing": 4,
        },
        2.5,
    )


def growth_fit_score(value: object) -> float:
    return mapped_score(
        value,
        {
            "declining": 25,
            "stable": 55,
            "mature": 62,
            "emerging": 78,
            "growing": 88,
        },
        55,
    )


def competition_axis_score(value: object) -> float:
    return mapped_score(
        value,
        {
            "low": 1,
            "medium": 2,
            "high": 3,
        },
        2,
    )


def competition_fit_score(value: object) -> float:
    return mapped_score(
        value,
        {
            "low": 86,
            "medium": 62,
            "high": 38,
        },
        55,
    )


def seasonality_fit_score(value: object) -> float:
    return mapped_score(
        value,
        {
            "evergreen": 78,
            "holiday": 72,
            "q4": 70,
            "seasonal": 68,
            "emerging": 66,
            "declining": 35,
        },
        60,
    )


def score_summary_by_parent(scorecard: pd.DataFrame) -> pd.DataFrame:
    if scorecard.empty or "parent_demand" not in scorecard.columns:
        return pd.DataFrame()
    aggregations: dict[str, tuple[str, str]] = {}
    for source, output in [
        ("total_score", "Average Opportunity"),
        ("growth_score", "Growth Score"),
        ("competition_score", "Competition Fit Score"),
        ("product_fit_score", "Product Fit Score"),
        ("seasonality_score", "Seasonality Score"),
        ("expansion_score", "Scorecard Expansion"),
    ]:
        if source in scorecard.columns:
            aggregations[output] = (source, "mean")
    if not aggregations:
        return pd.DataFrame()
    summary = scorecard.groupby("parent_demand", as_index=False).agg(**aggregations)
    return summary.rename(columns={"parent_demand": "Parent Market"})


def customization_score_by_parent(scorecard: pd.DataFrame, customization_fit: pd.DataFrame) -> pd.DataFrame:
    score_columns = ["photo", "name", "multiple_names", "birth_flower", "clipart", "line_art", "hand_drawing"]
    if (
        scorecard.empty
        or customization_fit.empty
        or "parent_demand" not in scorecard.columns
        or "child_segment" not in scorecard.columns
        or "child_segment" not in customization_fit.columns
    ):
        return pd.DataFrame()
    available_scores = existing_columns(customization_fit, score_columns)
    if not available_scores:
        return pd.DataFrame()
    merged = scorecard[["parent_demand", "child_segment"]].merge(customization_fit, on="child_segment", how="left")
    if merged.empty:
        return pd.DataFrame()
    merged["Customization Fit Score"] = merged[available_scores].apply(
        lambda row: pd.to_numeric(row, errors="coerce").max(),
        axis=1,
    )
    summary = merged.groupby("parent_demand", as_index=False)["Customization Fit Score"].mean()
    return summary.rename(columns={"parent_demand": "Parent Market"})


def series_or_default(df: pd.DataFrame, column: str, default: object = "") -> pd.Series:
    if column in df.columns:
        return df[column]
    return pd.Series(default, index=df.index)


def first_available_series(df: pd.DataFrame, columns: list[str], default: object = "") -> pd.Series:
    for column in columns:
        if column in df.columns:
            return df[column]
    return pd.Series(default, index=df.index)


def numeric_market_series(df: pd.DataFrame, columns: list[str], default: float = 0.0) -> pd.Series:
    return pd.to_numeric(first_available_series(df, columns, default), errors="coerce").fillna(default)


def market_landscape_data(
    portfolio_master: pd.DataFrame,
    market_intelligence: pd.DataFrame,
    scorecard: pd.DataFrame,
    customization_fit: pd.DataFrame,
) -> pd.DataFrame:
    if portfolio_master.empty and market_intelligence.empty:
        return pd.DataFrame()

    if portfolio_master.empty:
        view = market_intelligence.copy().rename(columns={"demand_name": "parent_demand"})
    else:
        view = portfolio_master.copy()
        if not market_intelligence.empty and "demand_name" in market_intelligence.columns:
            market_columns = [
                "demand_name",
                "market_size",
                "growth_stage",
                "market_stage",
                "expansion_score",
                "competition_level",
                "seasonality_type",
                "research_priority",
            ]
            view = view.merge(
                market_intelligence[existing_columns(market_intelligence, market_columns)],
                left_on="parent_demand",
                right_on="demand_name",
                how="left",
                suffixes=("", "_market"),
            )

    view["Parent Market"] = first_available_series(view, ["parent_demand", "demand_name"])
    view["Market Size"] = first_available_series(view, ["market_size", "market_size_market"])
    if "market_size_market" in view.columns:
        view["Market Size"] = view["market_size_market"].where(view["market_size_market"].astype(str).str.strip() != "", view["Market Size"])
    view["Growth"] = series_or_default(view, "growth_stage")
    view["Coverage"] = numeric_market_series(view, ["coverage_score"])
    view["Competition"] = series_or_default(view, "competition_level")
    view["Seasonality"] = series_or_default(view, "seasonality_type")
    view["Investment"] = first_available_series(view, ["investment_recommendation", "research_priority"])
    view["Expansion Potential"] = numeric_market_series(view, ["expansion_potential", "expansion_score"])
    view["Portfolio Stage"] = first_available_series(view, ["portfolio_stage", "market_stage"])
    view["Market Stage"] = first_available_series(view, ["market_stage", "portfolio_stage"])
    view["Average Opportunity"] = numeric_market_series(view, ["average_opportunity_score"])
    view["Best Child Score"] = numeric_market_series(view, ["best_child_score"])
    view["Child Segment Count"] = numeric_market_series(view, ["child_segment_count"])
    view["Recommendation"] = first_available_series(view, ["recommendation", "investment_recommendation", "research_priority"])
    view["Market Size Score"] = view["Market Size"].apply(market_size_score)
    view["Growth Axis"] = view["Growth"].apply(growth_axis_score)
    view["Competition Axis"] = view["Competition"].apply(competition_axis_score)

    score_summary = score_summary_by_parent(scorecard)
    if not score_summary.empty:
        view = view.merge(score_summary, on="Parent Market", how="left", suffixes=("", "_score"))
        for column in ["Average Opportunity", "Growth Score", "Competition Fit Score", "Product Fit Score", "Seasonality Score"]:
            score_column = f"{column}_score"
            if score_column in view.columns:
                view[column] = pd.to_numeric(view[column], errors="coerce").fillna(0)
                view[column] = view[column].where(view[column] > 0, pd.to_numeric(view[score_column], errors="coerce").fillna(0))
        if "Scorecard Expansion" in view.columns:
            view["Expansion Potential"] = view["Expansion Potential"].where(
                view["Expansion Potential"] > 0,
                pd.to_numeric(view["Scorecard Expansion"], errors="coerce").fillna(0),
            )

    customization_summary = customization_score_by_parent(scorecard, customization_fit)
    if not customization_summary.empty:
        view = view.merge(customization_summary, on="Parent Market", how="left")

    if "Growth Score" not in view.columns:
        view["Growth Score"] = view["Growth"].apply(growth_fit_score)
    view["Growth Score"] = pd.to_numeric(view["Growth Score"], errors="coerce").fillna(view["Growth"].apply(growth_fit_score))

    if "Competition Fit Score" not in view.columns:
        view["Competition Fit Score"] = view["Competition"].apply(competition_fit_score)
    view["Competition Fit Score"] = pd.to_numeric(view["Competition Fit Score"], errors="coerce").fillna(
        view["Competition"].apply(competition_fit_score)
    )

    if "Product Fit Score" not in view.columns:
        view["Product Fit Score"] = 0
    view["Product Fit Score"] = pd.to_numeric(view["Product Fit Score"], errors="coerce").fillna(0)
    view["Product Fit Score"] = view["Product Fit Score"].where(view["Product Fit Score"] > 0, view["Average Opportunity"])

    if "Customization Fit Score" not in view.columns:
        view["Customization Fit Score"] = 0
    view["Customization Fit Score"] = pd.to_numeric(view["Customization Fit Score"], errors="coerce").fillna(0)
    view["Customization Fit Score"] = view["Customization Fit Score"].where(
        view["Customization Fit Score"] > 0,
        view["Product Fit Score"],
    )

    if "Seasonality Score" not in view.columns:
        view["Seasonality Score"] = view["Seasonality"].apply(seasonality_fit_score)
    view["Seasonality Score"] = pd.to_numeric(view["Seasonality Score"], errors="coerce").fillna(
        view["Seasonality"].apply(seasonality_fit_score)
    )

    columns = [
        "Parent Market",
        "Market Size",
        "Growth",
        "Coverage",
        "Competition",
        "Seasonality",
        "Investment",
        "Expansion Potential",
        "Portfolio Stage",
        "Market Stage",
        "Average Opportunity",
        "Best Child Score",
        "Child Segment Count",
        "Recommendation",
        "Market Size Score",
        "Growth Axis",
        "Competition Axis",
        "Growth Score",
        "Competition Fit Score",
        "Product Fit Score",
        "Customization Fit Score",
        "Seasonality Score",
    ]
    return view[existing_columns(view, columns)].drop_duplicates(subset=["Parent Market"])


def dark_chart(chart: alt.Chart) -> alt.Chart:
    return (
        chart.configure_view(strokeOpacity=0)
        .configure_axis(labelColor="#e5e7eb", titleColor="#9ca3af", gridColor="rgba(148, 163, 184, 0.16)")
        .configure_legend(labelColor="#e5e7eb", titleColor="#9ca3af")
        .configure_title(color="#e5e7eb")
        .configure(background="#0f172a")
    )


def market_landscape_chart(markets: pd.DataFrame) -> None:
    if markets.empty:
        st.info("No market landscape data is available.")
        return
    chart_data = markets.copy()
    chart_data["Expansion Potential"] = pd.to_numeric(chart_data["Expansion Potential"], errors="coerce").fillna(0)
    chart = (
        alt.Chart(chart_data)
        .mark_bar(color="#38bdf8")
        .encode(
            x=alt.X("Expansion Potential:Q", title="Expansion Potential"),
            y=alt.Y("Parent Market:N", sort="-x", title=None),
            tooltip=[
                "Parent Market",
                "Market Size",
                "Growth",
                alt.Tooltip("Coverage:Q", format=".1f"),
                "Competition",
                "Seasonality",
                "Investment",
                alt.Tooltip("Expansion Potential:Q", format=".1f"),
                "Portfolio Stage",
            ],
        )
        .properties(height=max(360, len(chart_data) * 24), title="Top Parent Markets by Expansion Potential")
    )
    st.altair_chart(dark_chart(chart), use_container_width=True)


def market_heatmap(markets: pd.DataFrame) -> None:
    if markets.empty:
        st.info("No heat map data is available.")
        return
    metrics = ["Coverage", "Expansion Potential", "Average Opportunity", "Best Child Score", "Growth Score"]
    available_metrics = existing_columns(markets, metrics)
    if not available_metrics:
        st.info("No numeric market metrics are available for the heat map.")
        return
    heat_data = markets[["Parent Market", *available_metrics]].melt(
        id_vars="Parent Market",
        var_name="Metric",
        value_name="Score",
    )
    heat_data["Score"] = pd.to_numeric(heat_data["Score"], errors="coerce").fillna(0)
    chart = (
        alt.Chart(heat_data)
        .mark_rect(stroke="#0f172a", strokeWidth=1)
        .encode(
            x=alt.X("Metric:N", title=None),
            y=alt.Y("Parent Market:N", sort=markets["Parent Market"].tolist(), title=None),
            color=alt.Color("Score:Q", scale=alt.Scale(scheme="tealblues"), title="Score"),
            tooltip=["Parent Market", "Metric", alt.Tooltip("Score:Q", format=".1f")],
        )
        .properties(height=max(360, markets["Parent Market"].nunique() * 24), title="Market Quality Heat Map")
    )
    st.altair_chart(dark_chart(chart), use_container_width=True)


def market_growth_matrix(markets: pd.DataFrame) -> None:
    if markets.empty:
        st.info("No growth matrix data is available.")
        return
    matrix = markets.copy()
    matrix["Bubble Size"] = matrix["Market Size Score"].clip(lower=18)
    matrix["Potential"] = matrix["Growth Score"] + matrix["Expansion Potential"] + matrix["Competition Fit Score"]
    chart = (
        alt.Chart(matrix)
        .mark_circle(opacity=0.82, stroke="#e5e7eb", strokeWidth=0.6)
        .encode(
            x=alt.X(
                "Competition Axis:Q",
                title="Competition (Low to High)",
                scale=alt.Scale(domain=[0.7, 3.3]),
                axis=alt.Axis(values=[1, 2, 3], labelExpr="datum.value == 1 ? 'Low' : datum.value == 2 ? 'Medium' : 'High'"),
            ),
            y=alt.Y(
                "Growth Axis:Q",
                title="Growth (Low to High)",
                scale=alt.Scale(domain=[0.7, 4.3]),
                axis=alt.Axis(values=[1, 2, 3, 4], labelExpr="datum.value == 1 ? 'Declining' : datum.value == 2 ? 'Stable' : datum.value == 3 ? 'Emerging' : 'Growing'"),
            ),
            size=alt.Size("Bubble Size:Q", scale=alt.Scale(range=[90, 1400]), legend=alt.Legend(title="Market Size")),
            color=alt.Color("Investment:N", title="Investment"),
            tooltip=[
                "Parent Market",
                "Market Size",
                "Growth",
                "Competition",
                "Investment",
                alt.Tooltip("Expansion Potential:Q", format=".1f"),
                alt.Tooltip("Average Opportunity:Q", format=".1f"),
            ],
        )
        .properties(height=520, title="Growth vs Competition Matrix")
    )
    st.altair_chart(dark_chart(chart), use_container_width=True)


def month_position(value: object, peak_value: object = "") -> int | None:
    month = month_number(value)
    if month <= 12:
        return month
    text = clean_text(value).lower()
    peak = month_number(peak_value)
    if "three months before peak" in text and peak <= 12:
        return max(1, peak - 3)
    if "two months before peak" in text and peak <= 12:
        return max(1, peak - 2)
    if "one month before peak" in text and peak <= 12:
        return max(1, peak - 1)
    return None


def month_label(position: object) -> str:
    labels = {
        1: "Jan",
        2: "Feb",
        3: "Mar",
        4: "Apr",
        5: "May",
        6: "Jun",
        7: "Jul",
        8: "Aug",
        9: "Sep",
        10: "Oct",
        11: "Nov",
        12: "Dec",
        13: "Jan",
    }
    return labels.get(int(position), "")


def market_gantt_data(market_calendar: pd.DataFrame) -> pd.DataFrame:
    if market_calendar.empty or "demand" not in market_calendar.columns:
        return pd.DataFrame()
    rows: list[dict[str, object]] = []
    for _, row in market_calendar.iterrows():
        demand = clean_text(row.get("demand"))
        peak = row.get("peak_month")
        phase_months = [
            ("Research Start", row.get("research_month"), 0.0, 0.85),
            ("Design Start", row.get("listing_month"), 0.0, 0.45),
            ("Upload", row.get("listing_month"), 0.5, 0.95),
            ("Ads", row.get("ads_month"), 0.0, 0.85),
            ("Peak Month", peak, 0.0, 0.85),
        ]
        peak_position = month_position(peak)
        if peak_position is not None:
            phase_months.append(("Ending Month", peak_position + 1, 0.0, 0.85))
        for phase, month_value, start_offset, end_offset in phase_months:
            position = month_value if isinstance(month_value, int) else month_position(month_value, peak)
            if position is None:
                continue
            rows.append(
                {
                    "Market": demand,
                    "Phase": phase,
                    "Start": position + start_offset,
                    "End": position + end_offset,
                    "Month": month_label(position),
                }
            )
    if not rows:
        return pd.DataFrame()
    data = pd.DataFrame(rows)
    market_order = data.groupby("Market")["Start"].min().sort_values().head(32).index.tolist()
    return data[data["Market"].isin(market_order)].copy()


def market_gantt_chart(market_calendar: pd.DataFrame) -> None:
    data = market_gantt_data(market_calendar)
    if data.empty:
        st.info("No month-based seasonal calendar data is available.")
        return
    chart = (
        alt.Chart(data)
        .mark_bar(cornerRadius=3)
        .encode(
            x=alt.X(
                "Start:Q",
                title="Month",
                scale=alt.Scale(domain=[1, 13.9]),
                axis=alt.Axis(
                    values=list(range(1, 14)),
                    labelExpr="datum.value == 1 ? 'Jan' : datum.value == 2 ? 'Feb' : datum.value == 3 ? 'Mar' : datum.value == 4 ? 'Apr' : datum.value == 5 ? 'May' : datum.value == 6 ? 'Jun' : datum.value == 7 ? 'Jul' : datum.value == 8 ? 'Aug' : datum.value == 9 ? 'Sep' : datum.value == 10 ? 'Oct' : datum.value == 11 ? 'Nov' : datum.value == 12 ? 'Dec' : 'Jan'",
                ),
            ),
            x2="End:Q",
            y=alt.Y("Market:N", sort=alt.EncodingSortField(field="Start", op="min", order="ascending"), title=None),
            color=alt.Color("Phase:N", title="Stage"),
            tooltip=["Market", "Phase", "Month"],
        )
        .properties(height=max(430, data["Market"].nunique() * 24), title="Seasonality Calendar")
    )
    st.altair_chart(dark_chart(chart), use_container_width=True)


def lifecycle_summary(markets: pd.DataFrame) -> pd.DataFrame:
    if markets.empty:
        return pd.DataFrame()
    stage = markets.get("Portfolio Stage", pd.Series("", index=markets.index)).astype(str).str.lower()
    market_stage = markets.get("Market Stage", pd.Series("", index=markets.index)).astype(str).str.lower()
    growth = markets.get("Growth", pd.Series("", index=markets.index)).astype(str).str.lower()
    seasonality = markets.get("Seasonality", pd.Series("", index=markets.index)).astype(str).str.lower()
    groups = {
        "Emerging": stage.str.contains("emerging") | market_stage.str.contains("emerging") | growth.str.contains("emerging"),
        "Growing": stage.str.contains("growing") | growth.str.contains("growing"),
        "Mature": stage.str.contains("mature") | market_stage.str.contains("scale|mature", regex=True),
        "Seasonal": (seasonality != "") & ~seasonality.str.contains("evergreen"),
        "Declining": stage.str.contains("declining") | growth.str.contains("declining"),
    }
    rows = []
    for label, mask in groups.items():
        subset = markets[mask].copy()
        rows.append(
            {
                "Lifecycle": label,
                "Market Count": len(subset),
                "Average Opportunity": numeric(subset["Average Opportunity"].mean()) if "Average Opportunity" in subset.columns and not subset.empty else 0,
                "Average Growth": numeric(subset["Growth Score"].mean()) if "Growth Score" in subset.columns and not subset.empty else 0,
            }
        )
    return pd.DataFrame(rows)


def lifecycle_cards(summary: pd.DataFrame) -> None:
    if summary.empty:
        st.info("No lifecycle summary is available.")
        return
    columns = st.columns(len(summary))
    for column, (_, row) in zip(columns, summary.iterrows()):
        with column:
            st.markdown(
                f"""
                <div class="mrd-card" style="min-height:150px;">
                    <div class="mrd-card-label">{safe(row.get("Lifecycle"))}</div>
                    <div class="mrd-card-value">{format_int(row.get("Market Count"))}</div>
                    <div class="mrd-card-note">Avg opportunity {format_score(row.get("Average Opportunity"))}</div>
                    <div class="mrd-card-note">Avg growth {format_score(row.get("Average Growth"))}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def comparison_radar_data(markets: pd.DataFrame, selected_markets: list[str]) -> pd.DataFrame:
    if markets.empty or not selected_markets:
        return pd.DataFrame()
    dimensions = [
        ("Growth", "Growth Score"),
        ("Coverage", "Coverage"),
        ("Competition", "Competition Fit Score"),
        ("Product Fit", "Product Fit Score"),
        ("Customization Fit", "Customization Fit Score"),
        ("Seasonality", "Seasonality Score"),
        ("Expansion", "Expansion Potential"),
    ]
    rows: list[dict[str, object]] = []
    selected = markets[markets["Parent Market"].isin(selected_markets)].copy()
    for _, row in selected.iterrows():
        for order, (label, column) in enumerate(dimensions, start=1):
            rows.append(
                {
                    "Parent Market": row.get("Parent Market"),
                    "Dimension": label,
                    "Score": max(0, min(100, numeric(row.get(column)))),
                    "Order": order,
                }
            )
    return pd.DataFrame(rows)


def radar_chart(data: pd.DataFrame) -> None:
    if data.empty:
        st.info("Select up to 3 parent markets to compare.")
        return
    base = alt.Chart(data).encode(
        theta=alt.Theta("Dimension:N", sort=["Growth", "Coverage", "Competition", "Product Fit", "Customization Fit", "Seasonality", "Expansion"]),
        radius=alt.Radius("Score:Q", scale=alt.Scale(domain=[0, 100]), title="Score"),
        color=alt.Color("Parent Market:N", title="Parent Market"),
        tooltip=["Parent Market", "Dimension", alt.Tooltip("Score:Q", format=".1f")],
    )
    chart = (
        base.mark_area(opacity=0.12)
        + base.mark_line(strokeWidth=2)
        + base.mark_point(filled=True, size=70)
    ).properties(height=470, title="Market Comparison Radar")
    st.altair_chart(dark_chart(chart), use_container_width=True)


def market_executive_insights(markets: pd.DataFrame, research_queue: pd.DataFrame) -> list[tuple[str, str, str]]:
    insights: list[tuple[str, str, str]] = []
    if not markets.empty:
        largest = sort_by_available(markets, ["Market Size Score", "Average Opportunity"], [False, False]).head(1)
        fastest = sort_by_available(markets, ["Growth Score", "Expansion Potential"], [False, False]).head(1)
        seasonal = markets[markets["Seasonality"].astype(str) != "Evergreen"]
        evergreen = markets[markets["Seasonality"].astype(str) == "Evergreen"]
        highest_expansion = sort_by_available(markets, ["Expansion Potential"], [False]).head(1)
        lowest_coverage = sort_by_available(markets, ["Coverage", "Expansion Potential"], [True, False]).head(1)
        for label, rows, note_column in [
            ("Largest Market", largest, "Market Size"),
            ("Fastest Growing", fastest, "Growth"),
            ("Highest Expansion", highest_expansion, "Expansion Potential"),
            ("Lowest Coverage", lowest_coverage, "Coverage"),
        ]:
            if not rows.empty:
                row = rows.iloc[0]
                note = format_score(row.get(note_column)) if note_column in {"Expansion Potential", "Coverage"} else clean_text(row.get(note_column))
                insights.append((label, clean_text(row.get("Parent Market")), note))
        if not seasonal.empty:
            row = sort_by_available(seasonal, ["Average Opportunity", "Expansion Potential"], [False, False]).iloc[0]
            insights.append(("Best Seasonal", clean_text(row.get("Parent Market")), clean_text(row.get("Seasonality"))))
        if not evergreen.empty:
            row = sort_by_available(evergreen, ["Average Opportunity", "Expansion Potential"], [False, False]).iloc[0]
            insights.append(("Best Evergreen", clean_text(row.get("Parent Market")), clean_text(row.get("Growth"))))
    if not research_queue.empty:
        top = sort_by_available(research_queue, ["opportunity_score"], [False]).head(1)
        if not top.empty:
            row = top.iloc[0]
            insights.append(("Highest Opportunity", clean_text(row.get("child_segment")), f"Score {format_score(row.get('opportunity_score'))}"))
        confident = research_queue[research_queue.get("priority", "").astype(str) == "P1"].head(1)
        if not confident.empty:
            row = confident.iloc[0]
            insights.append(("Highest Confidence", clean_text(row.get("child_segment")), clean_text(row.get("parent_demand"))))
    return insights[:8]


def market_intelligence_page() -> None:
    page_header(
        "Market Intelligence",
        "Executive view of which parent markets MRnD should invest in.",
    )
    portfolio_master = load_csv("portfolio_master")
    market_intelligence = load_csv("market_intelligence")
    market_calendar = load_csv("market_calendar")
    scorecard = load_csv("opportunity_scorecard")
    customization_fit = load_csv("customization_fit_matrix")
    research_queue = build_research_queue()

    markets = market_landscape_data(portfolio_master, market_intelligence, scorecard, customization_fit)
    if markets.empty:
        st.info("Market intelligence data is missing or empty.")
        return

    top_markets = sort_by_available(
        markets,
        ["Market Size Score", "Expansion Potential", "Average Opportunity"],
        [False, False, False],
    ).head(15)

    metric_cards(
        [
            ("Parent Markets", len(markets), "Investment markets available"),
            ("Invest Aggressively", int((markets["Investment"] == "Invest Aggressively").sum()), "Highest investment tier"),
            ("Avg Expansion", f"{numeric(markets['Expansion Potential'].mean()):.1f}", "Expansion potential"),
            ("Low Coverage", int((markets["Coverage"] < 40).sum()), "Under-covered markets"),
        ]
    )

    section_break()
    st.subheader("1. Market Landscape")
    chart_col, heat_col = st.columns([1.05, 1])
    with chart_col:
        market_landscape_chart(top_markets)
    with heat_col:
        market_heatmap(top_markets)
    with st.expander("Top Parent Market Details", expanded=False):
        display_table(
            top_markets,
            [
                "Parent Market",
                "Market Size",
                "Growth",
                "Coverage",
                "Competition",
                "Seasonality",
                "Investment",
                "Expansion Potential",
                "Portfolio Stage",
            ],
            height=360,
        )

    section_break()
    st.subheader("2. Market Growth Matrix")
    market_growth_matrix(markets)

    section_break()
    st.subheader("3. Seasonality Calendar")
    market_gantt_chart(market_calendar)

    section_break()
    st.subheader("4. Market Lifecycle")
    lifecycle_cards(lifecycle_summary(markets))

    section_break()
    st.subheader("5. Market Comparison")
    market_options = top_markets["Parent Market"].astype(str).tolist()
    selected_markets = st.multiselect(
        "Compare up to 3 Parent Markets",
        market_options,
        default=market_options[:3],
        key="market_intelligence_compare",
    )
    if len(selected_markets) > 3:
        st.warning("Showing the first 3 selected parent markets.")
        selected_markets = selected_markets[:3]
    radar_chart(comparison_radar_data(markets, selected_markets))

    section_break()
    st.subheader("6. Executive Insights")
    card_grid(market_executive_insights(markets, research_queue), 4)


def decision_data() -> pd.DataFrame:
    queue = build_research_queue()
    product_fit = load_csv("product_fit_matrix")
    customization_fit = load_csv("customization_fit_matrix")
    reasoning = load_csv("research_reasoning")
    if queue.empty:
        return queue
    result = queue.copy()
    if not product_fit.empty:
        result = result.merge(product_fit, on="child_segment", how="left", suffixes=("", "_product_fit"))
    if not customization_fit.empty:
        result = result.merge(customization_fit, on="child_segment", how="left", suffixes=("", "_custom_fit"))
    if not reasoning.empty:
        result = result.merge(reasoning, on="child_segment", how="left", suffixes=("", "_reasoning"))
    result["recommended_product"] = result.get("best_product", result.get("primary_product", ""))
    result["recommended_customization"] = result.get("best_customization", result.get("primary_customization", ""))
    return sort_by_available(result, ["priority", "opportunity_score"], [True, False])


def score_metric_row(row: pd.Series, columns: list[str]) -> None:
    metric_cards([(column.replace("_", " ").title(), f"{numeric(row.get(column)):.1f}", "") for column in columns])


def decision_center() -> None:
    page_header(
        "Decision Center",
        "What should the team research this week?",
    )
    data = decision_data()
    roadmap = load_csv("portfolio_roadmap")
    if data.empty:
        st.info("Decision Center data is missing or empty.")
        return

    metric_cards(
        [
            ("Research Items", len(data), "Candidate child segments"),
            ("P1", int((data["priority"] == "P1").sum()) if "priority" in data.columns else 0, "Highest urgency"),
            ("Avg Score", f"{numeric(data['opportunity_score'].mean() if 'opportunity_score' in data.columns else 0):.1f}", "Opportunity score"),
            ("Roadmap Weeks", len(roadmap), "Weekly planning rows"),
        ]
    )

    section_break()
    st.subheader("Top 10 Research Priorities")
    render_research_cards(data, 10)

    section_break()
    st.subheader("Weekly Research Plan")
    display_table(
        roadmap,
        ["week", "parent_demand", "child_segment", "product", "customization", "priority", "reason"],
        height=360,
    )

    section_break()
    selected = st.selectbox("Select child segment", data["child_segment"].astype(str).drop_duplicates().tolist())
    row = data[data["child_segment"].astype(str) == selected].iloc[0]
    tab_breakdown, tab_product, tab_custom, tab_reasoning = st.tabs(
        ["Decision Breakdown", "Product Decision", "Customization Decision", "Analyst Reasoning"]
    )
    with tab_breakdown:
        score_metric_row(
            row,
            [
                "market_size_score",
                "growth_score",
                "competition_score",
                "expansion_score",
                "seasonality_score",
                "product_fit_score",
                "total_score",
            ],
        )
        st.write(clean_text(row.get("explanation")) or "No explanation available.")
    with tab_product:
        score_metric_row(row, ["blanket_score", "mug_score", "tumbler_score", "shirt_score", "ornament_score", "canvas_score"])
        st.markdown(f"**Best product:** {clean_text(row.get('best_product'))}")
        st.write(clean_text(row.get("explanation_product_fit")))
    with tab_custom:
        score_metric_row(row, ["photo", "name", "multiple_names", "birth_flower", "clipart", "line_art", "hand_drawing"])
        st.markdown(f"**Best customization:** {clean_text(row.get('best_customization'))}")
        st.write(clean_text(row.get("explanation_custom_fit")))
    with tab_reasoning:
        for label, column in [
            ("Strengths", "strengths"),
            ("Weaknesses", "weaknesses"),
            ("Risks", "risks"),
            ("Opportunities", "opportunities"),
            ("Why Now", "why_now"),
            ("Recommended Next Step", "recommended_next_step"),
        ]:
            st.markdown(f"#### {label}")
            st.write(clean_text(row.get(column)) or "No analyst note available.")


def card_grid(metrics: list[tuple[str, object, str | None]], per_row: int = 4) -> None:
    if not metrics:
        return
    for start in range(0, len(metrics), per_row):
        metric_cards(metrics[start : start + per_row])


def key_fragment(value: object) -> str:
    fragment = "".join(character.lower() if character.isalnum() else "_" for character in clean_text(value))
    fragment = "_".join(part for part in fragment.split("_") if part)
    return fragment[:60] or "market"


def confidence_from_score(score: object, priority: object = "") -> str:
    priority_value = clean_text(priority)
    score_value = numeric(score)
    if priority_value == "P1" or score_value >= 85:
        return "High"
    if priority_value == "P2" or score_value >= 70:
        return "Medium"
    return "Low"


def confidence_badge_class(confidence: object) -> str:
    value = clean_text(confidence)
    if value == "High":
        return "mrd-badge-p1"
    if value == "Medium":
        return "mrd-badge-p2"
    if value == "Low":
        return "mrd-badge-p3"
    return "mrd-badge-watch"


def research_status(priority: object, score: object) -> str:
    priority_value = clean_text(priority)
    score_value = numeric(score)
    if priority_value == "P1" or score_value >= 85:
        return "Ready"
    if priority_value == "P2" or score_value >= 70:
        return "Validate"
    return "Monitor"


def parent_market_options(
    portfolio_master: pd.DataFrame,
    market_intelligence: pd.DataFrame,
    queue: pd.DataFrame,
) -> list[str]:
    options: set[str] = set()
    if not portfolio_master.empty and "parent_demand" in portfolio_master.columns:
        options.update(clean_options(portfolio_master["parent_demand"]))
    if not market_intelligence.empty and "demand_name" in market_intelligence.columns:
        options.update(clean_options(market_intelligence["demand_name"]))
    if not queue.empty and "parent_demand" in queue.columns:
        options.update(clean_options(queue["parent_demand"]))
    return sorted(options)


def first_matching_row(df: pd.DataFrame, column: str, value: str) -> pd.Series:
    if df.empty or column not in df.columns:
        return pd.Series(dtype=object)
    matches = df[df[column].astype(str) == value]
    if matches.empty:
        return pd.Series(dtype=object)
    return matches.iloc[0]


def market_overview_metrics(
    parent_market: str,
    portfolio_master: pd.DataFrame,
    market_intelligence: pd.DataFrame,
    portfolio_summary: pd.DataFrame,
) -> list[tuple[str, object, str | None]]:
    portfolio_row = first_matching_row(portfolio_master, "parent_demand", parent_market)
    market_row = first_matching_row(market_intelligence, "demand_name", parent_market)
    summary_row = first_matching_row(portfolio_summary, "parent_demand", parent_market)

    coverage = first_existing_value(portfolio_row, ["coverage_score"])
    if not coverage:
        coverage = first_existing_value(summary_row, ["coverage_percent"])
    expansion = first_existing_value(portfolio_row, ["expansion_potential"])
    if not expansion:
        expansion = first_existing_value(market_row, ["expansion_score"])

    return [
        (
            "Market Size",
            first_existing_value(portfolio_row, ["market_size"], first_existing_value(market_row, ["market_size"], "Unknown")),
            "Parent market scale",
        ),
        (
            "Growth",
            first_existing_value(market_row, ["growth_stage"], "Unknown"),
            "Current movement signal",
        ),
        (
            "Competition",
            first_existing_value(market_row, ["competition_level"], "Unknown"),
            "Expected market friction",
        ),
        (
            "Coverage",
            f"{numeric(coverage):.1f}%" if coverage else "Unknown",
            "Estimated portfolio coverage",
        ),
        (
            "Expansion",
            f"{numeric(expansion):.1f}" if expansion else "Unknown",
            "Child-niche potential",
        ),
        (
            "Seasonality",
            first_existing_value(market_row, ["seasonality_type"], "Unknown"),
            "Research timing context",
        ),
        (
            "Current Stage",
            first_existing_value(portfolio_row, ["portfolio_stage"], first_existing_value(market_row, ["market_stage"], "Unknown")),
            "Portfolio maturity",
        ),
    ]


def parent_queue_rows(queue: pd.DataFrame, parent_market: str) -> pd.DataFrame:
    if queue.empty or "parent_demand" not in queue.columns:
        return pd.DataFrame()
    rows = queue[queue["parent_demand"].astype(str) == parent_market].copy()
    return sort_by_available(rows, ["priority", "opportunity_score"], [True, False])


def child_segments_for_parent(
    parent_market: str,
    queue: pd.DataFrame,
    portfolio_tree: pd.DataFrame,
    roadmap: pd.DataFrame,
) -> list[str]:
    segments: set[str] = set()
    if not queue.empty and {"parent_demand", "child_segment"}.issubset(queue.columns):
        rows = queue[queue["parent_demand"].astype(str) == parent_market]
        segments.update(clean_options(rows["child_segment"]))
    if not portfolio_tree.empty and {"parent_demand", "child_segment"}.issubset(portfolio_tree.columns):
        rows = portfolio_tree[portfolio_tree["parent_demand"].astype(str) == parent_market]
        segments.update(clean_options(rows["child_segment"]))
    if not roadmap.empty and {"parent_demand", "child_segment"}.issubset(roadmap.columns):
        rows = roadmap[roadmap["parent_demand"].astype(str) == parent_market]
        segments.update(clean_options(rows["child_segment"]))
    return sorted(segments)


def workspace_research_cards(rows: pd.DataFrame, limit: int = 6) -> None:
    if rows.empty:
        st.info("No child-segment research queue is available for this parent market.")
        return
    top_rows = rows.head(limit).reset_index(drop=True)
    for start in range(0, len(top_rows), 3):
        columns = st.columns(3)
        for column, (_, row) in zip(columns, top_rows.iloc[start : start + 3].iterrows()):
            priority = first_existing_value(row, ["priority", "recommended_priority"], "Watchlist")
            score = row.get("opportunity_score", row.get("total_score"))
            confidence = confidence_from_score(score, priority)
            status = research_status(priority, score)
            next_step = first_existing_value(row, ["next_action", "recommended_next_step", "explanation"], "Validate market evidence.")
            with column:
                st.markdown(
                    f"""
                    <div class="mrd-research-card">
                        <span class="mrd-badge {badge_class(priority)}">{safe(priority)}</span>
                        <span class="mrd-badge {confidence_badge_class(confidence)}" style="margin-left:0.35rem;">{safe(confidence)}</span>
                        <div class="mrd-research-title">{safe(row.get("child_segment"))}</div>
                        <div class="mrd-research-meta">Score {format_score(score)} | Status {safe(status)}</div>
                        <div class="mrd-research-line"><b>Reason:</b> {safe(row.get("reason", row.get("explanation")))}</div>
                        <div class="mrd-research-line"><b>Next Step:</b> {safe(next_step)}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


def ranked_fit_scores(
    fit: pd.DataFrame,
    child_segments: list[str],
    score_columns: dict[str, str],
) -> pd.DataFrame:
    if fit.empty or "child_segment" not in fit.columns or not child_segments:
        return pd.DataFrame()
    subset = fit[fit["child_segment"].astype(str).isin(child_segments)].copy()
    if subset.empty:
        return pd.DataFrame()

    rows: list[dict[str, object]] = []
    for column, label in score_columns.items():
        if column not in subset.columns:
            continue
        scores = pd.to_numeric(subset[column], errors="coerce")
        if scores.dropna().empty:
            continue
        best_index = scores.idxmax()
        fit_score = scores.mean()
        best_segment = clean_text(subset.loc[best_index].get("child_segment"))
        reason = clean_text(subset.loc[best_index].get("explanation"))
        if not reason:
            reason = f"Strongest fit signal appears in {best_segment}."
        rows.append(
            {
                "item": label,
                "fit_score": fit_score,
                "confidence": confidence_from_score(fit_score),
                "reason": reason,
                "source_segment": best_segment,
            }
        )
    return pd.DataFrame(rows).sort_values("fit_score", ascending=False)


def pipe_recommendation_scores(
    rows: pd.DataFrame,
    column: str,
    fallback_reason: str,
) -> pd.DataFrame:
    if rows.empty or column not in rows.columns:
        return pd.DataFrame()
    values: list[str] = []
    for value in rows[column].dropna():
        values.extend(split_pipe_values(value))
    if not values:
        return pd.DataFrame()
    counts = pd.Series(values).value_counts()
    max_count = numeric(counts.max(), 1)
    output_rows = []
    for item, count in counts.items():
        fit_score = 60 + (numeric(count) / max_count) * 35
        output_rows.append(
            {
                "item": item,
                "fit_score": fit_score,
                "confidence": confidence_from_score(fit_score),
                "reason": f"{fallback_reason} Appears in {int(count)} queued recommendation(s).",
                "source_segment": "",
            }
        )
    return pd.DataFrame(output_rows).sort_values("fit_score", ascending=False)


def render_ranked_recommendation_cards(rows: pd.DataFrame, item_label: str, limit: int = 5) -> None:
    if rows.empty:
        st.info(f"No {item_label.lower()} recommendation data is available for this parent market.")
        return
    top_rows = rows.head(limit).reset_index(drop=True)
    for start in range(0, len(top_rows), 3):
        columns = st.columns(3)
        for column, (_, row) in zip(columns, top_rows.iloc[start : start + 3].iterrows()):
            confidence = clean_text(row.get("confidence")) or confidence_from_score(row.get("fit_score"))
            with column:
                st.markdown(
                    f"""
                    <div class="mrd-card" style="min-height:210px;">
                        <span class="mrd-badge {confidence_badge_class(confidence)}">{safe(confidence)}</span>
                        <div class="mrd-card-label" style="margin-top:0.75rem;">{safe(item_label)}</div>
                        <div class="mrd-card-value" style="font-size:1.45rem;">{safe(row.get("item"))}</div>
                        <div class="mrd-card-note">Fit Score {format_score(row.get("fit_score"))}</div>
                        <div class="mrd-research-line"><b>Reason:</b> {safe(row.get("reason"))}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


def render_research_checklist(parent_market: str) -> None:
    tasks = [
        "Check Amazon Search",
        "Check Best Seller",
        "Check New Release",
        "Check Etsy",
        "Check Pinterest",
        "Check TikTok",
        "Verify competitors",
        "Build Design",
        "Upload",
        "Run Ads",
    ]
    prefix = f"workspace_checklist_{key_fragment(parent_market)}"
    columns = st.columns(2)
    for index, task in enumerate(tasks):
        with columns[index % 2]:
            st.checkbox(task, key=f"{prefix}_{key_fragment(task)}")


def related_markets(
    parent_market: str,
    portfolio_master: pd.DataFrame,
    market_intelligence: pd.DataFrame,
) -> pd.DataFrame:
    if portfolio_master.empty or "parent_demand" not in portfolio_master.columns:
        return pd.DataFrame()
    base = first_matching_row(portfolio_master, "parent_demand", parent_market)
    if base.empty:
        return pd.DataFrame()

    candidates = portfolio_master[portfolio_master["parent_demand"].astype(str) != parent_market].copy()
    if candidates.empty:
        return pd.DataFrame()
    if not market_intelligence.empty and "demand_name" in market_intelligence.columns:
        candidates = candidates.merge(
            market_intelligence[existing_columns(market_intelligence, ["demand_name", "growth_stage", "seasonality_type"])],
            left_on="parent_demand",
            right_on="demand_name",
            how="left",
        )

    rows: list[dict[str, object]] = []
    for _, row in candidates.iterrows():
        score = 0.0
        reasons: list[str] = []
        if clean_text(row.get("market_size")) == clean_text(base.get("market_size")):
            score += 25
            reasons.append("same market-size tier")
        if clean_text(row.get("investment_recommendation")) == clean_text(base.get("investment_recommendation")):
            score += 25
            reasons.append("same investment path")
        if clean_text(row.get("portfolio_stage")) == clean_text(base.get("portfolio_stage")):
            score += 15
            reasons.append("similar portfolio stage")
        if clean_text(row.get("research_priority")) == clean_text(base.get("research_priority")):
            score += 15
            reasons.append("same research priority")
        score += min(numeric(row.get("expansion_potential")), 100) * 0.2
        confidence = "High" if score >= 70 else "Medium" if score >= 45 else "Low"
        if not reasons:
            reasons.append("useful comparison market")
        rows.append(
            {
                "parent_market": row.get("parent_demand"),
                "confidence": confidence,
                "score": score,
                "reason": ", ".join(reasons),
            }
        )
    return pd.DataFrame(rows).sort_values("score", ascending=False).head(5)


def render_related_market_cards(rows: pd.DataFrame) -> None:
    if rows.empty:
        st.info("No related parent markets are available.")
        return
    for start in range(0, len(rows), 5):
        columns = st.columns(len(rows.iloc[start : start + 5]))
        for column, (_, row) in zip(columns, rows.iloc[start : start + 5].iterrows()):
            confidence = clean_text(row.get("confidence"))
            with column:
                st.markdown(
                    f"""
                    <div class="mrd-card" style="min-height:165px;">
                        <span class="mrd-badge {confidence_badge_class(confidence)}">{safe(confidence)}</span>
                        <div class="mrd-card-value" style="font-size:1.15rem;margin-top:0.75rem;">{safe(row.get("parent_market"))}</div>
                        <div class="mrd-card-note">{safe(row.get("reason"))}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


def research_workspace() -> None:
    page_header(
        "Research Workspace",
        "A working surface for choosing a parent market and executing the next research steps.",
    )
    portfolio_master = load_csv("portfolio_master")
    portfolio_summary = load_csv("portfolio_summary")
    market_intelligence = load_csv("market_intelligence")
    portfolio_tree = load_csv("portfolio_tree")
    portfolio_roadmap = load_csv("portfolio_roadmap")
    product_fit = load_csv("product_fit_matrix")
    customization_fit = load_csv("customization_fit_matrix")
    queue = decision_data()

    options = parent_market_options(portfolio_master, market_intelligence, queue)
    if not options:
        st.info("No parent market data is available for the workspace.")
        return

    selected_parent = st.selectbox("Choose Parent Market", options, key="research_workspace_parent")
    parent_rows = parent_queue_rows(queue, selected_parent)
    child_segments = child_segments_for_parent(selected_parent, parent_rows, portfolio_tree, portfolio_roadmap)

    section_break()
    st.subheader("Market Overview")
    card_grid(market_overview_metrics(selected_parent, portfolio_master, market_intelligence, portfolio_summary), 4)

    section_break()
    st.subheader("Research Queue")
    workspace_research_cards(parent_rows, 6)

    product_scores = ranked_fit_scores(
        product_fit,
        child_segments,
        {
            "blanket_score": "Blanket",
            "mug_score": "Mug",
            "tumbler_score": "Tumbler",
            "shirt_score": "Shirt",
            "ornament_score": "Ornament",
            "canvas_score": "Canvas",
        },
    )
    if product_scores.empty:
        product_scores = pipe_recommendation_scores(
            parent_rows,
            "product_recommendation",
            "Derived from queued product recommendations.",
        )

    section_break()
    st.subheader("Product Recommendation")
    render_ranked_recommendation_cards(product_scores, "Product", 6)

    customization_scores = ranked_fit_scores(
        customization_fit,
        child_segments,
        {
            "name": "Name",
            "photo": "Photo",
            "clipart": "Clipart",
            "birth_flower": "Birth Flower",
            "multiple_names": "Multiple Names",
            "line_art": "Line Art",
            "hand_drawing": "Hand Drawing",
        },
    )
    if customization_scores.empty:
        customization_scores = pipe_recommendation_scores(
            parent_rows,
            "customization_recommendation",
            "Derived from queued customization recommendations.",
        )

    section_break()
    st.subheader("Customization Recommendation")
    render_ranked_recommendation_cards(customization_scores, "Customization", 6)

    section_break()
    checklist_col, notes_col = st.columns([0.95, 1.05])
    with checklist_col:
        st.subheader("Research Checklist")
        render_research_checklist(selected_parent)
    with notes_col:
        st.subheader("Research Notes")
        st.text_area(
            "Session Notes",
            key=f"research_notes_{key_fragment(selected_parent)}",
            height=285,
            placeholder="Capture Amazon findings, design angles, competitor notes, and launch decisions here.",
            label_visibility="collapsed",
        )

    section_break()
    st.subheader("Next Recommended Markets")
    render_related_market_cards(related_markets(selected_parent, portfolio_master, market_intelligence))


def opportunity_explorer() -> None:
    page_header(
        "Opportunity Explorer",
        "Research queue and transparent opportunity scorecards.",
    )
    tab_queue, tab_scores = st.tabs(["Research Queue", "Opportunity Scorecards"])
    with tab_queue:
        research_queue_page()
    with tab_scores:
        opportunity_scorecard_page()


def research_queue_page() -> None:
    page_header(
        "Research Queue",
        "Prioritized child niches with product, customization, and next-action context.",
    )
    queue = build_research_queue()
    if queue.empty:
        st.info("Research queue data is missing. Expected decision and scoring CSVs.")
        return

    filters = st.columns(4)
    with filters[0]:
        queue = filter_multiselect(queue, "priority", "Priority", "rq_priority")
    with filters[1]:
        queue = filter_multiselect(queue, "parent_demand", "Parent Demand", "rq_parent")
    with filters[2]:
        queue = filter_pipe_multiselect(queue, "product_recommendation", "Product", "rq_product")
    with filters[3]:
        queue = filter_pipe_multiselect(queue, "customization_recommendation", "Customization", "rq_custom")

    metric_cards(
        [
            ("Visible Rows", len(queue), "Filtered research actions"),
            (
                "P1",
                int((queue["priority"] == "P1").sum()) if "priority" in queue.columns else 0,
                "Immediate research candidates",
            ),
            (
                "Avg Score",
                queue["opportunity_score"].mean() if "opportunity_score" in queue.columns else 0,
                "Transparent opportunity score",
            ),
            (
                "Parents",
                queue["parent_demand"].nunique() if "parent_demand" in queue.columns else 0,
                "Markets represented",
            ),
        ]
    )

    section_break()
    display_table(
        queue,
        [
            "priority",
            "parent_demand",
            "child_segment",
            "opportunity_score",
            "recommended_priority",
            "primary_product",
            "product_recommendation",
            "primary_customization",
            "customization_recommendation",
            "estimated_roi",
            "next_action",
            "explanation",
        ],
    )


def portfolio_planner() -> None:
    page_header(
        "Portfolio Strategy",
        "Portfolio coverage, investment recommendations, and weekly research roadmap.",
    )
    portfolio_master = load_csv("portfolio_master")
    portfolio_summary = load_csv("portfolio_summary")
    portfolio_roadmap = load_csv("portfolio_roadmap")

    if portfolio_master.empty and portfolio_summary.empty and portfolio_roadmap.empty:
        st.info("Portfolio CSVs are missing or empty.")
        return

    if not portfolio_master.empty:
        filters = st.columns(3)
        with filters[0]:
            portfolio_master = filter_multiselect(
                portfolio_master,
                "portfolio_stage",
                "Portfolio Stage",
                "portfolio_stage",
            )
        with filters[1]:
            portfolio_master = filter_multiselect(
                portfolio_master,
                "investment_recommendation",
                "Investment Recommendation",
                "portfolio_investment",
            )
        with filters[2]:
            portfolio_master = filter_multiselect(
                portfolio_master,
                "market_size",
                "Market Size",
                "portfolio_market_size",
            )

    metric_cards(
        [
            ("Portfolios", len(portfolio_master), "Filtered parent markets"),
            (
                "Avg Coverage",
                portfolio_master["coverage_score"].mean() if "coverage_score" in portfolio_master.columns else 0,
                "Estimated portfolio coverage",
            ),
            (
                "Expand",
                int((portfolio_master["investment_recommendation"] == "Expand").sum())
                if "investment_recommendation" in portfolio_master.columns
                else 0,
                "Expansion recommendations",
            ),
            (
                "Invest Aggressively",
                int((portfolio_master["investment_recommendation"] == "Invest Aggressively").sum())
                if "investment_recommendation" in portfolio_master.columns
                else 0,
                "Highest investment tier",
            ),
        ]
    )

    section_break()
    tab_master, tab_summary, tab_roadmap = st.tabs(["Portfolio Master", "Summary", "Roadmap by Week"])

    with tab_master:
        display_table(
            portfolio_master,
            [
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
            ],
        )

    with tab_summary:
        display_table(
            portfolio_summary,
            [
                "parent_demand",
                "current_child_segments",
                "estimated_total_segments",
                "coverage_percent",
                "average_score",
                "best_products",
                "strongest_customization",
                "next_recommendation",
            ],
        )

    with tab_roadmap:
        display_table(
            portfolio_roadmap,
            [
                "week",
                "parent_demand",
                "child_segment",
                "product",
                "customization",
                "priority",
                "reason",
            ],
        )


def opportunity_scorecard_page() -> None:
    page_header(
        "Opportunity Scorecard",
        "Transparent score breakdown for each child segment.",
    )
    scorecard = load_csv("opportunity_scorecard")
    if scorecard.empty:
        st.info("Opportunity scorecard CSV is missing or empty.")
        return

    filters = st.columns(3)
    with filters[0]:
        scorecard = filter_multiselect(scorecard, "parent_demand", "Parent Demand", "score_parent")
    with filters[1]:
        scorecard = filter_multiselect(
            scorecard,
            "recommended_priority",
            "Recommended Priority",
            "score_priority",
        )
    with filters[2]:
        min_score = st.slider("Minimum Total Score", 0, 100, 0, 5)
        if "total_score" in scorecard.columns:
            scorecard = scorecard[scorecard["total_score"] >= min_score]

    scorecard = sort_by_available(scorecard, ["total_score", "child_segment"], [False, True])
    selected_segment = None
    if not scorecard.empty and "child_segment" in scorecard.columns:
        selected_segment = st.selectbox(
            "Inspect Segment",
            scorecard["child_segment"].astype(str).tolist(),
            key="score_inspect",
        )

    if selected_segment:
        row = scorecard[scorecard["child_segment"].astype(str) == selected_segment].iloc[0]
        score_data = pd.DataFrame(
            {
                "score": [
                    numeric(row.get("market_size_score")),
                    numeric(row.get("growth_score")),
                    numeric(row.get("competition_score")),
                    numeric(row.get("expansion_score")),
                    numeric(row.get("seasonality_score")),
                    numeric(row.get("product_fit_score")),
                    numeric(row.get("total_score")),
                ]
            },
            index=[
                "Market Size",
                "Growth",
                "Competition",
                "Expansion",
                "Seasonality",
                "Product Fit",
                "Total",
            ],
        )
        chart_col, note_col = st.columns([1.2, 1])
        with chart_col:
            st.bar_chart(score_data)
        with note_col:
            st.markdown("#### Explanation")
            st.write(clean_text(row.get("explanation")) or "No explanation available.")

    section_break()
    display_table(
        scorecard,
        [
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
        ],
    )


def product_customization_fit() -> None:
    page_header(
        "Product Intelligence",
        "Best-fit products and personalization systems for child niches.",
    )
    product_fit = load_csv("product_fit_matrix")
    customization_fit = load_csv("customization_fit_matrix")

    if product_fit.empty and customization_fit.empty:
        st.info("Product and customization fit CSVs are missing or empty.")
        return

    combined = product_fit.merge(customization_fit, on="child_segment", how="outer", suffixes=("_product", "_custom"))
    filters = st.columns(3)
    with filters[0]:
        combined = filter_multiselect(combined, "best_product", "Best Product", "fit_product")
    with filters[1]:
        combined = filter_multiselect(combined, "best_customization", "Best Customization", "fit_custom")
    with filters[2]:
        if "child_segment" in combined.columns:
            text_filter = st.text_input("Search Child Segment", key="fit_search")
            if text_filter.strip():
                combined = combined[
                    combined["child_segment"].astype(str).str.contains(text_filter.strip(), case=False, na=False)
                ]

    tab_combined, tab_products, tab_customization = st.tabs(
        ["Combined Fit", "Product Scores", "Customization Scores"]
    )

    with tab_combined:
        display_table(
            combined,
            [
                "child_segment",
                "best_product",
                "best_customization",
                "blanket_score",
                "mug_score",
                "tumbler_score",
                "shirt_score",
                "ornament_score",
                "canvas_score",
                "photo",
                "name",
                "multiple_names",
                "birth_flower",
                "clipart",
                "line_art",
                "hand_drawing",
            ],
        )

    with tab_products:
        display_table(
            product_fit,
            [
                "child_segment",
                "best_product",
                "blanket_score",
                "mug_score",
                "tumbler_score",
                "shirt_score",
                "ornament_score",
                "canvas_score",
                "explanation",
            ],
        )

    with tab_customization:
        display_table(
            customization_fit,
            [
                "child_segment",
                "best_customization",
                "photo",
                "name",
                "multiple_names",
                "birth_flower",
                "clipart",
                "line_art",
                "hand_drawing",
                "explanation",
            ],
        )


def summarized_evidence_frame(record: pd.Series) -> pd.DataFrame:
    if "evidence_keywords" not in record.index or pd.isna(record["evidence_keywords"]):
        return pd.DataFrame(columns=["keyword_order", "keyword"])
    keywords = [keyword.strip() for keyword in str(record["evidence_keywords"]).split("|") if keyword.strip()]
    return pd.DataFrame({"keyword_order": range(1, len(keywords) + 1), "keyword": keywords})


def merge_summary_evidence(records: pd.DataFrame, fallback: pd.DataFrame, id_column: str) -> pd.DataFrame:
    if (
        records.empty
        or fallback.empty
        or id_column not in records.columns
        or id_column not in fallback.columns
        or "evidence_keywords" not in fallback.columns
    ):
        return records

    evidence = fallback[[id_column, "evidence_keywords"]].dropna(subset=[id_column]).copy()
    if evidence.empty:
        return records

    if "evidence_keywords" not in records.columns:
        return records.merge(evidence, on=id_column, how="left")

    merged = records.merge(evidence, on=id_column, how="left", suffixes=("", "_fallback"))
    merged["evidence_keywords"] = merged["evidence_keywords"].where(
        merged["evidence_keywords"].notna() & (merged["evidence_keywords"].astype(str).str.strip() != ""),
        merged["evidence_keywords_fallback"],
    )
    return merged.drop(columns=["evidence_keywords_fallback"])


def monthly_curve(evidence: pd.DataFrame, id_column: str, selected_id: str) -> pd.DataFrame:
    required = {id_column, "month", "search_frequency_rank", "normalized_keyword"}
    if evidence.empty or not required.issubset(evidence.columns):
        return pd.DataFrame()
    rows = evidence[evidence[id_column].astype(str) == str(selected_id)].copy()
    if rows.empty:
        return pd.DataFrame()
    return (
        rows.groupby("month", as_index=False)
        .agg(
            best_rank=("search_frequency_rank", "min"),
            median_rank=("search_frequency_rank", "median"),
            keyword_count=("normalized_keyword", "count"),
        )
        .sort_values("month")
    )


def select_record(df: pd.DataFrame, label_column: str, id_column: str, key: str) -> pd.Series | None:
    if df.empty or label_column not in df.columns or id_column not in df.columns:
        return None
    working = df.copy()
    working["_select_label"] = working[label_column].astype(str) + "  [" + working[id_column].astype(str) + "]"
    selected = st.selectbox("Select record", working["_select_label"].tolist(), key=key)
    if not selected:
        return None
    return working[working["_select_label"] == selected].iloc[0]


def select_record_with_keys(
    df: pd.DataFrame,
    label_columns: list[str],
    id_columns: list[str],
    key: str,
) -> pd.Series | None:
    label_column = next((column for column in label_columns if column in df.columns), None)
    id_column = next((column for column in id_columns if column in df.columns), label_column)
    if not label_column or not id_column:
        return None
    return select_record(df, label_column, id_column, key)


def show_evidence_detail(
    record: pd.Series,
    evidence: pd.DataFrame | None = None,
    id_column: str | None = None,
    record_id: str | None = None,
) -> None:
    metric_cards(
        [
            ("Best Rank", record.get("best_rank", 0), "Lowest known rank"),
            ("Median Rank", record.get("median_rank", 0), "Middle evidence rank"),
            ("Active Months", record.get("active_months", 0), "Observed months"),
            ("Keyword Count", record.get("keyword_count", 0), "Evidence breadth"),
        ]
    )

    if "evidence_keywords" in record.index and pd.notna(record["evidence_keywords"]):
        st.text_area("Evidence Keywords", str(record["evidence_keywords"]), height=120, disabled=True)

    summary_rows = summarized_evidence_frame(record)
    evidence = evidence if evidence is not None else pd.DataFrame()

    if evidence.empty or not id_column or not record_id or id_column not in evidence.columns:
        if not summary_rows.empty:
            st.info("Showing summarized evidence from available dashboard data.")
            st.subheader("Keyword Evidence")
            st.dataframe(summary_rows, use_container_width=True, hide_index=True, height=320)
        else:
            st.info("Detailed keyword evidence file is missing or empty.")
        return

    rows = evidence[evidence[id_column].astype(str) == str(record_id)].copy()
    if rows.empty:
        if not summary_rows.empty:
            st.info("Showing summarized evidence from available dashboard data.")
            st.subheader("Keyword Evidence")
            st.dataframe(summary_rows, use_container_width=True, hide_index=True, height=320)
        else:
            st.info("Detailed keyword evidence file is missing or empty.")
        return

    st.subheader("Keyword Evidence")
    rows = sort_by_available(rows, ["search_frequency_rank", "month"], [True, True])
    display_table(
        rows.head(200),
        ["raw_keyword", "normalized_keyword", "month", "search_frequency_rank"],
        height=360,
    )

    curve = monthly_curve(evidence, id_column, record_id)
    if not curve.empty:
        st.subheader("Monthly Trend")
        st.line_chart(curve.set_index("month")[["best_rank", "median_rank"]])
        display_table(curve, ["month", "best_rank", "median_rank", "keyword_count"], height=220)


def market_evidence() -> None:
    page_header(
        "Market Evidence",
        "Keyword evidence from compact evidence-light files, with evidence_keywords fallback.",
    )
    source = st.radio("Evidence Source", ["Demand", "Segment", "Opportunity", "Market Node"], horizontal=True)

    if source == "Demand":
        records = merge_summary_evidence(load_csv("composite_demands"), load_csv("opportunity_master"), "demand_id")
        records = sort_by_available(records, ["best_rank", "keyword_count"], [True, False])
        selected = select_record_with_keys(records, ["demand_name"], ["demand_id", "demand_name"], "evidence_demand")
        if selected is None:
            st.info("No demand records available.")
            return
        st.subheader(clean_text(selected.get("demand_name")) or "Demand")
        show_evidence_detail(
            selected,
            load_csv("demand_evidence_light"),
            "demand_id",
            clean_text(selected.get("demand_id", selected.get("demand_name", ""))),
        )
        return

    if source == "Segment":
        records = sort_by_available(load_csv("demand_segments"), ["segment_strength", "best_rank"], [False, True])
        selected = select_record_with_keys(records, ["segment_name"], ["segment_id", "segment_name"], "evidence_segment")
        if selected is None:
            st.info("No segment records available.")
            return
        st.subheader(clean_text(selected.get("segment_name")) or "Segment")
        show_evidence_detail(
            selected,
            load_csv("segment_evidence_light"),
            "segment_id",
            clean_text(selected.get("segment_id", selected.get("segment_name", ""))),
        )
        return

    if source == "Market Node":
        records = sort_by_available(load_csv("market_nodes"), ["strength_score", "best_rank"], [False, True])
        selected = select_record_with_keys(records, ["demand"], ["market_node_id", "demand"], "evidence_market_node")
        if selected is None:
            st.info("No market node records available.")
            return
        label = clean_text(selected.get("demand")) or "Market Node"
        niche = clean_text(selected.get("niche"))
        st.subheader(f"{label} + {niche}" if niche else label)
        show_evidence_detail(
            selected,
            load_csv("market_node_evidence_light"),
            "market_node_id",
            clean_text(selected.get("market_node_id", selected.get("demand", ""))),
        )
        return

    records = sort_by_available(load_csv("opportunity_master"), ["opportunity_score", "best_rank"], [False, True])
    selected = select_record_with_keys(records, ["demand_name"], ["opportunity_id", "demand_name"], "evidence_opp")
    if selected is None:
        st.info("No opportunity records available.")
        return
    st.subheader(clean_text(selected.get("demand_name")) or "Opportunity")
    show_evidence_detail(
        selected,
        load_csv("demand_evidence_light"),
        "demand_id",
        clean_text(selected.get("demand_id", selected.get("demand_name", ""))),
    )


# Sprint 30 decision dashboard pages. These functions intentionally keep raw
# dataframes inside expanders and use existing compact CSV outputs only.
PRODUCT_SCORE_COLUMNS = {
    "blanket_score": "Blanket",
    "mug_score": "Mug",
    "tumbler_score": "Tumbler",
    "shirt_score": "Shirt",
    "ornament_score": "Ornament",
    "canvas_score": "Canvas",
}

CUSTOMIZATION_SCORE_COLUMNS = {
    "name": "Name",
    "photo": "Photo",
    "multiple_names": "Multiple Names",
    "birth_flower": "Birth Flower",
    "clipart": "Clipart",
    "line_art": "Line Art",
    "hand_drawing": "Hand Drawing",
}


def insight_box(title: str, body: str) -> None:
    st.markdown(
        f"""
        <div class="mrd-card" style="min-height:120px;">
            <div class="mrd-card-label">{safe(title)}</div>
            <div class="mrd-research-line" style="font-size:0.95rem;line-height:1.55;">{safe(body)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def action_card(
    title: object,
    badge: object,
    score: object,
    lines: list[tuple[str, object]],
    badge_style: str | None = None,
) -> None:
    badge_value = clean_text(badge) or "Decision"
    style = badge_style or badge_class(badge_value)
    score_text = format_score(score)
    score_line = f'<div class="mrd-research-meta">Score {safe(score_text)}</div>' if score_text else ""
    st.markdown(
        f"""
        <div class="mrd-research-card">
            <span class="mrd-badge {style}">{safe(badge_value)}</span>
            <div class="mrd-research-title">{safe(title)}</div>
            {score_line}
            {''.join(f'<div class="mrd-research-line"><b>{safe(label)}:</b> {safe(value)}</div>' for label, value in lines)}
        </div>
        """,
        unsafe_allow_html=True,
    )


def score_to_decision(score: object) -> str:
    value = numeric(score)
    if value >= 80:
        return "Create now"
    if value >= 70:
        return "Validate first"
    if value >= 60:
        return "Monitor"
    return "Ignore"


def demand_options() -> list[str]:
    queue = build_research_queue()
    return parent_market_options(load_csv("portfolio_master"), load_csv("market_intelligence"), queue)


def calendar_row_for_demand(demand_name: str) -> pd.Series:
    calendar = load_csv("market_calendar")
    if not calendar.empty and "demand" in calendar.columns:
        row = first_matching_row(calendar, "demand", demand_name)
        if not row.empty:
            return row
    return pd.Series(dtype=object)


def inferred_timeline(demand_name: str, seasonality: object) -> dict[str, str]:
    row = calendar_row_for_demand(demand_name)
    if not row.empty:
        return {
            "Research Month": first_existing_value(row, ["research_month"], "Any Month"),
            "Listing / Upload": first_existing_value(row, ["listing_month"], "Rolling"),
            "Ads Month": first_existing_value(row, ["ads_month"], "Always-on"),
            "Peak Month": first_existing_value(row, ["peak_month"], "Evergreen"),
        }

    season = clean_text(seasonality).lower()
    if "q4" in season or "holiday" in season or "christmas" in demand_name.lower():
        return {
            "Research Month": "August",
            "Listing / Upload": "September",
            "Ads Month": "October",
            "Peak Month": "December",
        }
    if "evergreen" in season or not season:
        return {
            "Research Month": "Any Month",
            "Listing / Upload": "Rolling",
            "Ads Month": "Always-on",
            "Peak Month": "Evergreen",
        }
    return {
        "Research Month": "Three months before peak",
        "Listing / Upload": "Two months before peak",
        "Ads Month": "One month before peak",
        "Peak Month": clean_text(seasonality) or "Unproven",
    }


def demand_market_row(demand_name: str, markets: pd.DataFrame) -> pd.Series:
    row = first_matching_row(markets, "Parent Market", demand_name)
    if not row.empty:
        return row
    return pd.Series(dtype=object)


def demand_executive_insight(demand_name: str, row: pd.Series, queue_rows: pd.DataFrame) -> str:
    investment = first_existing_value(row, ["Investment"], "Monitor")
    growth = first_existing_value(row, ["Growth"], "unknown growth")
    competition = first_existing_value(row, ["Competition"], "unknown competition")
    seasonality = first_existing_value(row, ["Seasonality"], "Evergreen")
    stage = first_existing_value(row, ["Portfolio Stage", "Market Stage"], "Unknown")
    coverage = numeric(row.get("Coverage"))
    expansion = numeric(row.get("Expansion Potential"))
    child_count = len(queue_rows)

    if investment in {"Invest Aggressively", "Expand"} or expansion >= 70:
        invest_text = f"{demand_name} is worth active investment."
    else:
        invest_text = f"{demand_name} should be handled selectively until stronger signals appear."

    if child_count >= 3 or stage in {"Mature", "Growing"}:
        research_text = "Research child niches first; the parent demand should act as the market umbrella."
    else:
        research_text = "Validate the parent demand before expanding into many child niches."

    if competition == "High":
        risk = "The biggest risk is crowded competition, so avoid generic listings."
    elif coverage < 40 and expansion >= 60:
        risk = "The biggest risk is under-coverage, which can leave obvious child niches untested."
    elif seasonality != "Evergreen":
        risk = "The biggest risk is timing; research and upload need to happen before the seasonal ramp."
    else:
        risk = "The biggest risk is spending design time on weak child segments."

    return f"{invest_text} It is currently {clean_text(growth).lower()} with {clean_text(competition).lower()} competition and a {clean_text(stage).lower()} portfolio stage. {research_text} {risk}"


def prepare_market_rankings(markets: pd.DataFrame) -> pd.DataFrame:
    if markets.empty:
        return markets
    ranked = markets.copy()
    market_size = numeric_market_series(ranked, ["Market Size Score"])
    expansion = numeric_market_series(ranked, ["Expansion Potential"])
    average_opportunity = numeric_market_series(ranked, ["Average Opportunity"])
    growth = numeric_market_series(ranked, ["Growth Score"])
    best_child = numeric_market_series(ranked, ["Best Child Score"])
    coverage = numeric_market_series(ranked, ["Coverage"])
    child_count = numeric_market_series(ranked, ["Child Segment Count"])
    ranked["Market Rank Score"] = (
        market_size * 0.25
        + expansion * 0.25
        + average_opportunity * 0.20
        + growth * 0.15
        + best_child * 0.10
        + (100 - coverage).clip(lower=0) * 0.05
    )
    ranked["Expansion Opportunity Score"] = (
        expansion * 0.45
        + average_opportunity * 0.25
        + child_count.clip(upper=20) * 2
        + (100 - coverage).clip(lower=0) * 0.10
    )
    ranked["Risk Score"] = (
        (100 - ranked["Market Rank Score"]).clip(lower=0) * 0.45
        + (100 - average_opportunity).clip(lower=0) * 0.25
        + coverage.where(coverage < 20, 0) * 0.20
    )
    return ranked


def market_recommended_action(row: pd.Series) -> str:
    investment = first_existing_value(row, ["Investment"], "Monitor")
    expansion = numeric(row.get("Expansion Potential"))
    coverage = numeric(row.get("Coverage"))
    opportunity = numeric(row.get("Average Opportunity"))
    competition = clean_text(row.get("Competition"))
    recommendation = first_existing_value(row, ["Recommendation"])
    if investment == "Invest Aggressively" or (expansion >= 75 and opportunity >= 70):
        return "Research child niches now."
    if investment == "Expand" or (expansion >= 65 and coverage < 60):
        return "Expand with focused child tests."
    if competition == "High" and opportunity < 65:
        return "Validate before design work."
    if recommendation:
        return recommendation
    return "Monitor until stronger evidence appears."


def executive_market_overview(markets: pd.DataFrame, queue: pd.DataFrame) -> None:
    total_demands = len(markets)
    sizes = markets.get("Market Size", pd.Series(dtype=str)).astype(str)
    investment = markets.get("Investment", pd.Series(dtype=str)).astype(str)
    total_child_niches = (
        queue["child_segment"].nunique()
        if not queue.empty and "child_segment" in queue.columns
        else int(markets.get("Child Segment Count", pd.Series(dtype=float)).sum())
    )
    metric_cards(
        [
            ("Total Demands", total_demands, "Parent markets ranked"),
            ("Mega Markets", int((sizes == "Mega").sum()), "Largest market tier"),
            ("Large Markets", int((sizes == "Large").sum()), "Large market tier"),
            ("P1 Markets", int(((investment == "P1") | (investment == "Invest Aggressively")).sum()), "Highest priority"),
            ("Total Child Niches", total_child_niches, "Known child opportunities"),
            ("Average Coverage", f"{numeric(markets['Coverage'].mean() if 'Coverage' in markets.columns else 0):.1f}%", "Portfolio coverage"),
        ]
    )


def market_investment_cards(markets: pd.DataFrame, limit: int = 15) -> None:
    portfolio_metric_legend()
    if markets.empty:
        st.info("No market ranking data is available.")
        return
    top = markets.head(limit).reset_index(drop=True)
    for start in range(0, len(top), 3):
        columns = st.columns(3)
        for column, (index, row) in zip(columns, top.iloc[start : start + 3].iterrows()):
            with column:
                st.markdown(portfolio_card_html(row, index + 1), unsafe_allow_html=True)


def market_size_ranking_chart(markets: pd.DataFrame) -> None:
    if markets.empty or "Market Rank Score" not in markets.columns:
        st.info("No market-size ranking data is available.")
        return
    chart_data = markets.head(25).copy()
    chart = (
        alt.Chart(chart_data)
        .mark_bar()
        .encode(
            x=alt.X("Market Rank Score:Q", title="Overall market score"),
            y=alt.Y("Parent Market:N", sort="-x", title=None),
            color=alt.Color("Market Size:N", title="Market Size"),
            tooltip=[
                "Parent Market",
                "Market Size",
                "Growth",
                "Competition",
                alt.Tooltip("Coverage:Q", format=".1f"),
                alt.Tooltip("Expansion Potential:Q", format=".1f"),
                alt.Tooltip("Market Rank Score:Q", format=".1f"),
            ],
        )
        .properties(height=520, title="Market Size Ranking")
    )
    st.altair_chart(dark_chart(chart), use_container_width=True)


def portfolio_metric_legend() -> None:
    st.markdown(
        """
        <div class="mrd-portfolio-legend">
            <strong>How to read</strong>
            <ul>
                <li>Detected Segment Coverage = % of discovered child segments.</li>
                <li>Expansion Potential = Remaining opportunity to expand this parent market.</li>
                <li>Best targets = Low Coverage + High Expansion Potential.</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )


def compact_market_opportunity_cards(markets: pd.DataFrame, title: str, mode: str, limit: int = 6) -> None:
    st.subheader(title)
    if mode == "expansion":
        portfolio_metric_legend()
    if markets.empty:
        st.info("No markets are available for this section.")
        return
    rows = markets.head(limit).reset_index(drop=True)
    for start in range(0, len(rows), 3):
        columns = st.columns(3)
        for column, (_, row) in zip(columns, rows.iloc[start : start + 3].iterrows()):
            if mode == "risk":
                note = f"Risk score {format_score(row.get('Risk Score'))}. Action: {market_recommended_action(row)}"
                badge = "Review"
            with column:
                if mode == "risk":
                    with st.container(border=True):
                        st.caption(badge)
                        st.markdown(f"**{clean_text(row.get('Parent Market'))}**")
                        st.caption(
                            f"{clean_text(row.get('Market Size'))} | "
                            f"{clean_text(row.get('Growth'))} | "
                            f"{clean_text(row.get('Competition'))}"
                        )
                        st.markdown(note)
                else:
                    st.markdown(portfolio_card_html(row, default_investment="Expand"), unsafe_allow_html=True)


def weekly_research_focus(queue: pd.DataFrame, limit: int = 10) -> None:
    st.subheader("Weekly Research Focus")
    if queue.empty:
        st.info("No research candidates are available.")
        return
    rows = sort_by_available(queue, ["priority", "opportunity_score"], [True, False]).head(limit).reset_index(drop=True)
    for start in range(0, len(rows), 2):
        columns = st.columns(2)
        for column, (_, row) in zip(columns, rows.iloc[start : start + 2].iterrows()):
            with column:
                action_card(
                    row.get("child_segment"),
                    first_existing_value(row, ["priority", "recommended_priority"], "Watchlist"),
                    row.get("opportunity_score", row.get("total_score")),
                    [
                        ("Parent demand", row.get("parent_demand")),
                        ("Product", first_existing_value(row, ["recommended_product", "best_product", "primary_product"])),
                        ("Customization", first_existing_value(row, ["recommended_customization", "best_customization", "primary_customization"])),
                        ("Next action", first_existing_value(row, ["next_action", "recommended_next_step", "reason"], "Validate market evidence.")),
                    ],
                )


def child_detail_expander(row: pd.Series, key_prefix: str) -> None:
    child = clean_text(row.get("child_segment")) or key_prefix
    with st.expander(f"View detail: {child}", expanded=False):
        keywords = split_pipe_values(row.get("evidence_keywords"))
        st.markdown("#### Evidence Summary")
        card_grid(
            [
                (
                    "Evidence Count",
                    count_share_label(row.get("evidence_example_count", len(keywords)), row.get("evidence_example_denominator", len(keywords)), "evidence keywords"),
                    f"Estimated share {format_score(row.get('estimated_share'))}%",
                ),
                (
                    "Product",
                    selected_product_label(row),
                    f"Fit score {format_score(score_for_label(row, PRODUCT_SCORE_COLUMNS, selected_product_label(row)))}",
                ),
                (
                    "Customization",
                    selected_customization_label(row),
                    f"Fit score {format_score(score_for_label(row, CUSTOMIZATION_SCORE_COLUMNS, selected_customization_label(row)))}",
                ),
                (
                    "Opportunity",
                    f"{format_score(row.get('opportunity_score', row.get('total_score')))}",
                    f"Priority {first_existing_value(row, ['priority', 'recommended_priority'], 'unavailable')}",
                ),
            ],
            4,
        )

        st.markdown("#### Score Breakdown")
        score_breakdown_cards(row)

        product_rows = segment_fit_scores(row, PRODUCT_SCORE_COLUMNS)
        customization_rows = segment_fit_scores(row, CUSTOMIZATION_SCORE_COLUMNS)
        product_col, custom_col = st.columns(2)
        with product_col:
            st.markdown("#### Product Fit")
            if product_rows.empty:
                st.write("No product fit scores available.")
            else:
                display_table(product_rows, ["item", "score", "fit_level"], height=220)
        with custom_col:
            st.markdown("#### Customization Fit")
            if customization_rows.empty:
                st.write("No customization fit scores available.")
            else:
                display_table(customization_rows, ["item", "score", "fit_level"], height=220)

        for label, field in [
            ("Strengths", "strengths"),
            ("Weaknesses", "weaknesses"),
            ("Risks", "risks"),
            ("Opportunities", "opportunities"),
            ("Next Step", "recommended_next_step"),
        ]:
            value = clean_text(row.get(field))
            if value:
                st.markdown(f"#### {label}")
                st.write(value)

        if keywords:
            st.markdown("#### Keywords")
            display_table(pd.DataFrame({"keyword": keywords}), ["keyword"], height=220)


def demand_evidence_cards(demand_name: str, demand_segments: pd.DataFrame, composite_demands: pd.DataFrame) -> None:
    keywords = demand_evidence_keywords(demand_name, demand_segments, composite_demands)
    confidence = evidence_confidence(len(keywords))
    card_grid(
        [
            ("Evidence Confidence", confidence, f"{len(keywords)} summarized keywords"),
            ("Theme", evidence_summary_text(keywords, THEME_TERMS), f"Share of {len(keywords)} evidence keywords"),
            ("Product Mention", evidence_summary_text(keywords, PRODUCT_TERMS), f"Share of {len(keywords)} evidence keywords"),
            ("Occasion", evidence_summary_text(keywords, OCCASION_TERMS), f"Share of {len(keywords)} evidence keywords"),
            ("Customization Mention", evidence_summary_text(keywords, CUSTOMIZATION_TERMS), f"Share of {len(keywords)} evidence keywords"),
        ],
        3,
    )
    with st.expander("Keyword evidence details", expanded=False):
        if not keywords:
            st.info("No summarized evidence keywords are available for this demand.")
        else:
            display_table(pd.DataFrame({"keyword_order": range(1, len(keywords[:100]) + 1), "keyword": keywords[:100]}), height=320)


THEME_TERMS = {
    "Funny": ["funny", "gag", "joke"],
    "Family": ["family", "mom", "dad", "mother", "father", "grandma", "grandpa", "daughter", "son"],
    "Pet": ["dog", "cat", "pet"],
    "Faith": ["christian", "religious", "faith", "bible"],
    "Sports": ["soccer", "football", "baseball", "golf", "fishing", "hunting"],
    "Wedding": ["wedding", "bride", "groom"],
    "Seasonal": ["christmas", "halloween", "valentine", "easter", "thanksgiving"],
}

OCCASION_TERMS = {
    "Mother": ["mother", "mom", "mother's day", "mothers day"],
    "Father": ["father", "dad", "father's day", "fathers day"],
    "Christmas": ["christmas", "xmas"],
    "Birthday": ["birthday"],
    "Wedding": ["wedding", "bride", "groom"],
    "Anniversary": ["anniversary"],
    "Retirement": ["retirement", "retired"],
    "Graduation": ["graduation", "graduate"],
    "Memorial": ["memorial", "remembrance", "in memory"],
}

PRODUCT_TERMS = {
    "Blanket": ["blanket", "throw"],
    "Mug": ["mug"],
    "Tumbler": ["tumbler", "water bottle", "cup"],
    "Shirt": ["shirt", "t-shirt", "tee", "hoodie", "sweatshirt"],
    "Ornament": ["ornament"],
    "Canvas": ["canvas", "poster", "print", "wall art"],
}

CUSTOMIZATION_TERMS = {
    "Name": ["name", "personalized", "custom", "customized"],
    "Photo": ["photo", "picture"],
    "Multiple Names": ["multiple names", "kids names", "grandkids", "family names", "children names"],
    "Birth Flower": ["birth flower", "birthflower"],
    "Clipart": ["clipart", "clip art", "illustration"],
    "Line Art": ["line art", "line drawing"],
    "Hand Drawing": ["hand drawing", "hand drawn", "drawing"],
}


def percent_label(numerator: object, denominator: object, precision: int = 1) -> str:
    denom = numeric(denominator)
    if denom <= 0:
        return "0.0%"
    return f"{(numeric(numerator) / denom) * 100:.{precision}f}%"


def count_share_label(numerator: object, denominator: object, label: str = "evidence") -> str:
    return f"{format_int(numerator)} / {format_int(denominator)} {label}"


def demand_evidence_keywords(demand_name: str, demand_segments: pd.DataFrame, composite_demands: pd.DataFrame) -> list[str]:
    keywords: list[str] = []
    if not demand_segments.empty and "parent_demand" in demand_segments.columns and "evidence_keywords" in demand_segments.columns:
        rows = demand_segments[demand_segments["parent_demand"].astype(str) == demand_name]
        for value in rows["evidence_keywords"].dropna():
            keywords.extend(split_pipe_values(value))
    if not composite_demands.empty and "demand_name" in composite_demands.columns and "evidence_keywords" in composite_demands.columns:
        rows = composite_demands[composite_demands["demand_name"].astype(str) == demand_name]
        for value in rows["evidence_keywords"].dropna():
            keywords.extend(split_pipe_values(value))
    return keywords


def term_count(keywords: list[str], terms: list[str]) -> int:
    lowered_terms = [term.lower() for term in terms]
    count = 0
    for keyword in keywords:
        lower = keyword.lower()
        if any(term in lower for term in lowered_terms):
            count += 1
    return count


def term_distribution(keywords: list[str], mapping: dict[str, list[str]]) -> pd.DataFrame:
    denominator = len(keywords)
    rows = []
    for label, terms in mapping.items():
        count = term_count(keywords, terms)
        rows.append(
            {
                "item": label,
                "count": count,
                "denominator": denominator,
                "share": (count / denominator * 100) if denominator else 0,
            }
        )
    return pd.DataFrame(rows).sort_values(["share", "count"], ascending=False)


def evidence_summary_text(keywords: list[str], mapping: dict[str, list[str]], limit: int = 4) -> str:
    distribution = term_distribution(keywords, mapping)
    if distribution.empty or numeric(distribution["count"].sum()) <= 0:
        return "0.0% matched"
    rows = distribution[distribution["count"] > 0].head(limit)
    return " | ".join(
        f"{clean_text(row.get('item'))} {percent_label(row.get('count'), row.get('denominator'))}"
        for _, row in rows.iterrows()
    )


def portfolio_capacity(summary_row: pd.Series, market_row: pd.Series) -> dict[str, float]:
    current = numeric(first_existing_value(summary_row, ["current_child_segments"], market_row.get("Child Segment Count", 0)))
    estimated = numeric(first_existing_value(summary_row, ["estimated_total_segments"], current))
    coverage = numeric(first_existing_value(summary_row, ["coverage_percent"], market_row.get("Coverage", 0)))
    if estimated <= 0 and current > 0:
        estimated = current
    remaining = max(estimated - current, 0)
    return {
        "current": current,
        "estimated": estimated,
        "remaining": remaining,
        "coverage": coverage,
    }


def build_child_niche_rows(demand_name: str, queue_rows: pd.DataFrame, demand_segments: pd.DataFrame) -> pd.DataFrame:
    segment_columns = [
        "parent_demand",
        "segment_name",
        "keyword_count",
        "best_rank",
        "median_rank",
        "active_months",
        "trend",
        "segment_strength",
        "evidence_keywords",
    ]
    if not demand_segments.empty and {"parent_demand", "segment_name"}.issubset(demand_segments.columns):
        segment_rows = demand_segments[demand_segments["parent_demand"].astype(str) == demand_name]
        segment_rows = segment_rows[existing_columns(segment_rows, segment_columns)].rename(columns={"segment_name": "child_segment"})
    else:
        segment_rows = pd.DataFrame(columns=["child_segment"])

    if queue_rows.empty:
        children = segment_rows.copy()
    elif segment_rows.empty:
        children = queue_rows.copy()
    else:
        children = queue_rows.merge(segment_rows, on="child_segment", how="outer", suffixes=("", "_segment"))

    if children.empty:
        return children

    if "keyword_count" not in children.columns:
        children["keyword_count"] = 0
    if "opportunity_score" not in children.columns and "total_score" in children.columns:
        children["opportunity_score"] = children["total_score"]
    if "opportunity_score" not in children.columns:
        children["opportunity_score"] = 0

    keyword_counts = pd.to_numeric(children["keyword_count"], errors="coerce").fillna(0)
    opportunity_scores = pd.to_numeric(children["opportunity_score"], errors="coerce").fillna(0)
    keyword_total = numeric(keyword_counts.sum())
    score_total = numeric(opportunity_scores.sum())
    if keyword_total > 0:
        children["estimated_share"] = keyword_counts / keyword_total * 100
        children["share_basis"] = "keyword_count"
        children["share_denominator"] = keyword_total
    elif score_total > 0:
        children["estimated_share"] = opportunity_scores / score_total * 100
        children["share_basis"] = "opportunity_score"
        children["share_denominator"] = score_total
    else:
        children["estimated_share"] = 0
        children["share_basis"] = "unavailable"
        children["share_denominator"] = 0
    if "evidence_keywords" in children.columns:
        children["evidence_example_count"] = children["evidence_keywords"].apply(lambda value: len(split_pipe_values(value)))
        children["evidence_example_denominator"] = numeric(children["evidence_example_count"].sum())
    else:
        children["evidence_example_count"] = 0
        children["evidence_example_denominator"] = 0
    return sort_by_available(children, ["opportunity_score", "estimated_share"], [False, False])


def distribution_from_fit_and_evidence(
    fit: pd.DataFrame,
    child_segments: list[str],
    score_columns: dict[str, str],
    evidence_keywords: list[str],
    term_map: dict[str, list[str]],
) -> pd.DataFrame:
    if child_segments and not fit.empty and "child_segment" in fit.columns:
        subset = fit[fit["child_segment"].astype(str).isin(child_segments)].copy()
    else:
        subset = pd.DataFrame()

    evidence_denominator = len(evidence_keywords)
    evidence_counts = {
        label: term_count(evidence_keywords, term_map.get(label, []))
        for label in score_columns.values()
    }
    evidence_total = sum(evidence_counts.values())

    rows = []
    for column, label in score_columns.items():
        fit_score = 0.0
        if not subset.empty and column in subset.columns:
            fit_score = numeric(pd.to_numeric(subset[column], errors="coerce").mean())
        evidence_count = evidence_counts.get(label, 0)
        rows.append(
            {
                "item": label,
                "fit_score": fit_score,
                "evidence_count": evidence_count,
                "evidence_denominator": evidence_denominator,
            }
        )

    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame

    if evidence_total > 0:
        frame["estimated_share"] = frame["evidence_count"] / evidence_total * 100
        frame["share_basis"] = "evidence mentions"
    else:
        fit_total = numeric(frame["fit_score"].sum())
        frame["estimated_share"] = frame["fit_score"] / fit_total * 100 if fit_total > 0 else 0
        frame["share_basis"] = "fit scores"
    frame["reason"] = frame.apply(
        lambda row: (
            f"Fit score {format_score(row.get('fit_score'))}; "
            f"evidence {count_share_label(row.get('evidence_count'), row.get('evidence_denominator'))}; "
            f"share {format_score(row.get('estimated_share'))}% from {clean_text(row.get('share_basis'))}."
        ),
        axis=1,
    )
    return frame.sort_values(["estimated_share", "fit_score"], ascending=False)


def selected_product_label(row: pd.Series) -> str:
    return first_existing_value(row, ["recommended_product", "best_product", "primary_product", "product_recommendation"])


def selected_customization_label(row: pd.Series) -> str:
    return first_existing_value(row, ["recommended_customization", "best_customization", "primary_customization", "customization_recommendation"])


def score_for_label(row: pd.Series, score_columns: dict[str, str], label: str) -> float:
    for column, display in score_columns.items():
        if display == label and column in row.index:
            return numeric(row.get(column))
    return 0.0


def render_market_snapshot(market_row: pd.Series, summary_row: pd.Series) -> None:
    capacity = portfolio_capacity(summary_row, market_row)
    growth_score = numeric(market_row.get("Growth Score"))
    card_grid(
        [
            (
                "Market Size",
                first_existing_value(market_row, ["Market Size"], "Unknown"),
                f"Score {format_score(market_row.get('Market Size Score'))}",
            ),
            (
                "Growth",
                first_existing_value(market_row, ["Growth"], "Unknown"),
                f"Momentum score {format_score(growth_score)}" if growth_score else "Momentum metric unavailable",
            ),
            (
                "Competition",
                first_existing_value(market_row, ["Competition"], "Unknown"),
                f"Score {format_score(market_row.get('Competition Fit Score'))}",
            ),
            (
                "Seasonality",
                first_existing_value(market_row, ["Seasonality"], "Unknown"),
                f"Score {format_score(market_row.get('Seasonality Score'))}",
            ),
            (
                "Portfolio Stage",
                first_existing_value(market_row, ["Portfolio Stage"], "Unknown"),
                "Loaded from portfolio/market intelligence",
            ),
            (
                "Coverage",
                f"{capacity['coverage']:.1f}%",
                f"{format_int(capacity['current'])} researched | {format_int(capacity['estimated'])} estimated | {format_int(capacity['remaining'])} remaining",
            ),
            (
                "Expansion Potential",
                f"{numeric(market_row.get('Expansion Potential')):.1f}",
                "Loaded expansion score",
            ),
            (
                "Research Priority",
                first_existing_value(market_row, ["Investment"], "Monitor"),
                market_recommended_action(market_row),
            ),
        ],
        4,
    )


def metric_list_card(title: str, items: list[str]) -> None:
    if not items:
        return
    st.markdown(
        f"""
        <div class="mrd-card" style="min-height:190px;">
            <div class="mrd-card-label">{safe(title)}</div>
            {''.join(f'<div class="mrd-research-line">- {safe(item)}</div>' for item in items)}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_executive_insight(
    demand_name: str,
    market_row: pd.Series,
    summary_row: pd.Series,
    child_rows: pd.DataFrame,
    product_distribution: pd.DataFrame,
) -> None:
    capacity = portfolio_capacity(summary_row, market_row)
    top_child = child_rows.iloc[0] if not child_rows.empty else pd.Series(dtype=object)
    top_product = product_distribution.iloc[0] if not product_distribution.empty else pd.Series(dtype=object)
    strengths = [
        f"Market size {first_existing_value(market_row, ['Market Size'], 'Unknown')} with size score {format_score(market_row.get('Market Size Score'))}.",
        f"Expansion potential {format_score(market_row.get('Expansion Potential'))} with coverage {capacity['coverage']:.1f}%.",
    ]
    if not top_child.empty:
        strengths.append(
            f"Top child niche {clean_text(top_child.get('child_segment'))} has opportunity score {format_score(top_child.get('opportunity_score', top_child.get('total_score')))} and estimated share {format_score(top_child.get('estimated_share'))}%."
        )
    if numeric(market_row.get("Seasonality Score")):
        strengths.append(f"Seasonality score {format_score(market_row.get('Seasonality Score'))}.")

    risks = [
        f"Competition {first_existing_value(market_row, ['Competition'], 'Unknown')} with score {format_score(market_row.get('Competition Fit Score'))}."
    ]
    if not top_product.empty and numeric(top_product.get("estimated_share")) >= 50:
        risks.append(
            f"Product concentration: {clean_text(top_product.get('item'))} represents {format_score(top_product.get('estimated_share'))}% of product distribution."
        )
    if capacity["remaining"] <= 0 and capacity["estimated"] > 0:
        risks.append(f"No remaining capacity shown: {format_int(capacity['current'])} / {format_int(capacity['estimated'])} niches covered.")
    if numeric(market_row.get("Average Opportunity")) < 60:
        risks.append(f"Average opportunity score is {format_score(market_row.get('Average Opportunity'))}.")

    opportunity = [
        f"{demand_name} has {format_int(capacity['remaining'])} / {format_int(capacity['estimated'])} estimated child niches remaining.",
        f"Best child score {format_score(market_row.get('Best Child Score'))}; average opportunity {format_score(market_row.get('Average Opportunity'))}.",
    ]
    gap = [
        f"Current portfolio covers {format_int(capacity['current'])} / {format_int(capacity['estimated'])} child niches.",
        f"Remaining capacity is {format_int(capacity['remaining'])} niches; coverage is {capacity['coverage']:.1f}%.",
    ]

    columns = st.columns(4)
    for column, title, items in zip(columns, ["Opportunity", "Top Strengths", "Top Risks", "Current Gap"], [opportunity, strengths, risks, gap]):
        with column:
            metric_list_card(title, items)


def preparation_window(timeline: dict[str, str]) -> str:
    research_month = month_position(timeline.get("Research Month"), timeline.get("Peak Month"))
    peak_month = month_position(timeline.get("Peak Month"))
    if research_month is None or peak_month is None:
        return "Rolling / evergreen"
    if peak_month < research_month:
        peak_month += 12
    months = max(peak_month - research_month, 0)
    return f"{months} month preparation window"


def render_demand_timeline(timeline: dict[str, str]) -> None:
    labels = [
        ("Research", timeline.get("Research Month", "")),
        ("Listing", timeline.get("Listing / Upload", "")),
        ("Ads", timeline.get("Ads Month", "")),
        ("Peak Season", timeline.get("Peak Month", "")),
    ]
    st.markdown(
        f"""
        <div class="mrd-card" style="min-height:130px;">
            <div class="mrd-card-label">Preparation Window</div>
            <div class="mrd-card-value" style="font-size:1.35rem;">{safe(preparation_window(timeline))}</div>
            <div style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:0.75rem;margin-top:1rem;">
                {''.join(f'<div style="border:1px solid rgba(148,163,184,0.22);border-radius:10px;padding:0.8rem;background:#0b1220;"><div class="mrd-card-label">{safe(label)}</div><div class="mrd-research-title">{safe(value)}</div></div>' for label, value in labels)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_distribution_cards(rows: pd.DataFrame, title: str, item_label: str, limit: int = 6) -> None:
    st.subheader(title)
    if rows.empty:
        st.info(f"No {item_label.lower()} distribution data is available.")
        return
    top = rows.head(limit).reset_index(drop=True)
    for start in range(0, len(top), 3):
        columns = st.columns(3)
        for column, (_, row) in zip(columns, top.iloc[start : start + 3].iterrows()):
            with column:
                st.markdown(
                    f"""
                    <div class="mrd-card" style="min-height:205px;">
                        <div class="mrd-card-label">{safe(item_label)}</div>
                        <div class="mrd-card-value" style="font-size:1.35rem;">{safe(row.get("item"))}</div>
                        <div class="mrd-research-line"><b>Fit Score:</b> {format_score(row.get("fit_score"))}</div>
                        <div class="mrd-research-line"><b>Estimated Share:</b> {format_score(row.get("estimated_share"))}%</div>
                        <div class="mrd-research-line"><b>Evidence Count:</b> {safe(count_share_label(row.get("evidence_count"), row.get("evidence_denominator")))}</div>
                        <div class="mrd-research-line"><b>Reason:</b> {safe(row.get("reason"))}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


def render_market_distribution(child_rows: pd.DataFrame) -> None:
    st.subheader("Market Distribution")
    if child_rows.empty or "estimated_share" not in child_rows.columns:
        st.info("No child-niche market distribution data is available.")
        return
    chart_data = child_rows.head(10).copy()
    chart_data["estimated_share"] = pd.to_numeric(chart_data["estimated_share"], errors="coerce").fillna(0)
    chart = (
        alt.Chart(chart_data)
        .mark_bar(color="#38bdf8")
        .encode(
            x=alt.X("estimated_share:Q", title="Estimated demand share (%)"),
            y=alt.Y("child_segment:N", sort="-x", title=None),
            tooltip=[
                "child_segment",
                alt.Tooltip("estimated_share:Q", format=".1f"),
                alt.Tooltip("keyword_count:Q", format=".0f"),
                alt.Tooltip("opportunity_score:Q", format=".1f"),
            ],
        )
        .properties(height=360, title="Top 10 Child Niches by Estimated Share")
    )
    st.altair_chart(dark_chart(chart), use_container_width=True)


def render_whitespace_capacity(summary_row: pd.Series, market_row: pd.Series) -> None:
    capacity = portfolio_capacity(summary_row, market_row)
    card_grid(
        [
            ("Current", format_int(capacity["current"]), "Researched child niches"),
            ("Estimated", format_int(capacity["estimated"]), "Estimated total capacity"),
            ("Remaining", format_int(capacity["remaining"]), "Uncovered child niches"),
            ("Coverage", f"{capacity['coverage']:.1f}%", f"{format_int(capacity['current'])} / {format_int(capacity['estimated'])} covered"),
        ],
        4,
    )


def render_decision_recommendation(
    demand_name: str,
    market_row: pd.Series,
    summary_row: pd.Series,
    child_rows: pd.DataFrame,
    product_distribution: pd.DataFrame,
    customization_distribution: pd.DataFrame,
) -> None:
    capacity = portfolio_capacity(summary_row, market_row)
    top_child = child_rows.iloc[0] if not child_rows.empty else pd.Series(dtype=object)
    top_product = product_distribution.iloc[0] if not product_distribution.empty else pd.Series(dtype=object)
    top_customization = customization_distribution.iloc[0] if not customization_distribution.empty else pd.Series(dtype=object)
    top_score = numeric(top_child.get("opportunity_score", top_child.get("total_score")))
    expansion = numeric(market_row.get("Expansion Potential"))
    average_opportunity = numeric(market_row.get("Average Opportunity"))
    if top_score >= 80 or (expansion >= 70 and capacity["remaining"] > 0):
        decision = "INVEST"
    elif top_score >= 70 or average_opportunity >= 65:
        decision = "VALIDATE"
    else:
        decision = "MONITOR"
    confidence = confidence_from_score(top_score or average_opportunity, market_row.get("Investment"))
    why = (
        f"Expansion {format_score(expansion)}, coverage {capacity['coverage']:.1f}% "
        f"({format_int(capacity['current'])} / {format_int(capacity['estimated'])}), "
        f"top child score {format_score(top_score)}."
    )
    payoff = (
        f"Remaining capacity {format_int(capacity['remaining'])} / {format_int(capacity['estimated'])} niches; "
        f"best child score {format_score(top_score)}; average opportunity {format_score(average_opportunity)}."
    )
    card_grid(
        [
            ("Decision", decision, why),
            ("Confidence", confidence, f"Based on top score {format_score(top_score)} and priority {clean_text(market_row.get('Investment'))}"),
            ("Research First", clean_text(top_child.get("child_segment")), f"Estimated share {format_score(top_child.get('estimated_share'))}%"),
            ("Product", clean_text(top_product.get("item")), f"Fit {format_score(top_product.get('fit_score'))}; share {format_score(top_product.get('estimated_share'))}%"),
            ("Customization", clean_text(top_customization.get("item")), f"Fit {format_score(top_customization.get('fit_score'))}; share {format_score(top_customization.get('estimated_share'))}%"),
            ("Expected Payoff", demand_name, payoff),
        ],
        3,
    )


def render_grouped_child_evidence(child_rows: pd.DataFrame, limit: int = 10) -> None:
    if child_rows.empty:
        st.info("No child evidence is available.")
        return
    rows = child_rows.head(limit).reset_index(drop=True)
    for _, row in rows.iterrows():
        child = clean_text(row.get("child_segment"))
        keywords = split_pipe_values(row.get("evidence_keywords"))
        with st.expander(f"{child} evidence", expanded=False):
            st.markdown("#### Evidence Summary")
            card_grid(
                [
                    (
                        "Evidence Count",
                        count_share_label(row.get("evidence_example_count", len(keywords)), row.get("evidence_example_denominator", len(keywords)), "evidence keywords"),
                        f"Share {format_score(row.get('estimated_share'))}%",
                    ),
                    ("Product Fit", selected_product_label(row), f"Score {format_score(score_for_label(row, PRODUCT_SCORE_COLUMNS, selected_product_label(row)))}"),
                    ("Customization Fit", selected_customization_label(row), f"Score {format_score(score_for_label(row, CUSTOMIZATION_SCORE_COLUMNS, selected_customization_label(row)))}"),
                    ("Opportunity", f"{format_score(row.get('opportunity_score', row.get('total_score')))}", "Total score from scorecard"),
                ],
                4,
            )
            if keywords:
                st.markdown("#### Keywords")
                display_table(pd.DataFrame({"keyword": keywords}), ["keyword"], height=220)
            st.markdown("#### Opportunity Components")
            score_breakdown_cards(row)
            st.markdown("#### Supporting Row")
            display_table(pd.DataFrame([row]), height=220)


def top_child_niche_cards(rows: pd.DataFrame, limit: int = 10, show_detail: bool = True) -> None:
    if rows.empty:
        st.info("No child-niche research candidates are available for this demand.")
        return
    top_rows = sort_by_available(rows, ["opportunity_score", "total_score"], [False, False]).head(limit).reset_index(drop=True)
    for start in range(0, len(top_rows), 2):
        columns = st.columns(2)
        for column, (_, row) in zip(columns, top_rows.iloc[start : start + 2].iterrows()):
            priority = first_existing_value(row, ["priority", "recommended_priority"], "Watchlist")
            score = row.get("opportunity_score", row.get("total_score"))
            product = selected_product_label(row)
            customization = selected_customization_label(row)
            product_score = score_for_label(row, PRODUCT_SCORE_COLUMNS, product)
            customization_score = score_for_label(row, CUSTOMIZATION_SCORE_COLUMNS, customization)
            share_source = clean_text(row.get("share_basis"))
            reason = (
                f"Estimated share {format_score(row.get('estimated_share'))}% from {share_source}; "
                f"opportunity score {format_score(score)}; "
                f"{product} fit {format_score(product_score)}; "
                f"{customization} fit {format_score(customization_score)}."
            )
            action = "Research first" if numeric(score) >= 80 else "Validate with manual market review" if numeric(score) >= 70 else "Monitor until stronger evidence"
            with column:
                action_card(
                    row.get("child_segment"),
                    priority,
                    score,
                    [
                        ("Estimated Share", f"{format_score(row.get('estimated_share'))}%"),
                        ("Product", f"{product} (fit {format_score(product_score)})"),
                        ("Customization", f"{customization} (fit {format_score(customization_score)})"),
                        ("Reason", reason),
                        ("Action", f"{action}; next step: {first_existing_value(row, ['next_action', 'recommended_next_step'], 'review evidence')}"),
                    ],
                )
                if show_detail:
                    child_detail_expander(row, f"child_{start}")


def render_direction_summary(rows: pd.DataFrame, title: str, item_label: str, limit: int = 6) -> None:
    st.subheader(title)
    if rows.empty:
        st.info(f"No {item_label.lower()} direction is available.")
        return
    top = rows.head(limit).reset_index(drop=True)
    best = top.iloc[0]
    insight_box(
        f"Best {item_label}",
        f"{clean_text(best.get('item'))} is the strongest current direction with fit score {format_score(best.get('fit_score'))}. Suggested test: launch the highest-priority child niche with this {item_label.lower()} first, then expand only if evidence validates.",
    )
    render_ranked_recommendation_cards(top, item_label, limit)


def demand_research_recommendation(
    demand_name: str,
    row: pd.Series,
    queue_rows: pd.DataFrame,
    product_scores: pd.DataFrame,
    customization_scores: pd.DataFrame,
) -> str:
    top_child = queue_rows.iloc[0] if not queue_rows.empty else pd.Series(dtype=object)
    best_product = clean_text(product_scores.iloc[0].get("item")) if not product_scores.empty else "best-fit product"
    best_custom = clean_text(customization_scores.iloc[0].get("item")) if not customization_scores.empty else "best-fit customization"
    timeline = inferred_timeline(demand_name, row.get("Seasonality"))
    confidence = confidence_from_score(top_child.get("opportunity_score", row.get("Average Opportunity")), top_child.get("priority", ""))
    avoid = "Do not research generic parent-demand products first."
    if clean_text(row.get("Competition")) == "High":
        avoid = "Do not research broad, generic listings where competition is already high."
    first = clean_text(top_child.get("child_segment")) or demand_name
    return (
        f"{avoid} Research {first} first. Test {best_product} with {best_custom}. "
        f"Start in {timeline['Research Month']} and prepare upload by {timeline['Listing / Upload']}. "
        f"Confidence level: {confidence}."
    )


def demand_explorer() -> None:
    page_header(
        "Demand Explorer",
        "Executive market home for deciding which demands to inspect and research first.",
    )
    queue = decision_data()
    scorecard = load_csv("opportunity_scorecard")
    product_fit = load_csv("product_fit_matrix")
    customization_fit = load_csv("customization_fit_matrix")
    demand_segments = load_csv("demand_segments")
    composite_demands = load_csv("composite_demands")
    markets = market_landscape_data(load_csv("portfolio_master"), load_csv("market_intelligence"), scorecard, customization_fit)
    ranked_markets = prepare_market_rankings(markets)
    options = parent_market_options(load_csv("portfolio_master"), load_csv("market_intelligence"), queue)
    if not options:
        st.info("No demand data is available.")
        return

    ranked_markets = sort_by_available(
        ranked_markets,
        ["Market Rank Score", "Expansion Potential", "Average Opportunity"],
        [False, False, False],
    )

    st.subheader("Executive Market Overview")
    executive_market_overview(ranked_markets, queue)

    section_break()
    st.subheader("Top Markets to Invest")
    market_investment_cards(ranked_markets, 15)

    section_break()
    st.subheader("Market Size Ranking")
    market_size_ranking_chart(ranked_markets)

    section_break()
    expansion_candidates = ranked_markets[
        (pd.to_numeric(ranked_markets["Expansion Potential"], errors="coerce").fillna(0) >= 65)
        & (pd.to_numeric(ranked_markets["Coverage"], errors="coerce").fillna(0) <= 65)
        & (pd.to_numeric(ranked_markets["Child Segment Count"], errors="coerce").fillna(0) >= 3)
    ].copy()
    if expansion_candidates.empty:
        expansion_candidates = ranked_markets.copy()
    expansion_candidates = sort_by_available(
        expansion_candidates,
        ["Expansion Opportunity Score", "Expansion Potential"],
        [False, False],
    )
    compact_market_opportunity_cards(expansion_candidates, "Biggest Expansion Opportunities", "expansion", 6)

    section_break()
    weak_investment = ranked_markets.get("Investment", pd.Series("", index=ranked_markets.index)).astype(str).isin(
        ["Monitor", "Avoid", "Exit", "Archive", "Watchlist"]
    )
    risk_candidates = ranked_markets[
        weak_investment
        | (pd.to_numeric(ranked_markets["Market Rank Score"], errors="coerce").fillna(0) < 60)
        | (pd.to_numeric(ranked_markets["Average Opportunity"], errors="coerce").fillna(0) < 60)
    ].copy()
    if risk_candidates.empty:
        risk_candidates = ranked_markets.tail(6).copy()
    risk_candidates = sort_by_available(risk_candidates, ["Risk Score", "Market Rank Score"], [False, True])
    compact_market_opportunity_cards(risk_candidates, "Biggest Risks / Avoid", "risk", 6)

    section_break()
    weekly_research_focus(queue, 10)

    with st.expander("Market ranking details", expanded=False):
        display_table(
            ranked_markets,
            [
                "Parent Market",
                "Market Size",
                "Growth",
                "Competition",
                "Coverage",
                "Expansion Potential",
                "Average Opportunity",
                "Child Segment Count",
                "Investment",
                "Market Rank Score",
                "Recommendation",
            ],
            height=360,
        )

    section_break()
    st.subheader("Inspect a Demand")
    ranked_options = ranked_markets["Parent Market"].dropna().astype(str).tolist()
    remaining_options = [option for option in options if option not in ranked_options]
    selected = st.selectbox(
        "Select demand after reviewing the market ranking",
        ranked_options + remaining_options,
        key="demand_explorer_selected",
    )
    market_row = demand_market_row(selected, markets)
    portfolio_summary = load_csv("portfolio_summary")
    summary_row = first_matching_row(portfolio_summary, "parent_demand", selected)
    queue_rows = parent_queue_rows(queue, selected)
    child_rows = build_child_niche_rows(selected, queue_rows, demand_segments)
    child_segments = child_rows["child_segment"].dropna().astype(str).unique().tolist() if "child_segment" in child_rows.columns else []
    evidence_keywords = demand_evidence_keywords(selected, demand_segments, composite_demands)
    product_distribution = distribution_from_fit_and_evidence(
        product_fit,
        child_segments,
        PRODUCT_SCORE_COLUMNS,
        evidence_keywords,
        PRODUCT_TERMS,
    )
    customization_distribution = distribution_from_fit_and_evidence(
        customization_fit,
        child_segments,
        CUSTOMIZATION_SCORE_COLUMNS,
        evidence_keywords,
        CUSTOMIZATION_TERMS,
    )

    section_break()
    st.subheader("A. Market Snapshot")
    render_market_snapshot(market_row, summary_row)

    section_break()
    st.subheader("B. Executive Insight")
    render_executive_insight(selected, market_row, summary_row, child_rows, product_distribution)

    section_break()
    st.subheader("C. Demand Timeline")
    timeline = inferred_timeline(selected, market_row.get("Seasonality"))
    render_demand_timeline(timeline)

    section_break()
    st.subheader("D. Top Child Niches")
    top_child_niche_cards(child_rows, 10, show_detail=True)

    section_break()
    render_market_distribution(child_rows)

    section_break()
    render_distribution_cards(product_distribution, "Product Distribution", "Product", 6)

    section_break()
    render_distribution_cards(customization_distribution, "Customization Distribution", "Customization", 7)

    section_break()
    st.subheader("Evidence Summary")
    demand_evidence_cards(selected, demand_segments, composite_demands)

    section_break()
    st.subheader("Whitespace")
    render_whitespace_capacity(summary_row, market_row)

    section_break()
    st.subheader("Decision Recommendation")
    render_decision_recommendation(selected, market_row, summary_row, child_rows, product_distribution, customization_distribution)

    section_break()
    st.subheader("Expandable Evidence")
    render_grouped_child_evidence(child_rows, 10)


def research_center() -> None:
    page_header(
        "Research Center",
        "This week's highest-value research actions with reasons and next steps.",
    )
    data = decision_data()
    if data.empty:
        st.info("Research candidate data is missing or empty.")
        return

    filters = st.columns(4)
    with filters[0]:
        data = filter_multiselect(data, "parent_demand", "Parent Demand", "rc_parent")
    with filters[1]:
        data = filter_multiselect(data, "priority", "Priority", "rc_priority")
    with filters[2]:
        data = filter_multiselect(data, "recommended_product", "Product", "rc_product")
    with filters[3]:
        data = filter_multiselect(data, "recommended_customization", "Customization", "rc_customization")

    metric_cards(
        [
            ("Visible Actions", len(data), "Filtered research candidates"),
            ("P1", int((data["priority"] == "P1").sum()) if "priority" in data.columns else 0, "Immediate work"),
            ("Avg Score", f"{numeric(data['opportunity_score'].mean() if 'opportunity_score' in data.columns else 0):.1f}", "Opportunity quality"),
            ("Parents", data["parent_demand"].nunique() if "parent_demand" in data.columns else 0, "Markets represented"),
        ]
    )

    section_break()
    st.subheader("A. Top 20 Research Actions")
    top_rows = sort_by_available(data, ["priority", "opportunity_score"], [True, False]).head(20).reset_index(drop=True)
    for start in range(0, len(top_rows), 2):
        columns = st.columns(2)
        for column, (_, row) in zip(columns, top_rows.iloc[start : start + 2].iterrows()):
            with column:
                action_card(
                    row.get("child_segment"),
                    first_existing_value(row, ["priority", "recommended_priority"], "Watchlist"),
                    row.get("opportunity_score", row.get("total_score")),
                    [
                        ("Parent demand", row.get("parent_demand")),
                        ("Best product", first_existing_value(row, ["recommended_product", "best_product", "primary_product"])),
                        (
                            "Best customization",
                            first_existing_value(row, ["recommended_customization", "best_customization", "primary_customization"]),
                        ),
                        ("Why now", first_existing_value(row, ["why_now", "reason", "explanation"], "Ranking and fit signals justify review.")),
                        ("Next action", first_existing_value(row, ["next_action", "recommended_next_step"], "Validate market evidence.")),
                    ],
                )

    section_break()
    st.subheader("C. Expandable Details")
    if "child_segment" in data.columns:
        selected = st.selectbox("Inspect research action", data["child_segment"].astype(str).drop_duplicates().tolist(), key="rc_inspect")
        detail = data[data["child_segment"].astype(str) == selected].iloc[0]
        with st.expander("Analyst reasoning", expanded=True):
            for label, column in [
                ("Strengths", "strengths"),
                ("Weaknesses", "weaknesses"),
                ("Risks", "risks"),
                ("Opportunities", "opportunities"),
                ("Evidence", "explanation"),
            ]:
                st.markdown(f"#### {label}")
                st.write(clean_text(detail.get(column)) or "No detail available.")
    with st.expander("Filtered research rows", expanded=False):
        display_table(data, height=360)


def roadmap_cards(roadmap: pd.DataFrame, limit: int = 24) -> None:
    if roadmap.empty:
        st.info("No roadmap rows are available.")
        return
    rows = sort_by_available(roadmap, ["priority", "week"], [True, True]).head(limit).reset_index(drop=True)
    for start in range(0, len(rows), 3):
        columns = st.columns(3)
        for column, (_, row) in zip(columns, rows.iloc[start : start + 3].iterrows()):
            with column:
                action_card(
                    f"Week {clean_text(row.get('week'))}",
                    first_existing_value(row, ["priority"], "Plan"),
                    "",
                    [
                        ("Parent demand", row.get("parent_demand")),
                        ("Child segment", row.get("child_segment")),
                        ("Product", row.get("product")),
                        ("Customization", row.get("customization")),
                        ("Reason", row.get("reason")),
                    ],
                    "mrd-badge-p2",
                )


def portfolio_explorer() -> None:
    page_header(
        "Portfolio Explorer",
        "Portfolio health, investment direction, and weekly roadmap.",
    )
    master = load_csv("portfolio_master")
    summary = load_csv("portfolio_summary")
    roadmap = load_csv("portfolio_roadmap")
    if master.empty and summary.empty and roadmap.empty:
        st.info("Portfolio data is missing or empty.")
        return

    st.subheader("A. Portfolio Health")
    investment = master.get("investment_recommendation", pd.Series(dtype=str)).astype(str)
    metric_cards(
        [
            ("Total Portfolios", len(master), "Parent markets"),
            ("Average Coverage", f"{numeric(master['coverage_score'].mean() if 'coverage_score' in master.columns else 0):.1f}%", "Portfolio coverage"),
            ("Invest Aggressively", int((investment == "Invest Aggressively").sum()), "Highest investment tier"),
            ("Expand", int((investment == "Expand").sum()), "Expansion candidates"),
            ("Monitor", int((investment == "Monitor").sum()), "Watchlist portfolios"),
        ]
    )

    section_break()
    st.subheader("B. Parent Portfolio")
    options = clean_options(master["parent_demand"]) if not master.empty and "parent_demand" in master.columns else []
    if options:
        selected = st.selectbox("Select parent portfolio", options, key="portfolio_explorer_selected")
        master_row = first_matching_row(master, "parent_demand", selected)
        summary_row = first_matching_row(summary, "parent_demand", selected)
        card_grid(
            [
                ("Coverage", f"{numeric(first_existing_value(summary_row, ['coverage_percent'], master_row.get('coverage_score'))):.1f}%", "Current coverage"),
                ("Current Segments", first_existing_value(summary_row, ["current_child_segments"], master_row.get("child_segment_count", 0)), "Built child niches"),
                ("Estimated Total", first_existing_value(summary_row, ["estimated_total_segments"], ""), "Potential segment count"),
                ("Portfolio Stage", first_existing_value(master_row, ["portfolio_stage"], "Unknown"), "Lifecycle"),
                ("Investment", first_existing_value(master_row, ["investment_recommendation"], "Monitor"), "Action tier"),
                ("Next Recommendation", first_existing_value(summary_row, ["next_recommendation"], "Review next import"), "Next portfolio move"),
            ],
            3,
        )

    section_break()
    st.subheader("C. Roadmap")
    roadmap_cards(roadmap, 24)
    with st.expander("Roadmap details", expanded=False):
        display_table(roadmap, ["week", "parent_demand", "child_segment", "product", "customization", "priority", "reason"], height=360)


def score_breakdown_cards(row: pd.Series) -> None:
    card_grid(
        [
            ("Market Size", f"{numeric(row.get('market_size_score')):.1f}", "Demand scale"),
            ("Growth", f"{numeric(row.get('growth_score')):.1f}", "Momentum"),
            ("Competition", f"{numeric(row.get('competition_score')):.1f}", "Lower friction is better"),
            ("Expansion", f"{numeric(row.get('expansion_score')):.1f}", "Parent-market room"),
            ("Seasonality", f"{numeric(row.get('seasonality_score')):.1f}", "Timing quality"),
            ("Product Fit", f"{numeric(row.get('product_fit_score')):.1f}", "Product alignment"),
        ],
        3,
    )


def decision_center() -> None:
    page_header(
        "Decision Center",
        "Why an opportunity is recommended and what decision should be made.",
    )
    scorecard = load_csv("opportunity_scorecard")
    reasoning = load_csv("research_reasoning")
    if scorecard.empty or "child_segment" not in scorecard.columns:
        st.info("Opportunity scorecard data is missing or empty.")
        return
    data = scorecard.copy()
    if not reasoning.empty and "child_segment" in reasoning.columns:
        data = data.merge(reasoning, on="child_segment", how="left", suffixes=("", "_reasoning"))
    data = sort_by_available(data, ["total_score", "child_segment"], [False, True])
    selected = st.selectbox("Select child segment", data["child_segment"].astype(str).tolist(), key="decision_center_segment")
    row = data[data["child_segment"].astype(str) == selected].iloc[0]
    decision = score_to_decision(row.get("total_score"))
    confidence = confidence_from_score(row.get("total_score"), row.get("recommended_priority"))

    st.subheader("A. Decision Summary")
    card_grid(
        [
            ("Total Score", f"{numeric(row.get('total_score')):.1f}", "Weighted opportunity score"),
            ("Priority", first_existing_value(row, ["recommended_priority"], "Watchlist"), "Scorecard priority"),
            ("Final Recommendation", decision, "Decision output"),
            ("Confidence", confidence, "Based on score and priority"),
        ],
        4,
    )

    section_break()
    st.subheader("B. Score Breakdown")
    score_breakdown_cards(row)

    section_break()
    st.subheader("C. Analyst Reasoning")
    for start, items in enumerate(
        [
            [("Strengths", "strengths"), ("Weaknesses", "weaknesses"), ("Risks", "risks")],
            [("Opportunities", "opportunities"), ("Why Now", "why_now"), ("Next Step", "recommended_next_step")],
        ]
    ):
        columns = st.columns(3)
        for column, (label, field) in zip(columns, items):
            with column:
                insight_box(label, clean_text(row.get(field)) or "No analyst note available.")

    section_break()
    st.subheader("D. Decision Output")
    insight_box(
        decision,
        f"{clean_text(row.get('child_segment'))} should be classified as '{decision}'. {clean_text(row.get('explanation')) or 'Use score breakdown and analyst reasoning to guide the next action.'}",
    )
    with st.expander("Scorecard detail", expanded=False):
        display_table(data[data["child_segment"].astype(str) == selected], height=260)


def fit_level(score: object) -> str:
    value = numeric(score)
    if value >= 85:
        return "Strong"
    if value >= 70:
        return "Good"
    if value >= 55:
        return "Test"
    return "Weak"


def segment_fit_scores(row: pd.Series, columns: dict[str, str]) -> pd.DataFrame:
    rows = []
    for column, label in columns.items():
        if column in row.index:
            score = numeric(row.get(column))
            rows.append({"item": label, "score": score, "fit_level": fit_level(score)})
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    return frame.sort_values("score", ascending=False)


def render_fit_score_cards(rows: pd.DataFrame, reason: str) -> None:
    if rows.empty:
        st.info("No fit scores are available.")
        return
    for start in range(0, len(rows), 3):
        columns = st.columns(3)
        for column, (_, row) in zip(columns, rows.iloc[start : start + 3].iterrows()):
            level = clean_text(row.get("fit_level"))
            with column:
                st.markdown(
                    f"""
                    <div class="mrd-card" style="min-height:180px;">
                        <span class="mrd-badge {confidence_badge_class('High' if level == 'Strong' else 'Medium' if level == 'Good' else 'Low')}">{safe(level)}</span>
                        <div class="mrd-card-value" style="font-size:1.35rem;margin-top:0.75rem;">{safe(row.get("item"))}</div>
                        <div class="mrd-card-note">Score {format_score(row.get("score"))}</div>
                        <div class="mrd-research-line"><b>Reason:</b> {safe(reason)}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


def product_intelligence() -> None:
    page_header(
        "Product Intelligence",
        "Translate a child niche into product and customization tests.",
    )
    product_fit = load_csv("product_fit_matrix")
    customization_fit = load_csv("customization_fit_matrix")
    if product_fit.empty and customization_fit.empty:
        st.info("Product and customization fit data is missing or empty.")
        return
    segments = sorted(
        set(clean_options(product_fit["child_segment"]) if "child_segment" in product_fit.columns else [])
        | set(clean_options(customization_fit["child_segment"]) if "child_segment" in customization_fit.columns else [])
    )
    if not segments:
        st.info("No child segments are available for product intelligence.")
        return
    selected = st.selectbox("Select child segment", segments, key="product_intelligence_segment")
    product_row = first_matching_row(product_fit, "child_segment", selected)
    custom_row = first_matching_row(customization_fit, "child_segment", selected)
    product_rows = segment_fit_scores(product_row, PRODUCT_SCORE_COLUMNS)
    custom_rows = segment_fit_scores(custom_row, CUSTOMIZATION_SCORE_COLUMNS)

    st.subheader("A. Product Ranking")
    render_fit_score_cards(product_rows, clean_text(product_row.get("explanation")) or "Fit score from product matrix.")

    section_break()
    st.subheader("B. Customization Ranking")
    render_fit_score_cards(custom_rows, clean_text(custom_row.get("explanation")) or "Fit score from customization matrix.")

    section_break()
    st.subheader("C. Recommended Test Package")
    product_1 = clean_text(product_rows.iloc[0].get("item")) if not product_rows.empty else ""
    product_2 = clean_text(product_rows.iloc[1].get("item")) if len(product_rows) > 1 else ""
    custom_1 = clean_text(custom_rows.iloc[0].get("item")) if not custom_rows.empty else ""
    custom_2 = clean_text(custom_rows.iloc[1].get("item")) if len(custom_rows) > 1 else ""
    card_grid(
        [
            ("Product 1", product_1, "Primary test"),
            ("Product 2", product_2, "Backup test"),
            ("Custom 1", custom_1, "Primary personalization"),
            ("Custom 2", custom_2, "Backup personalization"),
        ],
        4,
    )
    insight_box("Suggested First Test", f"Start with {product_1 or 'the strongest product'} using {custom_1 or 'the strongest customization'} for {selected}. Add {product_2 or 'a second product'} only after the first test validates.")
    with st.expander("Fit details", expanded=False):
        display_table(product_fit[product_fit["child_segment"].astype(str) == selected] if "child_segment" in product_fit.columns else pd.DataFrame(), height=220)
        display_table(customization_fit[customization_fit["child_segment"].astype(str) == selected] if "child_segment" in customization_fit.columns else pd.DataFrame(), height=220)


def evidence_records_for_source(source: str) -> tuple[pd.DataFrame, pd.DataFrame, str, str, list[str]]:
    if source == "Demand":
        return (
            merge_summary_evidence(load_csv("composite_demands"), load_csv("opportunity_master"), "demand_id"),
            load_csv("demand_evidence_light"),
            "demand_id",
            "demand_name",
            ["demand_id", "demand_name"],
        )
    if source == "Segment":
        return (load_csv("demand_segments"), load_csv("segment_evidence_light"), "segment_id", "segment_name", ["segment_id", "segment_name"])
    if source == "Market Node":
        return (load_csv("market_nodes"), load_csv("market_node_evidence_light"), "market_node_id", "demand", ["market_node_id", "demand"])
    return (load_csv("opportunity_master"), load_csv("demand_evidence_light"), "demand_id", "demand_name", ["opportunity_id", "demand_name"])


def evidence_keyword_rows(record: pd.Series, evidence: pd.DataFrame, id_column: str, record_id: str) -> pd.DataFrame:
    rows = pd.DataFrame()
    if not evidence.empty and id_column in evidence.columns:
        rows = evidence[evidence[id_column].astype(str) == str(record_id)].copy()
        if not rows.empty:
            rows = sort_by_available(rows, ["search_frequency_rank"], [True]).head(200)
            keyword_column = "normalized_keyword" if "normalized_keyword" in rows.columns else "raw_keyword"
            rows["keyword"] = rows.get(keyword_column, "")
            return rows
    summary = summarized_evidence_frame(record)
    if not summary.empty:
        summary["normalized_keyword"] = summary["keyword"]
        return summary
    return pd.DataFrame(columns=["keyword"])


def keyword_category_counts(keywords: list[str], terms: list[str]) -> str:
    found: dict[str, int] = {}
    for keyword in keywords:
        lower = keyword.lower()
        for term in terms:
            if term in lower:
                found[term] = found.get(term, 0) + 1
    if not found:
        return "No clear signal"
    return " | ".join(f"{term}: {count}" for term, count in sorted(found.items(), key=lambda item: item[1], reverse=True)[:5])


def evidence_confidence(keyword_count: int, best_rank: object = 0) -> str:
    rank = numeric(best_rank, 999999)
    if keyword_count >= 50 or (keyword_count >= 15 and rank <= 1000):
        return "Strong"
    if keyword_count >= 10 or rank <= 5000:
        return "Medium"
    return "Weak"


def market_evidence() -> None:
    page_header(
        "Market Evidence",
        "Summarized keyword evidence with details kept expandable.",
    )
    source = st.radio("Evidence Source", ["Demand", "Segment", "Opportunity", "Market Node"], horizontal=True)
    records, evidence, id_column, label_column, id_columns = evidence_records_for_source(source)
    if records.empty:
        st.info("No evidence records are available for this source.")
        return
    selected = select_record_with_keys(records, [label_column], id_columns, "evidence_summary_source")
    if selected is None:
        st.info("No matching evidence record is available.")
        return

    record_id = clean_text(selected.get(id_column, selected.get(label_column, "")))
    rows = evidence_keyword_rows(selected, evidence, id_column, record_id)
    keyword_values = rows["keyword"].dropna().astype(str).tolist() if "keyword" in rows.columns else []
    if not keyword_values and "normalized_keyword" in rows.columns:
        keyword_values = rows["normalized_keyword"].dropna().astype(str).tolist()

    st.subheader("A. Evidence Summary")
    intent_terms = ["gift", "personalized", "custom", "memorial", "appreciation", "christmas", "birthday", "wedding", "anniversary", "decor", "apparel"]
    product_terms = ["blanket", "mug", "tumbler", "shirt", "ornament", "canvas", "doormat", "poster", "sign", "pillow", "cup", "frame", "hoodie"]
    recipient_terms = ["mom", "dad", "teacher", "grandma", "grandpa", "wife", "husband", "dog", "cat", "nurse", "friend", "boy", "girl"]
    occasion_terms = ["christmas", "birthday", "anniversary", "wedding", "retirement", "memorial", "graduation", "thanksgiving", "halloween", "easter", "valentine", "mother", "father"]
    theme_terms = ["funny", "vintage", "retro", "floral", "watercolor", "boho", "faith", "patriotic", "minimalist", "country"]
    confidence = evidence_confidence(len(keyword_values), selected.get("best_rank"))
    card_grid(
        [
            ("Top Keyword Themes", keyword_category_counts(keyword_values, theme_terms), "Theme language"),
            ("Top Intent", keyword_category_counts(keyword_values, intent_terms), "Intent language"),
            ("Top Product Words", keyword_category_counts(keyword_values, product_terms), "Solution clues"),
            ("Top Recipient Words", keyword_category_counts(keyword_values, recipient_terms), "Audience clues"),
            ("Top Occasion Words", keyword_category_counts(keyword_values, occasion_terms), "Timing clues"),
            ("Evidence Confidence", confidence, f"{len(keyword_values)} keywords summarized"),
        ],
        3,
    )

    section_break()
    st.subheader("C. Evidence Confidence")
    insight_box(
        confidence,
        f"Evidence is {confidence.lower()} for {clean_text(selected.get(label_column))}. Use this to decide whether to create now, validate with manual Amazon review, or monitor until stronger evidence appears.",
    )

    with st.expander("B. Keyword Evidence", expanded=False):
        if rows.empty:
            st.info("No keyword evidence is available.")
        else:
            display_table(rows, ["raw_keyword", "normalized_keyword", "keyword", "month", "search_frequency_rank"], height=360)


def render_sidebar() -> str:
    st.sidebar.title("MRnD")
    st.sidebar.caption("Demand Decision Dashboard")
    page = st.sidebar.radio(
        "Navigation",
        [
            "Demand Explorer",
            "Research Center",
            "Portfolio Explorer",
            "Decision Center",
            "Product Intelligence",
            "Market Evidence",
        ],
    )

    missing = missing_core_files()
    if missing:
        with st.sidebar.expander("Missing Core CSV Files", expanded=False):
            for path in missing:
                st.caption(str(path.relative_to(PROJECT_ROOT)))

    with st.sidebar.expander("Loaded Data Files", expanded=False):
        st.dataframe(loaded_data_files_frame(), use_container_width=True, hide_index=True, height=360)

    st.sidebar.markdown("---")
    st.sidebar.caption("Reads compact CSV outputs only. No DuckDB connection.")
    return page


def main() -> None:
    page = render_sidebar()
    if page == "Demand Explorer":
        demand_explorer()
    elif page == "Research Center":
        research_center()
    elif page == "Portfolio Explorer":
        portfolio_explorer()
    elif page == "Decision Center":
        decision_center()
    elif page == "Product Intelligence":
        product_intelligence()
    elif page == "Market Evidence":
        market_evidence()


if __name__ == "__main__":
    main()
