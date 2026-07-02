# Data Dictionary

This document describes the current and planned data model for the Market Intelligence Platform.

## Current Physical Tables

The current DuckDB database at `data/output/aba.duckdb` contains these tables:

```text
raw_keywords
import_history
```

## Implemented Or Planned Tables

Some tables are already created in the current database. Others are implemented by pipeline scripts or planned for later research engines but may not exist until their pipeline is run.

| Table | Status | Owner Stage | Created By |
| --- | --- | --- | --- |
| `raw_keywords` | Current physical table | Import | `src/pipeline/import_aba.py` |
| `import_history` | Current physical table | Import | `src/pipeline/import_aba.py` |
| `normalized_keywords` | Implemented, derived table | Intent Discovery | `src/pipeline/build_research_model.py` |
| `keyword_metrics_monthly` | Implemented, derived table | Demand Prioritization input | `src/pipeline/build_research_model.py` |
| `keyword_trend` | Implemented, derived table | Demand Prioritization input | `src/pipeline/build_research_model.py` |
| `demand_objects` | Implemented, derived table | Demand Discovery | `src/pipeline/build_demand_objects.py` |
| `knowledge_entities` | Planned logical table | Intent Discovery | Future Knowledge Base Engine |
| `entity_match_coverage` | Planned table | Intent Discovery | Future Coverage Engine |
| `demand_scores` | Planned table | Demand Prioritization | Future Demand Prioritization Engine |
| `solution_candidates` | Planned table | Solution Mapping | Future Solution Mapping Engine |
| `product_gap_analysis` | Planned table | Product Gap Analysis | Future Product Gap Analysis Engine |
| `internal_product_map` | Planned table | Internal Mapping | Future Internal Mapping Engine |
| `research_backlog` | Planned table | Research Backlog | Future Research Backlog Engine |
| `review_decisions` | Planned table | Research Backlog | Future Review Workflow Engine |

## Lineage

```text
data/raw/*.csv
  -> raw_keywords
  -> normalized_keywords
  -> keyword_metrics_monthly
  -> keyword_trend

knowledge/master/*.csv
  -> demand_objects

normalized_keywords + knowledge/master/*.csv
  -> demand_objects
  -> knowledge/review/unknown_*.csv

demand_objects + keyword_metrics_monthly + keyword_trend
  -> demand_scores
  -> solution_candidates
  -> product_gap_analysis
  -> internal_product_map
  -> research_backlog
  -> review_decisions
```

`raw_keywords` is the immutable imported source table for the platform. Derived tables should be rebuilt from it and should not mutate it.

## Table Details

### raw_keywords

Status: current physical table

Purpose: stores imported Amazon Brand Analytics keyword rows after CSV import.

Grain: one raw ABA keyword row per source file and reporting month.

Columns:

| Column | Type | Description |
| --- | --- | --- |
| `search_frequency_rank` | BIGINT | ABA search frequency rank. Lower rank means higher search demand. |
| `search_term` | VARCHAR | Raw search keyword from ABA. |
| `top_clicked_brand_1` | VARCHAR | First top clicked brand. |
| `top_clicked_brands_2` | VARCHAR | Second top clicked brand. |
| `top_clicked_brands_3` | VARCHAR | Third top clicked brand. |
| `top_clicked_category_1` | VARCHAR | First top clicked category. |
| `top_clicked_category_2` | VARCHAR | Second top clicked category. |
| `top_clicked_category_3` | VARCHAR | Third top clicked category. |
| `top_clicked_product_1_asin` | VARCHAR | ASIN for first top clicked product. |
| `top_clicked_product_1_product_title` | VARCHAR | Title for first top clicked product. |
| `top_clicked_product_1_click_share` | DOUBLE | Click share for first top clicked product. |
| `top_clicked_product_1_conversion_share` | DOUBLE | Conversion share for first top clicked product. |
| `top_clicked_product_2_asin` | VARCHAR | ASIN for second top clicked product. |
| `top_clicked_product_2_product_title` | VARCHAR | Title for second top clicked product. |
| `top_clicked_product_2_click_share` | DOUBLE | Click share for second top clicked product. |
| `top_clicked_product_2_conversion_share` | DOUBLE | Conversion share for second top clicked product. |
| `top_clicked_product_3_asin` | VARCHAR | ASIN for third top clicked product. |
| `top_clicked_product_3_product_title` | VARCHAR | Title for third top clicked product. |
| `top_clicked_product_3_click_share` | DOUBLE | Click share for third top clicked product. |
| `top_clicked_product_3_conversion_share` | DOUBLE | Conversion share for third top clicked product. |
| `reporting_date` | DATE | ABA reporting date. |
| `source_file` | VARCHAR | Source CSV filename. |
| `month` | VARCHAR | Reporting month in `YYYY-MM` format. |
| `imported_at` | TIMESTAMP | Timestamp when the row was imported. |

Lineage: `data/raw/*.csv` -> `data/processed/*.parquet` -> `raw_keywords`

### import_history

Status: current physical table

Purpose: records import attempts for ABA source files.

Grain: one row per file import attempt.

Columns:

| Column | Type | Description |
| --- | --- | --- |
| `file_name` | VARCHAR | Imported source filename. |
| `month` | VARCHAR | Reporting month detected from filename. |
| `rows` | BIGINT | Number of rows imported for the file. |
| `started_at` | TIMESTAMP | Import start timestamp. |
| `finished_at` | TIMESTAMP | Import finish timestamp. |
| `duration_seconds` | DOUBLE | Import duration in seconds. |
| `status` | VARCHAR | Import status, such as `success` or `failed`. |

Lineage: import pipeline runtime metadata -> `import_history`

### normalized_keywords

Status: implemented, derived table

Purpose: standardizes the keyword text and selects the core fields needed for research.

Grain: one normalized keyword row per raw keyword row.

Columns:

| Column | Type | Description |
| --- | --- | --- |
| `search_frequency_rank` | BIGINT | Casted search frequency rank. |
| `raw_search_term` | VARCHAR | Original search term from `raw_keywords`. |
| `normalized_search_term` | VARCHAR | Lowercased, trimmed, punctuation-normalized search term with selected variant normalization. |
| `reporting_date` | DATE | Reporting date. |
| `month` | VARCHAR | Reporting month in `YYYY-MM` format. |
| `source_file` | VARCHAR | Source file inherited from `raw_keywords`. |
| `imported_at` | TIMESTAMP | Import timestamp inherited from `raw_keywords`. |

Lineage: `raw_keywords` -> `normalized_keywords`

### keyword_metrics_monthly

Status: implemented, derived table

Purpose: aggregates keyword demand metrics by normalized term and month.

Grain: one row per normalized keyword and month.

Columns:

| Column | Type | Description |
| --- | --- | --- |
| `normalized_search_term` | VARCHAR | Normalized keyword. |
| `month` | VARCHAR | Reporting month. |
| `min_search_frequency_rank` | BIGINT | Best rank for the normalized term in the month. |
| `avg_search_frequency_rank` | DOUBLE | Average rank for the normalized term in the month. |
| `keyword_count` | BIGINT | Number of raw keyword rows behind the normalized term for the month. |
| `raw_keyword_examples` | VARCHAR | Representative raw search terms. |

Lineage: `normalized_keywords` -> `keyword_metrics_monthly`

### keyword_trend

Status: implemented, derived table

Purpose: summarizes month-level rank trend for each normalized keyword.

Grain: one row per normalized keyword.

Columns:

| Column | Type | Description |
| --- | --- | --- |
| `normalized_search_term` | VARCHAR | Normalized keyword. |
| `months_present` | BIGINT | Number of months where the keyword appears. |
| `first_month` | VARCHAR | First observed month. |
| `last_month` | VARCHAR | Last observed month. |
| `best_rank` | BIGINT | Best observed rank. |
| `worst_rank` | BIGINT | Worst observed rank. |
| `rank_change` | BIGINT | Last observed rank minus first observed rank. Negative means rank improved. |
| `trend_label` | VARCHAR | Trend classification such as `emerging`, `growing`, `declining`, or `stable`. |

Lineage: `keyword_metrics_monthly` -> `keyword_trend`

### demand_objects

Status: implemented, derived table

Purpose: transforms normalized keywords into structured demand records using knowledge base entity matching.

Grain: one demand object per normalized keyword row.

Columns:

| Column | Type | Description |
| --- | --- | --- |
| `demand_id` | BIGINT | Generated row identifier for the demand object build. |
| `raw_keyword` | VARCHAR | Raw keyword text. |
| `normalized_keyword` | VARCHAR | Normalized keyword text. |
| `recipient` | VARCHAR | Matched recipient entity. |
| `profession` | VARCHAR | Matched profession entity. |
| `interest` | VARCHAR | Matched interest entity. |
| `pet` | VARCHAR | Matched pet entity. |
| `occasion` | VARCHAR | Matched occasion entity. |
| `product` | VARCHAR | Matched product entity. |
| `customization` | VARCHAR | Matched customization entity. |
| `style` | VARCHAR | Matched style entity. |
| `modifier` | VARCHAR | Matched modifier entity. |
| `month` | VARCHAR | Reporting month. |
| `search_frequency_rank` | BIGINT | Search frequency rank inherited from normalized keyword row. |
| `reporting_date` | DATE | Reporting date. |

Lineage: `normalized_keywords` + `knowledge/master/*.csv` -> `demand_objects`

### knowledge_entities

Status: planned logical table

Purpose: database representation of curated knowledge base entities from `knowledge/master/*.csv`.

Expected grain: one row per canonical entity and entity type.

Planned columns:

| Column | Description |
| --- | --- |
| `entity_id` | Stable identifier for the entity. |
| `canonical` | Preferred entity value. |
| `entity_type` | Entity category. |
| `aliases` | Alias list used for matching. |
| `priority` | Matching and review priority. |
| `active` | Whether the entity is active. |
| `notes` | Curator notes. |

Lineage: `knowledge/master/*.csv` -> `knowledge_entities`

### entity_match_coverage

Status: planned table

Purpose: summarizes how well the knowledge base covers demand keywords.

Expected grain: one row per entity type, month, and optional demand segment.

Planned columns:

| Column | Description |
| --- | --- |
| `entity_type` | Entity category being measured. |
| `month` | Reporting month. |
| `total_keywords` | Number of keywords evaluated. |
| `matched_keywords` | Number of keywords with a match for the entity type. |
| `unmatched_keywords` | Number of keywords without a match for the entity type. |
| `coverage_rate` | Matched keywords divided by total keywords. |

Lineage: `demand_objects` -> `entity_match_coverage`

### demand_scores

Status: planned table

Purpose: prioritizes demand objects for research and product action.

Expected grain: one row per demand object or demand object group.

Planned columns:

| Column | Description |
| --- | --- |
| `demand_id` | Demand object identifier. |
| `demand_strength_score` | Score based on rank and keyword count. |
| `trend_score` | Score based on rank movement and month presence. |
| `entity_completeness_score` | Score based on matched entity coverage. |
| `confidence_score` | Overall confidence in the opportunity. |
| `priority_label` | Human-readable priority band. |

Lineage: `demand_objects` + `keyword_metrics_monthly` + `keyword_trend` -> `demand_scores`

### solution_candidates

Status: planned table

Purpose: maps prioritized demand to possible product and design solutions.

Expected grain: one row per demand and candidate solution.

Planned columns:

| Column | Description |
| --- | --- |
| `solution_id` | Stable solution candidate identifier. |
| `demand_id` | Related demand object. |
| `product` | Recommended product format. |
| `design_angle` | Suggested design or message angle. |
| `customization_type` | Personalization type if applicable. |
| `solution_fit_score` | Fit score for the demand-solution pairing. |
| `notes` | Strategy notes. |

Lineage: `demand_scores` + `demand_objects` -> `solution_candidates`

### product_gap_analysis

Status: planned table

Purpose: identifies demand with missing, weak, stale, or saturated product coverage.

Expected grain: one row per solution candidate and gap assessment.

Planned columns:

| Column | Description |
| --- | --- |
| `gap_id` | Stable gap identifier. |
| `solution_id` | Related solution candidate. |
| `internal_product_count` | Number of matching internal products. |
| `coverage_status` | Missing, weak, covered, saturated, or refresh-needed. |
| `gap_score` | Strength of the identified product gap. |
| `recommended_action` | New product, refresh, differentiate, defer, or reject. |

Lineage: `solution_candidates` + internal catalog data -> `product_gap_analysis`

### internal_product_map

Status: planned table

Purpose: maps product gaps to internal assets, capabilities, owners, and constraints.

Expected grain: one row per product gap and internal execution path.

Planned columns:

| Column | Description |
| --- | --- |
| `internal_map_id` | Stable mapping identifier. |
| `gap_id` | Related product gap. |
| `owner` | Internal owner or team. |
| `asset_reuse_level` | Estimated reuse of existing design or product assets. |
| `production_feasibility` | Feasibility band. |
| `launch_window` | Recommended launch timing. |
| `risk_notes` | Execution risks and constraints. |

Lineage: `product_gap_analysis` + internal asset data -> `internal_product_map`

### research_backlog

Status: planned table

Purpose: manages the opportunity lifecycle from research candidate to decision.

Expected grain: one row per backlog opportunity.

Planned columns:

| Column | Description |
| --- | --- |
| `backlog_id` | Stable backlog identifier. |
| `demand_id` | Related demand object. |
| `solution_id` | Related solution candidate when available. |
| `gap_id` | Related product gap when available. |
| `status` | New, reviewing, approved, deferred, rejected, launched, or measured. |
| `owner` | Assigned owner. |
| `next_action` | Recommended next step. |
| `priority_label` | Priority band. |
| `created_at` | Backlog creation timestamp. |
| `updated_at` | Last update timestamp. |

Lineage: `demand_scores` + `solution_candidates` + `product_gap_analysis` + `internal_product_map` -> `research_backlog`

### review_decisions

Status: planned table

Purpose: records human review decisions that improve the knowledge base and opportunity workflow.

Expected grain: one row per review decision.

Planned columns:

| Column | Description |
| --- | --- |
| `review_id` | Stable review identifier. |
| `review_type` | Knowledge entity, demand object, solution, gap, or backlog review. |
| `subject_id` | Identifier of the reviewed item. |
| `decision` | Approved, rejected, merged, renamed, deferred, or needs-more-data. |
| `reviewer` | Person or process that made the decision. |
| `decision_notes` | Human-readable rationale. |
| `decided_at` | Decision timestamp. |

Lineage: review workflow events -> `review_decisions`; accepted knowledge changes may later update `knowledge/master/*.csv`

## Non-Table Files

### knowledge/master/*.csv

Purpose: curated master knowledge dictionaries used for entity matching.

Schema:

```text
canonical,entity_type,aliases,priority,active,notes
```

Lineage: human curation -> `knowledge/master/*.csv` -> `demand_objects`

### knowledge/review/unknown_*.csv

Purpose: append-only review candidate files for terms that did not match a knowledge entity type.

Schema:

```text
candidate,entity_type,raw_keyword_example,keyword_count,first_month,last_month,best_rank,status,notes
```

Lineage: `demand_objects` unmatched entity fields -> `knowledge/review/unknown_*.csv` -> human review -> possible updates to `knowledge/master/*.csv`
