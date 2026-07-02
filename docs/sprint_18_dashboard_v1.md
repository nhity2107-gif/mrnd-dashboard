# Sprint 18 - Research Dashboard V1

Sprint 18 adds a read-only Streamlit dashboard for MRnD leadership to explore
Demand, Demand Segment, and Opportunity outputs.

The dashboard reads CSV exports only. It does not connect to DuckDB and does not
modify any pipeline tables or files.

## App

```text
app.py
```

## Run

From the project root:

```powershell
streamlit run app.py
```

If using the project virtual environment:

```powershell
.\.venv\Scripts\streamlit.exe run app.py
```

## Input Folders

```text
data/output/opportunity/
data/output/demand_segments/
data/output/composite_demands/
data/output/market_nodes/
data/output/intent_layer/
```

The app handles missing CSV files gracefully. Missing files are listed in the
sidebar and the affected page shows an empty-state message instead of failing.

## Pages

### Executive Overview

Shows:

```text
total raw keywords
composite demands
demand segments
opportunities
P1 / P2 / P3 / Watchlist count
top 20 opportunities
```

The raw keyword count comes from `intent_summary.csv` so the dashboard does not
need to load the large `intent_keywords.csv` file.

### Demand Explorer

Shows top composite demands with:

```text
demand name
intent
recipient
profession
interest
holiday
best rank
strength
trend
active months
evidence keywords
```

Evidence keywords are joined from `composite_keywords.csv`.

### Segment Explorer

Shows top demand segments with:

```text
segment name
parent demand
segment strength
best rank
trend
active months
evidence keywords
```

Filters include intent, parent demand, trend, and holiday.

### Opportunity Explorer

Shows `research_backlog.csv` with filters for:

```text
priority
trend
recipient
interest
holiday
```

Also shows `top_100_opportunities.csv`.

### Market Evidence

Allows selecting:

```text
Demand
Segment
Opportunity
```

For the selected record, the page shows:

```text
evidence keywords
best rank
median rank
active months
keyword count
detailed keyword evidence
monthly best-rank and median-rank trend
```

Demand and Opportunity evidence comes from `composite_keywords.csv`.

Segment evidence comes from `segment_keywords.csv`.

## Design Notes

The dashboard is dark-theme friendly and uses Streamlit's active theme colors.
The custom CSS only adds restrained spacing, borders, and metric styling.

Tables are intentionally dense and scan-friendly because this is an operational
research dashboard, not a marketing site.

## Safety

The dashboard:

```text
uses pandas
reads CSV outputs only
does not connect to DuckDB
does not modify existing pipeline files
does not write database tables
does not implement dashboard-side scoring
```

## Validation

Syntax validation:

```powershell
python -m py_compile app.py
```

The app can then be launched with:

```powershell
streamlit run app.py
```
