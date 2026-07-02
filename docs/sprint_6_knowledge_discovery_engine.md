# Sprint 6 - Knowledge Discovery Engine

This sprint adds a Knowledge Discovery Engine for the MRnD Market Intelligence
Platform.

The goal is to expand the Market Taxonomy from real Amazon Brand Analytics data
without automatically modifying master knowledge files.

Sprint 6 does not build Opportunity Score.

## Purpose

The Knowledge Discovery Engine scans interpreted keyword data and identifies
candidate taxonomy terms for manual review.

It helps answer:

- Which market terms are appearing in real ABA data but are not in the master
  taxonomy?
- Which entity types have weak coverage?
- Which gift-related and personalized-related terms should be reviewed first?
- Which obvious non-POD terms should be routed to ignore review?

## Inputs

DuckDB database:

```text
data/output/aba.duckdb
```

Required tables:

```sql
normalized_keywords
demand_objects
```

Master knowledge files:

```text
knowledge/master/*.csv
```

The engine reads all master files so it can avoid proposing terms that are
already present as canonical values or aliases.

## Output Folder

The engine creates:

```text
knowledge/review/discovery/
```

## Candidate Outputs

Generated review files:

```text
recipient_candidates.csv
profession_candidates.csv
interest_candidates.csv
occasion_candidates.csv
theme_candidates.csv
product_candidates.csv
customization_candidates.csv
ignore_candidates.csv
```

Each candidate file uses this schema:

```text
candidate
suggested_category
frequency
best_rank
example_keywords
recommended_aliases
confidence
action
```

Candidate files are review inputs only. They are not accepted taxonomy.

## Coverage Report

The engine writes:

```text
knowledge/review/discovery/coverage_report.csv
```

Schema:

```text
entity_type
matched_rows
total_rows
coverage_percent
unknown_rows
```

Coverage is calculated from `demand_objects` entity columns. `theme` is included
as a Sprint 6 discovery category, so it currently reports zero matched rows until
a future theme entity exists in the data model.

## Summary Report

The engine writes:

```text
knowledge/review/discovery/summary.txt
```

The summary includes:

- source table counts
- date range
- number of weak or unmatched keywords reviewed
- candidate counts by output file
- coverage summary
- non-POD exclusion policy
- reminder that `knowledge/master/` was not modified

## Candidate Detection

The engine reads weakly matched or unmatched rows from `demand_objects`.

A keyword is considered discovery-eligible when:

- it is gift-related
- it is personalized-related
- or it has one or fewer matched entity values

Gift-related keywords are detected from terms such as:

```text
gift
gifts
present
presents
```

Personalized-related keywords are detected from terms such as:

```text
personalized
custom
name
photo
picture
portrait
engraved
monogram
```

Gift-related and personalized-related rows are prioritized first in candidate
output ordering.

## Non-POD Exclusions

Obvious non-POD terms are excluded from taxonomy candidate files and routed to:

```text
ignore_candidates.csv
```

Examples:

```text
amazon gift card
gift card
roblox gift card
starbucks gift card
iphone
toilet paper
paper towels
electronics
grocery
household commodity
```

The ignore file still requires manual review. It exists so reviewers can decide
whether a term should remain ignored or become strategically useful later.

## Run

```powershell
python notebooks/knowledge_discovery_engine.py
```

Optional arguments:

```powershell
python notebooks/knowledge_discovery_engine.py --max-source-keywords 250000
python notebooks/knowledge_discovery_engine.py --max-examples 5
```

## Review Workflow

1. Run the engine after monthly ABA import and demand object refresh.
2. Open `knowledge/review/discovery/summary.txt`.
3. Review `coverage_report.csv` to identify weak taxonomy areas.
4. Review candidate files in this order:

```text
ignore_candidates.csv
recipient_candidates.csv
profession_candidates.csv
interest_candidates.csv
occasion_candidates.csv
theme_candidates.csv
product_candidates.csv
customization_candidates.csv
```

5. Manually approve, edit, reject, or defer candidates.
6. Add approved terms to the appropriate `knowledge/master/*.csv` file manually.
7. Rebuild downstream analytical tables after master knowledge changes.

## Review Policy

The Knowledge Discovery Engine must not:

- automatically modify `knowledge/master/`
- create or update DuckDB tables
- build Opportunity Score
- replace the existing demand object pipeline
- treat generated candidates as accepted taxonomy

All generated candidates require manual review.

## Architecture Position

Sprint 6 supports the Demand Engine and future Opportunity Engine by improving
taxonomy coverage.

```text
ABA Keywords
  -> normalized_keywords
  -> demand_objects
  -> Knowledge Discovery Engine
  -> knowledge/review/discovery/*.csv
  -> manual review
  -> knowledge/master/*.csv
```

Knowledge discovery is a review workflow, not an automated merge workflow.
