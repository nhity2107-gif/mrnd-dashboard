# Sprint 1 - Import Engine

This sprint implements only the raw Amazon Brand Analytics import pipeline.

## What It Does

- Reads every CSV file from `data/raw/`.
- Processes one CSV at a time.
- Detects the reporting month from filenames like `US_Top_Search_Terms_Simple_Month_2025_09_30.csv`.
- Writes one Parquet file per CSV into `data/processed/` using the same base filename.
- Creates or updates `data/output/aba.duckdb`.
- Creates the DuckDB table `raw_keywords`.
- Keeps every original ABA field, normalizes column names to `snake_case`, and appends:
  - `source_file`
  - `month`
  - `imported_at`
- Automatically casts known import types:
  - `search_frequency_rank` to `Int64`
  - `*_click_share` to `Float64`
  - `*_conversion_share` to `Float64`
  - `reporting_date` to `Date`
  - `source_file` and `month` to `Utf8`
  - `imported_at` to `Datetime`
- Creates the DuckDB table `import_history` with one row per file import attempt.
- Writes logs to `logs/import_aba.log` and the console.

The importer does not clean, cluster, classify, or enrich keywords.

## Run

Import all raw files:

```powershell
python src/pipeline/import_aba.py
```

Import a small sample from each CSV:

```powershell
python src/pipeline/import_aba.py --sample 50000
```

Rebuild generated Parquet files and the DuckDB `raw_keywords` table:

```powershell
python src/pipeline/import_aba.py --rebuild
```

Rebuild using a sample:

```powershell
python src/pipeline/import_aba.py --rebuild --sample 50000
```

## Outputs

Parquet files:

```text
data/processed/
```

DuckDB database:

```text
data/output/aba.duckdb
```

DuckDB table:

```sql
raw_keywords
```

Import history table:

```sql
import_history
```

Import history columns:

```text
file_name
month
rows
started_at
finished_at
duration_seconds
status
```

Log file:

```text
logs/import_aba.log
```
