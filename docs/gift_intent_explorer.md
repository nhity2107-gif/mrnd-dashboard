# Gift Intent Explorer

This notebook-style script exports gift-related demand slices from the DuckDB
`demand_objects` table.

## Prerequisites

The explorer reads:

```text
data/output/aba.duckdb
```

Required source table:

```sql
demand_objects
```

If `demand_objects` does not exist yet, run the upstream pipelines first:

```powershell
python src/pipeline/build_research_model.py
python src/pipeline/build_demand_objects.py
```

## Run

```powershell
python notebooks/gift_intent_explorer.py
```

## Output Folder

The script creates:

```text
data/output/gift_intent/
```

## Exports

`gift_keywords.csv`

All rows from `demand_objects` where `normalized_keyword` contains one of these
gift-intent terms:

```text
gift
gifts
present
presents
```

`top_gift_recipients.csv`

Top combined `recipient` and `profession` values within gift keywords.

`top_gift_occasions.csv`

Top `occasion` values within gift keywords.

`top_gift_products.csv`

Top `product` values within gift keywords.

`top_gift_interests.csv`

Top `interest` values within gift keywords.

`unmatched_gift_keywords.csv`

Gift keyword rows where all current entity columns are unmatched:

```text
recipient
profession
interest
pet
occasion
product
customization
style
modifier
```

## Top File Schema

Each top file contains:

```text
value
keyword_count
best_rank
example_keywords
```

Rows are sorted by `keyword_count` descending, then `best_rank` ascending.

`example_keywords` contains up to five raw keyword examples for the value.

## Console Summary

The script prints:

- DuckDB database path
- Output folder path
- gift keyword row count
- distinct gift keyword count
- month coverage
- best gift keyword rank
- top-value counts for each export
- unmatched gift keyword row count
