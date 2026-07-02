"""MRnD Executive Intelligence Dashboard V2.

This app is intentionally separate from app.py. It reads compact CSV exports
only and does not connect to DuckDB or modify source data.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "data" / "output"

DATA_FILES = {
    "market_intelligence": OUTPUT / "intelligence" / "market_intelligence.csv",
    "demand_intelligence": OUTPUT / "intelligence" / "demand_intelligence.csv",
    "market_scorecard": OUTPUT / "decision" / "market_scorecard.csv",
    "research_candidates": OUTPUT / "decision" / "research_candidates.csv",
    "market_calendar": OUTPUT / "decision" / "market_calendar.csv",
    "opportunity_scorecard": OUTPUT / "scoring" / "opportunity_scorecard.csv",
    "product_fit_matrix": OUTPUT / "scoring" / "product_fit_matrix.csv",
    "customization_fit_matrix": OUTPUT / "scoring" / "customization_fit_matrix.csv",
    "research_reasoning": OUTPUT / "scoring" / "research_reasoning.csv",
    "portfolio_master": OUTPUT / "portfolio" / "portfolio_master.csv",
    "portfolio_summary": OUTPUT / "portfolio" / "portfolio_summary.csv",
    "portfolio_roadmap": OUTPUT / "portfolio" / "portfolio_roadmap.csv",
    "portfolio_tree": OUTPUT / "portfolio" / "portfolio_tree.csv",
    "whitespace_analysis": OUTPUT / "portfolio" / "whitespace_analysis.csv",
    "opportunity_master": OUTPUT / "opportunity" / "opportunity_master.csv",
    "demand_segments": OUTPUT / "demand_segments" / "demand_segments.csv",
    "composite_demands": OUTPUT / "composite_demands" / "composite_demands.csv",
    "market_nodes": OUTPUT / "market_nodes" / "market_nodes.csv",
    "demand_evidence_light": OUTPUT / "evidence_light" / "demand_evidence_light.csv",
    "segment_evidence_light": OUTPUT / "evidence_light" / "segment_evidence_light.csv",
    "market_node_evidence_light": OUTPUT / "evidence_light" / "market_node_evidence_light.csv",
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

RANK_COLUMNS = {
    "best_rank",
    "p10_rank",
    "p25_rank",
    "median_rank",
    "average_rank",
    "search_frequency_rank",
}

SCORE_COLUMNS = {
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
    "coverage_percent",
    "expansion_potential",
    "average_opportunity_score",
    "best_child_score",
    "average_score",
    "confidence",
    "expected_value",
}


st.set_page_config(
    page_title="MRnD Executive Intelligence V2",
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
        max-width: 1500px;
        padding-top: 1.25rem;
        padding-bottom: 2rem;
    }

    [data-testid="stSidebar"] {
        background: #0b1220 !important;
        border-right: 1px solid var(--mrd-border);
    }

    [data-testid="stSidebar"] * {
        color: var(--mrd-text) !important;
    }

    h1, h2, h3, h4, h5, h6, p, span, label {
        color: var(--mrd-text) !important;
    }

    .mrd-title {
        margin-bottom: 0.1rem;
        letter-spacing: 0;
    }

    .mrd-subtitle {
        color: var(--mrd-muted);
        font-size: 0.96rem;
        margin-bottom: 1.1rem;
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
        font-size: 0.78rem;
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

    .mrd-section {
        margin-top: 1.25rem;
        padding-top: 1rem;
        border-top: 1px solid var(--mrd-border);
    }

    .mrd-pill {
        display: inline-block;
        background: rgba(56, 189, 248, 0.12);
        border: 1px solid rgba(56, 189, 248, 0.35);
        color: var(--mrd-accent);
        border-radius: 999px;
        padding: 0.22rem 0.58rem;
        font-size: 0.78rem;
        margin-right: 0.35rem;
        margin-bottom: 0.3rem;
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
def read_csv(path_text: str, modified_time: float | None) -> pd.DataFrame:
    if modified_time is None:
        return pd.DataFrame()
    try:
        return pd.read_csv(path_text)
    except (OSError, pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError):
        return pd.DataFrame()


@st.cache_data(show_spinner=False)
def count_csv_rows(path_text: str, modified_time: float | None) -> int | None:
    if modified_time is None:
        return None
    try:
        count = 0
        with open(path_text, "rb") as handle:
            for count, _ in enumerate(handle, start=1):
                pass
        return max(count - 1, 0)
    except OSError:
        return None


def load(name: str) -> pd.DataFrame:
    path = DATA_FILES[name]
    path_text, modified_time = file_signature(path)
    return read_csv(path_text, modified_time).copy()


def row_count(name: str) -> int | None:
    path = DATA_FILES[name]
    path_text, modified_time = file_signature(path)
    return count_csv_rows(path_text, modified_time)


def loaded_files() -> pd.DataFrame:
    rows = []
    for name, path in DATA_FILES.items():
        exists = path.exists()
        rows.append(
            {
                "file": name,
                "path": str(path.relative_to(ROOT)),
                "exists": exists,
                "rows": row_count(name) if exists else None,
                "core": name in CORE_FILES,
            }
        )
    return pd.DataFrame(rows)


def missing_core_files() -> list[Path]:
    return [DATA_FILES[name] for name in sorted(CORE_FILES) if not DATA_FILES[name].exists()]


def present_columns(df: pd.DataFrame, columns: Iterable[str]) -> list[str]:
    return [column for column in columns if column in df.columns]


def clean(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if text.lower() == "nan":
        return ""
    return text


def number(value: object, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def fmt_int(value: object) -> str:
    try:
        return f"{int(round(float(value))):,}"
    except (TypeError, ValueError):
        return "0"


def fmt_decimal(value: object) -> str:
    try:
        return f"{float(value):,.2f}"
    except (TypeError, ValueError):
        return ""


def sort_priority(series: pd.Series) -> pd.Series:
    return series.map(PRIORITY_ORDER).fillna(99)


def sort_table(df: pd.DataFrame, columns: list[str], ascending: list[bool]) -> pd.DataFrame:
    sort_columns = [column for column in columns if column in df.columns]
    if not sort_columns:
        return df
    sort_ascending = [ascending[columns.index(column)] for column in sort_columns]
    return df.sort_values(
        sort_columns,
        ascending=sort_ascending,
        na_position="last",
        key=lambda series: sort_priority(series) if series.name in {"priority", "research_priority"} else series,
    )


def option_values(series: pd.Series) -> list[str]:
    values = series.dropna().astype(str).str.strip()
    values = values[values != ""]
    return sorted(values.unique().tolist())


def pipe_values(value: object) -> list[str]:
    return [item.strip() for item in clean(value).split("|") if item.strip()]


def pipe_options(series: pd.Series) -> list[str]:
    values: set[str] = set()
    for value in series.dropna():
        values.update(pipe_values(value))
    return sorted(values)


def filter_values(df: pd.DataFrame, column: str, label: str, key: str) -> pd.DataFrame:
    if df.empty or column not in df.columns:
        return df
    options = option_values(df[column])
    if not options:
        return df
    selected = st.multiselect(label, options, key=key)
    if not selected:
        return df
    return df[df[column].astype(str).isin(selected)]


def filter_pipe_values(df: pd.DataFrame, column: str, label: str, key: str) -> pd.DataFrame:
    if df.empty or column not in df.columns:
        return df
    options = pipe_options(df[column])
    if not options:
        return df
    selected = st.multiselect(label, options, key=key)
    if not selected:
        return df
    selected_set = set(selected)
    return df[df[column].apply(lambda value: bool(selected_set.intersection(pipe_values(value))))]


def draw_table(df: pd.DataFrame, columns: list[str] | None = None, height: int = 520) -> None:
    if df.empty:
        st.info("No rows available for this view.")
        return
    view = df.copy()
    if columns is not None:
        selected = present_columns(view, columns)
        if not selected:
            st.info("No display columns are available for this data.")
            return
        view = view[selected].copy()

    for column in view.columns:
        if column in RANK_COLUMNS:
            view[column] = view[column].map(fmt_int)
        elif column in SCORE_COLUMNS:
            view[column] = view[column].map(fmt_decimal)

    st.dataframe(view, use_container_width=True, hide_index=True, height=height)


def header(title: str, subtitle: str) -> None:
    st.markdown(f'<h1 class="mrd-title">{title}</h1>', unsafe_allow_html=True)
    st.markdown(f'<div class="mrd-subtitle">{subtitle}</div>', unsafe_allow_html=True)


def section() -> None:
    st.markdown('<div class="mrd-section"></div>', unsafe_allow_html=True)


def cards(items: list[tuple[str, object, str]]) -> None:
    columns = st.columns(len(items))
    for column, (label, value, note) in zip(columns, items):
        with column:
            if isinstance(value, str):
                display_value = value
            else:
                display_value = fmt_int(value)
            st.markdown(
                f"""
                <div class="mrd-card">
                    <div class="mrd-card-label">{label}</div>
                    <div class="mrd-card-value">{display_value}</div>
                    <div class="mrd-card-note">{note}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def primary_pipe(value: object) -> str:
    values = pipe_values(value)
    return values[0] if values else ""


def research_queue_data() -> pd.DataFrame:
    candidates = load("research_candidates")
    scorecard = load("opportunity_scorecard")
    if candidates.empty and scorecard.empty:
        return pd.DataFrame()
    if candidates.empty:
        queue = scorecard.copy()
        queue["priority"] = queue.get("recommended_priority", "")
        queue["opportunity_score"] = queue.get("total_score", 0)
        queue["product_recommendation"] = ""
        queue["customization_recommendation"] = ""
        queue["next_action"] = queue.get("explanation", "")
        return sort_table(queue, ["priority", "opportunity_score"], [True, False])

    queue = candidates.rename(
        columns={
            "suggested_products": "product_recommendation",
            "suggested_customizations": "customization_recommendation",
        }
    ).copy()
    if not scorecard.empty:
        score_columns = [
            "parent_demand",
            "child_segment",
            "total_score",
            "recommended_priority",
            "explanation",
        ]
        queue = queue.merge(
            scorecard[present_columns(scorecard, score_columns)],
            on=["parent_demand", "child_segment"],
            how="left",
        )
        if "total_score" in queue.columns:
            queue["opportunity_score"] = queue["total_score"].combine_first(queue.get("opportunity_score"))
    queue["primary_product"] = queue.get("product_recommendation", "").apply(primary_pipe)
    queue["primary_customization"] = queue.get("customization_recommendation", "").apply(primary_pipe)
    return sort_table(queue, ["priority", "opportunity_score"], [True, False])


def executive_page() -> None:
    header(
        "Executive Intelligence",
        "Leadership view for portfolios, demand, research priorities, and next actions.",
    )
    portfolios = load("portfolio_master")
    composite_demands = load("composite_demands")
    demand_intelligence = load("demand_intelligence")
    scorecards = load("market_scorecard")
    queue = research_queue_data()

    total_demands = len(composite_demands) if not composite_demands.empty else len(demand_intelligence)
    p1_count = int((queue["priority"] == "P1").sum()) if "priority" in queue.columns else 0
    cards(
        [
            ("Total Portfolios", len(portfolios), "Parent markets in portfolio layer"),
            ("Total Demands", total_demands, "Composite or intelligence demand rows"),
            ("Research Candidates", len(queue), "Child niches ready for review"),
            ("P1 Count", p1_count, "Highest-priority research actions"),
        ]
    )

    section()
    tab_market, tab_portfolio, tab_actions = st.tabs(
        ["Top Market Scorecards", "Top Portfolio Recommendations", "Top Research Actions"]
    )
    with tab_market:
        draw_table(
            sort_table(scorecards, ["research_priority", "overall_score"], [True, False]).head(25),
            [
                "demand_id",
                "demand_name",
                "market_size",
                "growth_stage",
                "competition_level",
                "seasonality",
                "overall_score",
                "research_priority",
                "recommended_action",
            ],
        )
    with tab_portfolio:
        draw_table(
            sort_table(portfolios, ["research_priority", "expansion_potential"], [True, False]).head(25),
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
    with tab_actions:
        draw_table(
            queue.head(35),
            [
                "priority",
                "parent_demand",
                "child_segment",
                "opportunity_score",
                "product_recommendation",
                "customization_recommendation",
                "next_action",
            ],
        )


def research_queue_page() -> None:
    header(
        "Research Queue",
        "Filtered action queue combining decision candidates and transparent opportunity scoring.",
    )
    queue = research_queue_data()
    if queue.empty:
        st.info("Research queue data is missing. Expected decision and scoring CSV outputs.")
        return

    filters = st.columns(4)
    with filters[0]:
        queue = filter_values(queue, "priority", "Priority", "rq_priority")
    with filters[1]:
        queue = filter_values(queue, "parent_demand", "Parent Demand", "rq_parent")
    with filters[2]:
        queue = filter_pipe_values(queue, "product_recommendation", "Product", "rq_product")
    with filters[3]:
        queue = filter_pipe_values(queue, "customization_recommendation", "Customization", "rq_custom")

    cards(
        [
            ("Visible Rows", len(queue), "Filtered research actions"),
            ("P1", int((queue["priority"] == "P1").sum()), "Immediate research candidates"),
            ("Avg Score", f"{number(queue['opportunity_score'].mean()):.1f}", "Mean opportunity score"),
            ("Parents", queue["parent_demand"].nunique(), "Markets represented"),
        ]
    )
    section()
    draw_table(
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


def portfolio_page() -> None:
    header(
        "Portfolio Planner",
        "Coverage, investment recommendations, whitespace, and weekly execution planning.",
    )
    master = load("portfolio_master")
    summary = load("portfolio_summary")
    roadmap = load("portfolio_roadmap")
    whitespace = load("whitespace_analysis")
    if master.empty and summary.empty and roadmap.empty:
        st.info("Portfolio CSV outputs are missing or empty.")
        return

    if not master.empty:
        filters = st.columns(3)
        with filters[0]:
            master = filter_values(master, "portfolio_stage", "Portfolio Stage", "pf_stage")
        with filters[1]:
            master = filter_values(master, "investment_recommendation", "Investment", "pf_investment")
        with filters[2]:
            master = filter_values(master, "market_size", "Market Size", "pf_size")

    cards(
        [
            ("Portfolios", len(master), "Filtered parent markets"),
            (
                "Avg Coverage",
                f"{number(master['coverage_score'].mean() if 'coverage_score' in master.columns else 0):.1f}",
                "Estimated coverage score",
            ),
            (
                "Expand",
                int((master["investment_recommendation"] == "Expand").sum())
                if "investment_recommendation" in master.columns
                else 0,
                "Expansion recommendations",
            ),
            (
                "Invest Aggressively",
                int((master["investment_recommendation"] == "Invest Aggressively").sum())
                if "investment_recommendation" in master.columns
                else 0,
                "Highest investment tier",
            ),
        ]
    )

    section()
    tab_master, tab_summary, tab_roadmap, tab_white = st.tabs(
        ["Portfolio Master", "Summary", "Roadmap by Week", "Whitespace"]
    )
    with tab_master:
        draw_table(
            master,
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
        draw_table(
            summary,
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
        draw_table(roadmap, ["week", "parent_demand", "child_segment", "product", "customization", "priority", "reason"])
    with tab_white:
        draw_table(
            whitespace,
            ["parent_demand", "missing_child_segment", "confidence", "expected_value", "reason"],
        )


def scorecard_page() -> None:
    header("Opportunity Scorecard", "Transparent score components for every child segment.")
    scores = load("opportunity_scorecard")
    if scores.empty:
        st.info("Opportunity scorecard CSV is missing or empty.")
        return

    filters = st.columns(3)
    with filters[0]:
        scores = filter_values(scores, "parent_demand", "Parent Demand", "sc_parent")
    with filters[1]:
        scores = filter_values(scores, "recommended_priority", "Priority", "sc_priority")
    with filters[2]:
        minimum = st.slider("Minimum Total Score", 0, 100, 0, 5)
        if "total_score" in scores.columns:
            scores = scores[scores["total_score"] >= minimum]

    scores = sort_table(scores, ["total_score", "child_segment"], [False, True])
    if not scores.empty and "child_segment" in scores.columns:
        selected = st.selectbox("Inspect Segment", scores["child_segment"].astype(str).tolist(), key="score_segment")
        row = scores[scores["child_segment"].astype(str) == selected].iloc[0]
        chart = pd.DataFrame(
            {
                "score": [
                    number(row.get("market_size_score")),
                    number(row.get("growth_score")),
                    number(row.get("competition_score")),
                    number(row.get("expansion_score")),
                    number(row.get("seasonality_score")),
                    number(row.get("product_fit_score")),
                    number(row.get("total_score")),
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
        left, right = st.columns([1.2, 1])
        with left:
            st.bar_chart(chart)
        with right:
            st.markdown("#### Explanation")
            st.write(clean(row.get("explanation")) or "No explanation available.")

    section()
    draw_table(
        scores,
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


def fit_page() -> None:
    header(
        "Product & Customization Fit",
        "Product score matrix and personalization fit for each child segment.",
    )
    product = load("product_fit_matrix")
    custom = load("customization_fit_matrix")
    if product.empty and custom.empty:
        st.info("Product and customization fit CSVs are missing or empty.")
        return

    combined = product.merge(custom, on="child_segment", how="outer", suffixes=("_product", "_custom"))
    filters = st.columns(3)
    with filters[0]:
        combined = filter_values(combined, "best_product", "Best Product", "fit_product")
    with filters[1]:
        combined = filter_values(combined, "best_customization", "Best Customization", "fit_custom")
    with filters[2]:
        query = st.text_input("Search Child Segment", key="fit_search")
        if query.strip() and "child_segment" in combined.columns:
            combined = combined[combined["child_segment"].astype(str).str.contains(query.strip(), case=False, na=False)]

    tab_combo, tab_product, tab_custom = st.tabs(["Combined Fit", "Product Scores", "Customization Scores"])
    with tab_combo:
        draw_table(
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
    with tab_product:
        draw_table(
            product,
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
    with tab_custom:
        draw_table(
            custom,
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


def evidence_keywords_frame(record: pd.Series) -> pd.DataFrame:
    if "evidence_keywords" not in record.index or pd.isna(record["evidence_keywords"]):
        return pd.DataFrame(columns=["keyword_order", "keyword"])
    keywords = [keyword.strip() for keyword in str(record["evidence_keywords"]).split("|") if keyword.strip()]
    return pd.DataFrame({"keyword_order": range(1, len(keywords) + 1), "keyword": keywords})


def merge_evidence_keywords(records: pd.DataFrame, fallback: pd.DataFrame, id_column: str) -> pd.DataFrame:
    if (
        records.empty
        or fallback.empty
        or id_column not in records.columns
        or id_column not in fallback.columns
        or "evidence_keywords" not in fallback.columns
    ):
        return records
    evidence = fallback[[id_column, "evidence_keywords"]].dropna(subset=[id_column]).copy()
    if "evidence_keywords" not in records.columns:
        return records.merge(evidence, on=id_column, how="left")
    merged = records.merge(evidence, on=id_column, how="left", suffixes=("", "_fallback"))
    merged["evidence_keywords"] = merged["evidence_keywords"].where(
        merged["evidence_keywords"].notna() & (merged["evidence_keywords"].astype(str).str.strip() != ""),
        merged["evidence_keywords_fallback"],
    )
    return merged.drop(columns=["evidence_keywords_fallback"])


def monthly_curve(evidence: pd.DataFrame, id_column: str, record_id: str) -> pd.DataFrame:
    required = {id_column, "month", "search_frequency_rank", "normalized_keyword"}
    if evidence.empty or not required.issubset(evidence.columns):
        return pd.DataFrame()
    rows = evidence[evidence[id_column].astype(str) == str(record_id)].copy()
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


def select_record(df: pd.DataFrame, label_columns: list[str], id_columns: list[str], key: str) -> pd.Series | None:
    label_column = next((column for column in label_columns if column in df.columns), None)
    id_column = next((column for column in id_columns if column in df.columns), label_column)
    if df.empty or not label_column or not id_column:
        return None
    working = df.copy()
    working["_label"] = working[label_column].astype(str) + "  [" + working[id_column].astype(str) + "]"
    selected = st.selectbox("Select record", working["_label"].tolist(), key=key)
    if not selected:
        return None
    return working[working["_label"] == selected].iloc[0]


def evidence_detail(record: pd.Series, evidence: pd.DataFrame, id_column: str | None, record_id: str | None) -> None:
    cards(
        [
            ("Best Rank", record.get("best_rank", 0), "Lowest known rank"),
            ("Median Rank", record.get("median_rank", 0), "Middle evidence rank"),
            ("Active Months", record.get("active_months", 0), "Observed months"),
            ("Keyword Count", record.get("keyword_count", 0), "Evidence breadth"),
        ]
    )

    if "evidence_keywords" in record.index and pd.notna(record["evidence_keywords"]):
        st.text_area("Evidence Keywords", str(record["evidence_keywords"]), height=120, disabled=True)

    summarized = evidence_keywords_frame(record)
    if evidence.empty or not id_column or not record_id or id_column not in evidence.columns:
        if not summarized.empty:
            st.info("Showing summarized evidence from available dashboard data.")
            st.dataframe(summarized, use_container_width=True, hide_index=True, height=320)
        else:
            st.info("Detailed keyword evidence file is missing or empty.")
        return

    rows = evidence[evidence[id_column].astype(str) == str(record_id)].copy()
    if rows.empty:
        if not summarized.empty:
            st.info("Showing summarized evidence from available dashboard data.")
            st.dataframe(summarized, use_container_width=True, hide_index=True, height=320)
        else:
            st.info("Detailed keyword evidence file is missing or empty.")
        return

    st.subheader("Keyword Evidence")
    draw_table(sort_table(rows, ["search_frequency_rank", "month"], [True, True]).head(200), height=360)

    curve = monthly_curve(evidence, id_column, record_id)
    if not curve.empty:
        st.subheader("Monthly Trend")
        st.line_chart(curve.set_index("month")[["best_rank", "median_rank"]])
        draw_table(curve, ["month", "best_rank", "median_rank", "keyword_count"], height=220)


def evidence_page() -> None:
    header(
        "Market Evidence",
        "Compact evidence-light keyword tables with fallback to summarized evidence_keywords.",
    )
    source = st.radio("Evidence Source", ["Demand", "Segment", "Opportunity", "Market Node"], horizontal=True)

    if source == "Demand":
        records = merge_evidence_keywords(load("composite_demands"), load("opportunity_master"), "demand_id")
        records = sort_table(records, ["best_rank", "keyword_count"], [True, False])
        selected = select_record(records, ["demand_name"], ["demand_id", "demand_name"], "ev_demand")
        if selected is None:
            st.info("No demand records available.")
            return
        st.subheader(clean(selected.get("demand_name")) or "Demand")
        evidence_detail(selected, load("demand_evidence_light"), "demand_id", clean(selected.get("demand_id")))
        return

    if source == "Segment":
        records = sort_table(load("demand_segments"), ["segment_strength", "best_rank"], [False, True])
        selected = select_record(records, ["segment_name"], ["segment_id", "segment_name"], "ev_segment")
        if selected is None:
            st.info("No segment records available.")
            return
        st.subheader(clean(selected.get("segment_name")) or "Segment")
        evidence_detail(selected, load("segment_evidence_light"), "segment_id", clean(selected.get("segment_id")))
        return

    if source == "Market Node":
        records = sort_table(load("market_nodes"), ["strength_score", "best_rank"], [False, True])
        selected = select_record(records, ["demand"], ["market_node_id", "demand"], "ev_node")
        if selected is None:
            st.info("No market node records available.")
            return
        label = clean(selected.get("demand")) or "Market Node"
        niche = clean(selected.get("niche"))
        st.subheader(f"{label} + {niche}" if niche else label)
        evidence_detail(
            selected,
            load("market_node_evidence_light"),
            "market_node_id",
            clean(selected.get("market_node_id")),
        )
        return

    records = sort_table(load("opportunity_master"), ["opportunity_score", "best_rank"], [False, True])
    selected = select_record(records, ["demand_name"], ["opportunity_id", "demand_name"], "ev_opp")
    if selected is None:
        st.info("No opportunity records available.")
        return
    st.subheader(clean(selected.get("demand_name")) or "Opportunity")
    evidence_detail(selected, load("demand_evidence_light"), "demand_id", clean(selected.get("demand_id")))


def sidebar() -> str:
    st.sidebar.title("MRnD")
    st.sidebar.caption("Executive Intelligence Dashboard V2")
    page = st.sidebar.radio(
        "Navigation",
        [
            "Executive Intelligence",
            "Research Queue",
            "Portfolio Planner",
            "Opportunity Scorecard",
            "Product & Customization Fit",
            "Market Evidence",
        ],
    )

    missing = missing_core_files()
    if missing:
        with st.sidebar.expander("Missing Core CSV Files", expanded=False):
            for path in missing:
                st.caption(str(path.relative_to(ROOT)))

    with st.sidebar.expander("Loaded Data Files", expanded=False):
        draw_table(loaded_files(), height=360)

    st.sidebar.markdown("---")
    st.sidebar.caption("Compact CSV dashboard. No DuckDB. No large ignored evidence files.")
    return page


def main() -> None:
    page = sidebar()
    if page == "Executive Intelligence":
        executive_page()
    elif page == "Research Queue":
        research_queue_page()
    elif page == "Portfolio Planner":
        portfolio_page()
    elif page == "Opportunity Scorecard":
        scorecard_page()
    elif page == "Product & Customization Fit":
        fit_page()
    elif page == "Market Evidence":
        evidence_page()


if __name__ == "__main__":
    main()
