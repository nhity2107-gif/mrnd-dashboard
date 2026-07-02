# Sprint 2 - Research Data Model

This sprint builds foundational research tables from the imported `raw_keywords` DuckDB table.

## Scope

The pipeline reads from:

```text
data/output/aba.duckdb
```

Source table:

```sql
raw_keywords
```

The pipeline does not modify `raw_keywords`.

## Tables

`normalized_keywords`

```text
search_frequency_rank
raw_search_term
normalized_search_term
reporting_date
month
source_file
imported_at
```

`keyword_metrics_monthly`

```text
normalized_search_term
month
min_search_frequency_rank
avg_search_frequency_rank
keyword_count
raw_keyword_examples
```

`keyword_trend`

```text
normalized_search_term
months_present
first_month
last_month
best_rank
worst_rank
rank_change
trend_label
```

## Term Normalization

`normalized_search_term` is derived from the raw search term by:

- lowercasing
- trimming spaces
- collapsing repeated spaces
- removing punctuation except apostrophes
- normalizing selected variants:
  - `t-shirt`, `tshirt`, `tee` -> `shirt`
  - `personalised` -> `personalized`
  - `customised` -> `customized`
  - `gifts` -> `gift`
  - `shirts` -> `shirt`
  - `mugs` -> `mug`
  - `tumblers` -> `tumbler`
  - `ornaments` -> `ornament`
  - `blankets` -> `blanket`

## Trend Labels

- `emerging`: first appears after the earliest available month and is present in the latest available month
- `growing`: rank improves across every observed month-to-month step
- `declining`: rank worsens across every observed month-to-month step
- `stable`: mixed, unchanged, or insufficient trend signal

Lower search frequency rank is better, so a negative `rank_change` indicates improvement from first observed month to last observed month.

## Run

Build or refresh the derived research tables:

```powershell
python src/pipeline/build_research_model.py
```

Drop existing derived research tables before rebuilding:

```powershell
python src/pipeline/build_research_model.py --rebuild
```

## Validate

Inspect row counts:

```sql
SELECT count(*) FROM normalized_keywords;
SELECT count(*) FROM keyword_metrics_monthly;
SELECT count(*) FROM keyword_trend;
```

Inspect trend labels:

```sql
SELECT trend_label, count(*)
FROM keyword_trend
GROUP BY trend_label
ORDER BY trend_label;
```

Inspect normalized examples:

```sql
SELECT raw_search_term, normalized_search_term
FROM normalized_keywords
LIMIT 20;
```

Log file:

```text
logs/build_research_model.log
```

This sprint does not implement AI, dashboard features, or final clustering.
