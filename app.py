"""Streamlit dashboard for MRnD Demand Intelligence CSV outputs."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_ROOT = PROJECT_ROOT / "data" / "output"

CSV_FILES = {
    "opportunity_master": OUTPUT_ROOT / "opportunity" / "opportunity_master.csv",
    "research_backlog": OUTPUT_ROOT / "opportunity" / "research_backlog.csv",
    "top_100_opportunities": OUTPUT_ROOT / "opportunity" / "top_100_opportunities.csv",
    "demand_segments": OUTPUT_ROOT / "demand_segments" / "demand_segments.csv",
    "segment_keywords": OUTPUT_ROOT / "demand_segments" / "segment_keywords.csv",
    "top_200_segments": OUTPUT_ROOT / "demand_segments" / "top_200_segments.csv",
    "composite_demands": OUTPUT_ROOT / "composite_demands" / "composite_demands.csv",
    "composite_keywords": OUTPUT_ROOT / "composite_demands" / "composite_keywords.csv",
    "demand_strength_v3": OUTPUT_ROOT / "composite_demands" / "demand_strength_v3.csv",
    "top_composite_demands": OUTPUT_ROOT / "composite_demands" / "top_composite_demands.csv",
    "market_nodes": OUTPUT_ROOT / "market_nodes" / "market_nodes.csv",
    "market_node_monthly": OUTPUT_ROOT / "market_nodes" / "market_node_monthly.csv",
    "market_node_evidence": OUTPUT_ROOT / "market_nodes" / "market_node_evidence.csv",
    "intent_summary": OUTPUT_ROOT / "intent_layer" / "intent_summary.csv",
    "intent_market_nodes": OUTPUT_ROOT / "intent_layer" / "intent_market_nodes.csv",
}

RANK_COLUMNS = [
    "best_rank",
    "p25_rank",
    "median_rank",
    "average_rank",
    "search_frequency_rank",
]


st.set_page_config(
    page_title="MRnD Demand Intelligence",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)


st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1.25rem;
        padding-bottom: 2rem;
    }
    div[data-testid="stMetric"] {
        background: rgba(127, 127, 127, 0.08);
        border: 1px solid rgba(127, 127, 127, 0.18);
        border-radius: 8px;
        padding: 0.75rem 0.9rem;
    }
    div[data-testid="stMetricLabel"] p {
        font-size: 0.82rem;
    }
    .mrd-section {
        border-top: 1px solid rgba(127, 127, 127, 0.2);
        margin-top: 1.5rem;
        padding-top: 1rem;
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
    return pd.read_csv(path_text)


def load_csv(name: str) -> pd.DataFrame:
    path = CSV_FILES[name]
    path_text, modified_time = file_signature(path)
    return read_csv_cached(path_text, modified_time).copy()


def missing_files() -> list[Path]:
    return [path for path in CSV_FILES.values() if not path.exists()]


def format_int(value: object) -> str:
    if pd.isna(value):
        return "0"
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return "0"


def format_rank(value: object) -> str:
    if pd.isna(value):
        return ""
    try:
        return f"{int(round(float(value))):,}"
    except (TypeError, ValueError):
        return str(value)


def existing_columns(df: pd.DataFrame, columns: Iterable[str]) -> list[str]:
    return [column for column in columns if column in df.columns]


def clean_options(series: pd.Series) -> list[str]:
    values = series.dropna().astype(str).str.strip()
    values = values[values != ""]
    return sorted(values.unique().tolist())


def filter_multiselect(
    df: pd.DataFrame,
    column: str,
    label: str,
    key: str,
) -> pd.DataFrame:
    if column not in df.columns or df.empty:
        return df
    options = clean_options(df[column])
    if not options:
        return df
    selected = st.multiselect(label, options, key=key)
    if selected:
        return df[df[column].astype(str).isin(selected)]
    return df


def sort_by_available(
    df: pd.DataFrame,
    columns: list[str],
    ascending: list[bool],
) -> pd.DataFrame:
    sort_columns = [column for column in columns if column in df.columns]
    if not sort_columns:
        return df
    sort_ascending = [ascending[columns.index(column)] for column in sort_columns]
    return df.sort_values(sort_columns, ascending=sort_ascending, na_position="last")


def add_evidence_keywords(
    records: pd.DataFrame,
    evidence: pd.DataFrame,
    id_column: str,
    limit: int = 8,
) -> pd.DataFrame:
    if records.empty or evidence.empty or id_column not in records.columns or id_column not in evidence.columns:
        return records
    if "normalized_keyword" not in evidence.columns:
        return records

    evidence_columns = [id_column, "normalized_keyword"]
    if "search_frequency_rank" in evidence.columns:
        evidence_columns.append("search_frequency_rank")

    working = evidence[evidence_columns].dropna(subset=[id_column, "normalized_keyword"]).copy()
    if working.empty:
        return records

    sort_columns = [id_column]
    ascending = [True]
    if "search_frequency_rank" in working.columns:
        sort_columns.append("search_frequency_rank")
        ascending.append(True)
    sort_columns.append("normalized_keyword")
    ascending.append(True)

    working = working.sort_values(sort_columns, ascending=ascending, na_position="last")
    working = working.drop_duplicates([id_column, "normalized_keyword"])
    working = working.groupby(id_column, as_index=False).head(limit)
    evidence_strings = (
        working.groupby(id_column)["normalized_keyword"]
        .apply(lambda values: " | ".join(values.astype(str)))
        .rename("evidence_keywords")
        .reset_index()
    )

    result = records.drop(columns=["evidence_keywords"], errors="ignore")
    return result.merge(evidence_strings, on=id_column, how="left")


def display_table(df: pd.DataFrame, columns: list[str], height: int = 520) -> None:
    view = df[existing_columns(df, columns)].copy()
    if view.empty:
        st.info("No rows available for the selected view.")
        return

    for column in RANK_COLUMNS:
        if column in view.columns:
            view[column] = view[column].map(format_rank)

    st.dataframe(view, use_container_width=True, hide_index=True, height=height)


def monthly_curve(evidence: pd.DataFrame, id_column: str, selected_id: str) -> pd.DataFrame:
    if evidence.empty or id_column not in evidence.columns or "month" not in evidence.columns:
        return pd.DataFrame()
    if "search_frequency_rank" not in evidence.columns:
        return pd.DataFrame()

    rows = evidence[evidence[id_column].astype(str) == str(selected_id)].copy()
    if rows.empty:
        return pd.DataFrame()

    curve = (
        rows.groupby("month", as_index=False)
        .agg(
            best_rank=("search_frequency_rank", "min"),
            median_rank=("search_frequency_rank", "median"),
            keyword_count=("normalized_keyword", "count"),
        )
        .sort_values("month")
    )
    return curve


def show_metric_row(metrics: list[tuple[str, object]]) -> None:
    columns = st.columns(len(metrics))
    for column, (label, value) in zip(columns, metrics):
        column.metric(label, format_int(value))


def executive_overview() -> None:
    intent_summary = load_csv("intent_summary")
    demand_strength = load_csv("demand_strength_v3")
    demand_segments = load_csv("demand_segments")
    opportunity_master = load_csv("opportunity_master")
    top_100 = load_csv("top_100_opportunities")

    st.title("Executive Overview")

    total_raw_keywords = (
        intent_summary["keyword_count"].sum()
        if not intent_summary.empty and "keyword_count" in intent_summary.columns
        else 0
    )

    priority_counts = (
        opportunity_master["priority"].value_counts()
        if not opportunity_master.empty and "priority" in opportunity_master.columns
        else pd.Series(dtype="int64")
    )

    show_metric_row(
        [
            ("Raw Keywords", total_raw_keywords),
            ("Composite Demands", len(demand_strength)),
            ("Demand Segments", len(demand_segments)),
            ("Opportunities", len(opportunity_master)),
        ]
    )

    show_metric_row(
        [
            ("P1", priority_counts.get("P1", 0)),
            ("P2", priority_counts.get("P2", 0)),
            ("P3", priority_counts.get("P3", 0)),
            ("Watchlist", priority_counts.get("Watchlist", 0)),
        ]
    )

    st.markdown('<div class="mrd-section"></div>', unsafe_allow_html=True)
    st.subheader("Top 20 Opportunities")
    top_rows = top_100.head(20) if not top_100.empty else opportunity_master.head(20)
    display_table(
        top_rows,
        [
            "opportunity_id",
            "demand_name",
            "priority",
            "opportunity_score",
            "best_rank",
            "p25_rank",
            "trend",
            "recipient",
            "profession",
            "interest",
            "holiday",
            "recommendation_note",
        ],
        height=560,
    )


def demand_explorer() -> None:
    st.title("Demand Explorer")
    demands = load_csv("top_composite_demands")
    if demands.empty:
        demands = load_csv("demand_strength_v3")
    evidence = load_csv("composite_keywords")

    if demands.empty:
        st.info("Composite demand CSVs are missing or empty.")
        return

    demands = add_evidence_keywords(demands, evidence, "demand_id")
    demands = sort_by_available(
        demands,
        ["strength_score", "best_rank", "active_months"],
        [False, True, False],
    )

    filter_columns = st.columns(3)
    with filter_columns[0]:
        demands = filter_multiselect(demands, "intent", "Intent", "demand_intent")
    with filter_columns[1]:
        demands = filter_multiselect(demands, "trend", "Trend", "demand_trend")
    with filter_columns[2]:
        demands = filter_multiselect(demands, "recipient", "Recipient", "demand_recipient")

    limit = st.slider("Rows", 20, 250, 100, 10, key="demand_rows")
    display_table(
        demands.head(limit),
        [
            "demand_id",
            "demand_name",
            "intent",
            "recipient",
            "profession",
            "interest",
            "holiday",
            "best_rank",
            "strength_score",
            "trend",
            "active_months",
            "evidence_keywords",
        ],
    )


def segment_explorer() -> None:
    st.title("Segment Explorer")
    segments = load_csv("top_200_segments")
    if segments.empty:
        segments = load_csv("demand_segments")

    if segments.empty:
        st.info("Demand segment CSVs are missing or empty.")
        return

    segments = sort_by_available(
        segments,
        ["segment_strength", "best_rank", "active_months"],
        [False, True, False],
    )

    filter_columns = st.columns(4)
    with filter_columns[0]:
        segments = filter_multiselect(segments, "intent", "Intent", "segment_intent")
    with filter_columns[1]:
        segments = filter_multiselect(segments, "parent_demand", "Parent Demand", "segment_parent")
    with filter_columns[2]:
        segments = filter_multiselect(segments, "trend", "Trend", "segment_trend")
    with filter_columns[3]:
        segments = filter_multiselect(segments, "holiday", "Holiday", "segment_holiday")

    display_table(
        segments,
        [
            "segment_id",
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
            "segment_strength",
            "best_rank",
            "trend",
            "active_months",
            "evidence_keywords",
        ],
    )


def opportunity_explorer() -> None:
    st.title("Opportunity Explorer")
    backlog = load_csv("research_backlog")
    top_100 = load_csv("top_100_opportunities")

    if backlog.empty and top_100.empty:
        st.info("Opportunity CSVs are missing or empty.")
        return

    filtered = backlog.copy()
    st.subheader("Research Backlog")
    filter_columns = st.columns(5)
    with filter_columns[0]:
        filtered = filter_multiselect(filtered, "priority", "Priority", "opp_priority")
    with filter_columns[1]:
        filtered = filter_multiselect(filtered, "trend", "Trend", "opp_trend")
    with filter_columns[2]:
        filtered = filter_multiselect(filtered, "recipient", "Recipient", "opp_recipient")
    with filter_columns[3]:
        filtered = filter_multiselect(filtered, "interest", "Interest", "opp_interest")
    with filter_columns[4]:
        filtered = filter_multiselect(filtered, "holiday", "Holiday", "opp_holiday")

    filtered = sort_by_available(
        filtered,
        ["opportunity_score", "best_rank"],
        [False, True],
    )
    display_table(
        filtered,
        [
            "opportunity_id",
            "demand_name",
            "priority",
            "opportunity_score",
            "trend",
            "intent",
            "recipient",
            "profession",
            "pet",
            "interest",
            "occasion",
            "holiday",
            "best_rank",
            "p25_rank",
            "active_months",
            "evidence_keywords",
            "recommendation_note",
            "next_action",
            "research_status",
        ],
    )

    st.markdown('<div class="mrd-section"></div>', unsafe_allow_html=True)
    st.subheader("Top 100 Opportunities")
    display_table(
        top_100,
        [
            "opportunity_id",
            "demand_name",
            "priority",
            "opportunity_score",
            "best_rank",
            "p25_rank",
            "trend",
            "recipient",
            "profession",
            "interest",
            "holiday",
            "evidence_keywords",
            "recommendation_note",
        ],
    )


def select_record(df: pd.DataFrame, label_column: str, id_column: str, key: str) -> pd.Series | None:
    if df.empty or label_column not in df.columns or id_column not in df.columns:
        return None

    working = df.copy()
    working["_select_label"] = (
        working[label_column].astype(str)
        + "  ["
        + working[id_column].astype(str)
        + "]"
    )
    options = working["_select_label"].tolist()
    selected = st.selectbox("Select record", options, key=key)
    if not selected:
        return None
    return working[working["_select_label"] == selected].iloc[0]


def show_evidence_detail(
    record: pd.Series,
    evidence: pd.DataFrame,
    id_column: str,
    record_id: str,
) -> None:
    metric_candidates = [
        ("Best Rank", record.get("best_rank")),
        ("Median Rank", record.get("median_rank")),
        ("Active Months", record.get("active_months")),
        ("Keyword Count", record.get("keyword_count")),
    ]
    show_metric_row(metric_candidates)

    if "evidence_keywords" in record.index and pd.notna(record["evidence_keywords"]):
        st.text_area(
            "Evidence Keywords",
            str(record["evidence_keywords"]),
            height=120,
            disabled=True,
        )

    if evidence.empty:
        st.info("Detailed keyword evidence file is missing or empty.")
        return

    rows = evidence[evidence[id_column].astype(str) == str(record_id)].copy()
    if rows.empty:
        st.info("No detailed evidence rows found for this record.")
        return

    rows = sort_by_available(rows, ["search_frequency_rank", "month"], [True, True])
    st.subheader("Keyword Evidence")
    display_table(
        rows.head(200),
        [
            "raw_keyword",
            "normalized_keyword",
            "month",
            "search_frequency_rank",
            "segment_dimension",
            "segment_value",
        ],
        height=360,
    )

    curve = monthly_curve(evidence, id_column, record_id)
    if not curve.empty:
        st.subheader("Monthly Trend")
        st.line_chart(curve.set_index("month")[["best_rank", "median_rank"]])
        display_table(curve, ["month", "best_rank", "median_rank", "keyword_count"], height=220)


def market_evidence() -> None:
    st.title("Market Evidence")
    source = st.radio(
        "Evidence Source",
        ["Demand", "Segment", "Opportunity", "Market Node"],
        horizontal=True,
    )

    if source == "Demand":
        records = load_csv("demand_strength_v3")
        evidence = load_csv("composite_keywords")
        records = add_evidence_keywords(records, evidence, "demand_id")
        records = sort_by_available(records, ["strength_score", "best_rank"], [False, True])
        selected = select_record(records, "demand_name", "demand_id", "evidence_demand")
        if selected is None:
            st.info("No demand records available.")
            return
        st.subheader(str(selected["demand_name"]))
        show_evidence_detail(selected, evidence, "demand_id", str(selected["demand_id"]))
        return

    if source == "Segment":
        records = load_csv("demand_segments")
        evidence = load_csv("segment_keywords")
        records = sort_by_available(records, ["segment_strength", "best_rank"], [False, True])
        selected = select_record(records, "segment_name", "segment_id", "evidence_segment")
        if selected is None:
            st.info("No segment records available.")
            return
        st.subheader(str(selected["segment_name"]))
        show_evidence_detail(selected, evidence, "segment_id", str(selected["segment_id"]))
        return

    if source == "Market Node":
        records = load_csv("market_nodes")
        evidence = load_csv("market_node_evidence")
        records = add_evidence_keywords(records, evidence, "market_node_id")
        records = sort_by_available(records, ["strength_score", "best_rank"], [False, True])

        if not records.empty:
            records = records.copy()
            label_columns = existing_columns(records, ["demand", "niche"])
            if label_columns:
                records["market_node_label"] = records[label_columns].fillna("").astype(str).agg(
                    lambda values: " / ".join(value for value in values if value.strip()),
                    axis=1,
                )
            else:
                records["market_node_label"] = records["market_node_id"].astype(str)

        selected = select_record(records, "market_node_label", "market_node_id", "evidence_market_node")
        if selected is None:
            st.info("No market node records available.")
            return
        st.subheader(str(selected["market_node_label"]))
        show_evidence_detail(selected, evidence, "market_node_id", str(selected["market_node_id"]))
        return

    records = load_csv("opportunity_master")
    evidence = load_csv("composite_keywords")
    records = add_evidence_keywords(records, evidence, "demand_id")
    records = sort_by_available(records, ["opportunity_score", "best_rank"], [False, True])
    selected = select_record(records, "demand_name", "opportunity_id", "evidence_opportunity")
    if selected is None:
        st.info("No opportunity records available.")
        return
    st.subheader(str(selected["demand_name"]))
    demand_id = str(selected["demand_id"]) if "demand_id" in selected.index else ""
    show_evidence_detail(selected, evidence, "demand_id", demand_id)


def render_sidebar() -> str:
    st.sidebar.title("MRnD")
    st.sidebar.caption("Demand Intelligence Platform")
    page = st.sidebar.radio(
        "Page",
        [
            "Executive Overview",
            "Demand Explorer",
            "Segment Explorer",
            "Opportunity Explorer",
            "Market Evidence",
        ],
    )

    missing = missing_files()
    if missing:
        with st.sidebar.expander("Missing CSV files", expanded=False):
            for path in missing:
                st.caption(str(path.relative_to(PROJECT_ROOT)))

    st.sidebar.markdown("---")
    st.sidebar.caption("Data source: CSV exports under data/output/")
    return page


def main() -> None:
    page = render_sidebar()

    if page == "Executive Overview":
        executive_overview()
    elif page == "Demand Explorer":
        demand_explorer()
    elif page == "Segment Explorer":
        segment_explorer()
    elif page == "Opportunity Explorer":
        opportunity_explorer()
    elif page == "Market Evidence":
        market_evidence()


if __name__ == "__main__":
    main()
