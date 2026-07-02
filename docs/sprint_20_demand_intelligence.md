# Sprint 20 - Demand Intelligence Engine V1

Sprint 20 adds a deterministic business intelligence layer for demand-level
research decisions.

The goal is to evaluate each demand from a business perspective instead of only
showing keyword and rank statistics.

## Run

From the project root:

```powershell
python src/pipeline/build_demand_intelligence.py --rebuild
```

## Inputs

```text
data/output/composite_demands/composite_demands.csv
data/output/composite_demands/demand_strength_v3.csv
data/output/demand_segments/demand_segments.csv
data/output/opportunity/opportunity_master.csv
data/output/insights/*.csv
```

The engine uses existing CSV exports only. It does not connect to DuckDB.

## Outputs

Folder:

```text
data/output/intelligence/
```

Files:

```text
demand_intelligence.csv
expansion_graph.csv
research_queue.csv
executive_dashboard.csv
```

## demand_intelligence.csv

Purpose:

```text
One row per demand with business-level scores and a recommended strategy.
```

Columns:

```text
demand_id
demand_name
market_size_score
expansion_score
growth_score
seasonality_score
evidence_score
overall_score
market_size_tier
expansion_tier
research_priority
recommended_strategy
executive_summary
```

## Score Components

### Market Size Score

Primary signals:

```text
best_rank
p25_rank
median_rank
```

Keyword count is not a primary signal. Lower Search Frequency Rank is stronger.

### Expansion Score

Signals:

```text
number of child segments
diversity of segment types
diversity of interests
diversity of occasions
max child segment strength
```

This score answers:

```text
Can this demand expand into multiple researchable sub-markets?
```

### Growth Score

Signals:

```text
trend
growth_map growth signal
demand strength
active months
```

### Seasonality Score

Signals:

```text
seasonality_map
holiday and occasion child segments
```

Seasonal opportunities can score well when they create clear planning windows.

### Evidence Score

Signals:

```text
opportunity evidence score
median-rank quality
number of child segments
active-month consistency
```

Evidence score is about confidence and richness, not raw keyword volume.

## Overall Score

Weighted deterministic formula:

```text
30% market_size_score
25% expansion_score
20% growth_score
10% seasonality_score
15% evidence_score
```

## Research Priority

```text
P1        overall_score >= 69
P2        overall_score >= 60
P3        overall_score >= 50
Watchlist otherwise
```

## Recommended Strategy

The engine chooses one:

```text
Core Market
Seasonal Expansion
Emerging Opportunity
Niche Expansion
Validate Further
Low Priority
```

Examples:

```text
Core Market
Large evergreen demand with high expansion potential and strong ranking signals.

Seasonal Expansion
Demand has holiday or occasion leverage and should be researched against timing windows.

Niche Expansion
Demand has meaningful child-segment breadth but needs more specific niche research.
```

## expansion_graph.csv

Purpose:

```text
Summarize child-segment breadth by parent demand.
```

Columns:

```text
parent_demand
segment_count
seasonal_segments
interest_segments
pet_segments
profession_segments
occasion_segments
theme_segments
expansion_score
```

## research_queue.csv

Purpose:

```text
Create an action-oriented research queue from demand intelligence results.
```

Columns:

```text
priority
demand
reason
recommended_action
next_step
```

Example:

```text
P1
Mom Gift
Large demand with many scalable child segments
Research micro niches such as Dog Mom, Gardening Mom, Reading Mom
```

## executive_dashboard.csv

Purpose:

```text
One-row executive summary for dashboard cards.
```

Columns:

```text
Total Demand
P1
P2
P3
Top Opportunity
Largest Market
Highest Expansion
Fastest Growing
Highest Seasonality
```

## Safety

This sprint:

```text
creates a new independent pipeline
exports CSV only
does not modify existing pipeline outputs
does not modify database tables
does not connect to DuckDB
does not use AI
does not use clustering
```

All scoring and notes are deterministic business rules.
