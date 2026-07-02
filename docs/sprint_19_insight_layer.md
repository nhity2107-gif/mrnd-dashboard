# Sprint 19 - Insight Layer V1

Sprint 19 adds a deterministic Insight Layer for the MRnD Demand Intelligence
Platform.

The goal is to move the dashboard from keyword lookup toward business-readable
insights. This layer exports CSVs only. Dashboard V2 can read these files later.

## Run

From the project root:

```powershell
python src/pipeline/build_insight_layer.py --rebuild
```

## Inputs

```text
data/output/composite_demands/composite_demands.csv
data/output/composite_demands/demand_strength_v3.csv
data/output/demand_segments/demand_segments.csv
data/output/opportunity/opportunity_master.csv
data/output/intent_layer/intent_summary.csv
```

The layer does not connect to DuckDB and does not modify existing tables or
pipeline outputs.

## Outputs

Folder:

```text
data/output/insights/
```

Files:

```text
demand_size_map.csv
segment_size_map.csv
seasonality_map.csv
growth_map.csv
niche_direction_map.csv
research_opportunity_queue.csv
```

## Demand Size Map

Purpose:

```text
Classify composite demands by rank-based market size.
```

Columns:

```text
demand_id
demand_name
size_tier
best_rank
p25_rank
median_rank
keyword_count
active_months
trend
strength_score
insight_note
```

Size tiers:

```text
Mega
Large
Mid
Small
Micro
```

The tier logic primarily uses Search Frequency Rank-derived fields:

```text
best_rank
p25_rank
median_rank
strength_score
active_months
```

Keyword count is retained as context but is not the main sizing metric.

## Segment Size Map

Purpose:

```text
Classify demand segments by rank-based segment size.
```

Columns:

```text
segment_id
parent_demand
segment_name
size_tier
best_rank
median_rank
keyword_count
active_months
trend
segment_strength
insight_note
```

Segment size uses the same philosophy as demand size, but with segment-level
thresholds.

## Seasonality Map

Purpose:

```text
Identify whether a demand, segment, or opportunity behaves like an evergreen,
seasonal, emerging, declining, or insufficient-data entity.
```

Columns:

```text
entity_type
entity_id
entity_name
start_month
peak_month
last_month
active_months
seasonality_type
seasonality_note
research_start_recommendation
```

Seasonality types:

```text
Evergreen
Q4 Seasonal
Holiday Seasonal
Emerging
Declining
Insufficient Data
```

V1 does not have entity-level monthly curves in the requested source files.
Therefore:

```text
start_month and last_month come from intent_summary.csv's observed import range.
peak_month is inferred from deterministic holiday and occasion markers.
```

Examples:

```text
christmas -> Q4 Seasonal, peak month December
halloween -> Q4 Seasonal, peak month October
mother's day -> Holiday Seasonal, peak month May
graduation -> Holiday Seasonal, peak month May
```

## Growth Map

Purpose:

```text
Convert trend labels into readable growth signals.
```

Columns:

```text
entity_type
entity_id
entity_name
trend
growth_signal
rank_momentum
active_months
growth_note
```

Growth is deterministic:

```text
growing + strong rank -> Strong Growth
growing -> Growing
emerging -> Emerging
stable -> Stable
declining -> Declining
```

## Niche Direction Map

Purpose:

```text
Classify demand segments into research direction types.
```

Columns:

```text
parent_demand
segment_name
direction_type
size_tier
trend
best_rank
segment_strength
potential_direction_note
```

Direction types:

```text
Core Segment
Seasonal Segment
Emerging Segment
Lifestyle Segment
Pet Segment
Interest Segment
Theme Segment
```

The layer uses deterministic fields such as:

```text
holiday
occasion
lifestyle
pet
interest
theme
trend
```

## Research Opportunity Queue

Purpose:

```text
Produce a ranked queue of demand and segment research candidates.
```

Columns:

```text
priority_rank
opportunity_type
parent_demand
segment_name
size_tier
trend
seasonality_type
best_rank
strength_score
reason
recommended_action
```

The queue combines:

```text
rank-based size tier
strength score
best rank
trend
seasonality type
```

It does not use competition, AI clustering, or internal catalog gap scoring.

## Safety

This sprint:

```text
exports CSV only
does not modify existing pipeline tables
does not modify original data files
does not connect to DuckDB
does not use AI or clustering
```

## Dashboard V2

Dashboard V2 can use these insight files to show:

```text
market size tiers
seasonal planning windows
growth signals
niche directions
research queue
```
