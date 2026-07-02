# Sprint 4 - Opportunity Engine

This sprint designs the analytical layer that turns interpreted market demand
into prioritized product opportunities.

Sprint 4 does not build another keyword matching pipeline. Keyword matching and
entity extraction remain the responsibility of the existing demand object and
knowledge base workflows. The Opportunity Engine starts after intent and demand
signals already exist.

## Philosophy

```text
Search Term
        ↓
Intent
        ↓
Demand
        ↓
Niche
        ↓
Product
        ↓
Customization
        ↓
Internal Catalog
        ↓
Opportunity
```

The platform should separate market interpretation from execution decisions.
A search term is not an opportunity by itself. It becomes useful only after the
system understands the shopper intent, groups it into demand, identifies the
niche, maps possible product solutions, compares those solutions against the
internal catalog, and scores the resulting opportunity.

## Architecture Overview

Sprint 4 introduces five analytical layers:

1. Demand
2. Niche
3. Solution
4. Internal Product Mapping
5. Opportunity Score

These layers should be implemented as derived analytical tables. They should not
mutate `raw_keywords`, `normalized_keywords`, `demand_objects`, or master
knowledge files.

The proposed lineage is:

```text
raw_keywords
  -> normalized_keywords
  -> demand_objects
  -> demand_groups
  -> niche_segments
  -> solution_candidates
  -> internal_product_mapping
  -> opportunity_scores
```

## 1. Demand

### Purpose

The Demand layer groups individual `demand_objects` into reusable demand patterns.

Its job is to answer:

- What are shoppers asking for?
- Which entity combinations repeatedly appear?
- Which demand patterns have strong rank, frequency, or trend signals?
- Which demand patterns are too vague to act on?

Demand is market evidence. It is not yet a product recommendation.

### Input

Primary input:

```sql
demand_objects
```

Supporting input:

```sql
keyword_metrics_monthly
keyword_trend
```

Useful fields:

```text
normalized_keyword
recipient
profession
interest
pet
occasion
product
customization
style
modifier
month
search_frequency_rank
reporting_date
```

### Output

Proposed table:

```sql
demand_groups
```

Expected grain:

```text
One row per meaningful entity combination and month-aware demand pattern.
```

Core columns:

```text
demand_group_id
demand_signature
recipient
profession
interest
pet
occasion
product
customization
style
modifier
keyword_count
best_rank
avg_rank
months_present
first_month
last_month
trend_label
example_keywords
entity_completeness_score
created_at
```

### Example

Input demand objects:

```text
gifts for nurse
nurse christmas gifts
personalized nurse tumbler
funny nurse mug
```

Possible demand group:

```text
demand_signature: profession=nurse | product=tumbler,mug | occasion=christmas | customization=personalized
keyword_count: 42
best_rank: 1,240
trend_label: growing
```

Interpretation:

```text
There is repeated gift demand around nurses, with drinkware and personalization signals.
```

### Required Database Tables

Current dependencies:

```sql
demand_objects
keyword_metrics_monthly
keyword_trend
```

New Sprint 4 table:

```sql
demand_groups
```

Optional future support table:

```sql
demand_group_members
```

`demand_group_members` would map each `demand_id` to one or more
`demand_group_id` values for traceability.

## 2. Niche

### Purpose

The Niche layer converts demand groups into market segments.

Its job is to answer:

- Who is the buyer or recipient context?
- What community, identity, event, hobby, or use case defines the market?
- Is this a broad category or a specific actionable niche?
- Does the niche have enough evidence to support product research?

A niche is more strategic than a demand group. It can contain multiple demand
groups that belong to the same market context.

### Input

Primary input:

```sql
demand_groups
```

Supporting input:

```sql
demand_objects
keyword_trend
```

Useful fields:

```text
recipient
profession
interest
pet
occasion
style
modifier
keyword_count
best_rank
months_present
trend_label
entity_completeness_score
```

### Output

Proposed table:

```sql
niche_segments
```

Expected grain:

```text
One row per market niche.
```

Core columns:

```text
niche_id
niche_name
niche_type
primary_entity_type
primary_entity_value
secondary_entity_type
secondary_entity_value
demand_group_count
keyword_count
best_rank
months_present
trend_label
seasonality_label
niche_confidence
example_keywords
created_at
```

Proposed `niche_type` values:

```text
recipient
profession
interest
occasion
pet
identity
theme
seasonal
hybrid
```

### Example

Demand groups:

```text
nurse gifts
personalized nurse tumbler
funny nurse mug
nurse graduation gift
nurse christmas ornament
```

Possible niche:

```text
niche_name: nurse gifts
niche_type: profession
primary_entity_type: profession
primary_entity_value: nurse
demand_group_count: 5
keyword_count: 180
best_rank: 740
niche_confidence: high
```

Interpretation:

```text
Nurse gift demand is a durable professional niche with multiple product angles.
```

### Required Database Tables

Current dependencies:

```sql
demand_objects
keyword_trend
```

New Sprint 4 tables:

```sql
demand_groups
niche_segments
niche_demand_members
```

`niche_demand_members` should map demand groups into niches:

```text
niche_id
demand_group_id
membership_reason
confidence
```

## 3. Solution

### Purpose

The Solution layer maps demand and niches to possible product solutions.

Its job is to answer:

- What product format could satisfy this demand?
- What customization type is implied or viable?
- What style, message, or design angle fits the niche?
- Is the solution directly supported by search demand or inferred from adjacent evidence?

A solution is a product strategy candidate. It is still not an opportunity until
it is compared against internal catalog coverage and scored.

### Input

Primary input:

```sql
niche_segments
demand_groups
```

Supporting input:

```sql
demand_objects
```

Future supporting inputs:

```sql
product_rules
customization_rules
design_angle_templates
```

Useful fields:

```text
niche_name
niche_type
product
customization
style
modifier
occasion
keyword_count
best_rank
trend_label
example_keywords
```

### Output

Proposed table:

```sql
solution_candidates
```

Expected grain:

```text
One row per niche and proposed product solution.
```

Core columns:

```text
solution_id
niche_id
demand_group_id
recommended_product
recommended_customization
recommended_style
design_angle
buyer_context
recipient_context
occasion_context
solution_source
solution_fit_score
evidence_strength
example_keywords
created_at
```

Proposed `solution_source` values:

```text
explicit_keyword
entity_match
adjacent_demand
strategy_rule
manual_review
```

### Example

Niche:

```text
nurse gifts
```

Demand evidence:

```text
personalized nurse tumbler
funny nurse mug
nurse graduation gift
```

Possible solutions:

```text
recommended_product: tumbler
recommended_customization: name
recommended_style: funny
design_angle: Personalized nurse appreciation tumbler
solution_source: explicit_keyword
solution_fit_score: 88
```

```text
recommended_product: ornament
recommended_customization: year
recommended_style: sentimental
design_angle: Nurse graduation keepsake ornament
solution_source: adjacent_demand
solution_fit_score: 72
```

### Required Database Tables

Current dependencies:

```sql
demand_objects
demand_groups
niche_segments
```

New Sprint 4 table:

```sql
solution_candidates
```

Future rule/config tables:

```sql
product_rules
customization_rules
design_angle_templates
```

These future tables should describe product and customization strategy. They
should not duplicate keyword matching logic.

## 4. Internal Product Mapping

### Purpose

The Internal Product Mapping layer compares solution candidates against the
internal catalog.

Its job is to answer:

- Do we already sell products that cover this solution?
- Is current coverage strong, weak, stale, duplicated, or missing?
- Can existing assets be reused?
- What internal product, design, collection, or team should own the opportunity?

This layer connects external demand to internal execution reality.

### Input

Primary input:

```sql
solution_candidates
```

Internal inputs:

```sql
internal_catalog
internal_product_assets
internal_collections
internal_performance_metrics
```

Useful fields from `solution_candidates`:

```text
niche_id
recommended_product
recommended_customization
recommended_style
design_angle
solution_fit_score
evidence_strength
```

Useful fields from internal catalog:

```text
internal_product_id
title
product_type
recipient
profession
interest
occasion
customization_type
style
launch_date
status
sales
conversion_rate
asset_count
collection
owner
```

### Output

Proposed table:

```sql
internal_product_mapping
```

Expected grain:

```text
One row per solution candidate and internal coverage assessment.
```

Core columns:

```text
internal_mapping_id
solution_id
coverage_status
matching_product_count
best_matching_product_id
best_matching_product_title
asset_reuse_level
catalog_freshness
internal_performance_label
owner
recommended_action
mapping_confidence
mapping_notes
created_at
```

Proposed `coverage_status` values:

```text
missing
weak
covered
saturated
stale
needs_refresh
needs_differentiation
```

Proposed `recommended_action` values:

```text
create_new
refresh_existing
expand_collection
differentiate
merge_with_existing
defer
reject
```

### Example

Solution candidate:

```text
Personalized nurse appreciation tumbler
```

Internal catalog comparison:

```text
matching_product_count: 1
best_matching_product_title: Nurse Life 20oz Tumbler
catalog_freshness: stale
asset_reuse_level: medium
internal_performance_label: low_recent_activity
coverage_status: needs_refresh
recommended_action: refresh_existing
```

Interpretation:

```text
The market demand exists, but current internal coverage is stale and should be refreshed.
```

### Required Database Tables

New Sprint 4 dependency tables:

```sql
solution_candidates
internal_catalog
internal_product_assets
internal_collections
internal_performance_metrics
```

New Sprint 4 output table:

```sql
internal_product_mapping
```

If internal catalog data is not available yet, the table can still be designed
now and populated later.

## 5. Opportunity Score

### Purpose

The Opportunity Score layer prioritizes the strongest product opportunities.

Its job is to answer:

- Which opportunities deserve action first?
- Is the opportunity backed by strong demand?
- Is the niche specific and commercially useful?
- Is the solution fit clear?
- Is internal catalog coverage missing, stale, or weak?
- How confident is the recommendation?

The final opportunity should combine market evidence with internal execution
context.

### Input

Primary inputs:

```sql
demand_groups
niche_segments
solution_candidates
internal_product_mapping
```

Supporting inputs:

```sql
keyword_metrics_monthly
keyword_trend
internal_performance_metrics
review_decisions
```

### Output

Proposed table:

```sql
opportunity_scores
```

Expected grain:

```text
One row per scored solution opportunity.
```

Core columns:

```text
opportunity_id
solution_id
niche_id
demand_group_id
opportunity_name
demand_strength_score
trend_score
niche_confidence_score
solution_fit_score
catalog_gap_score
execution_fit_score
review_confidence_score
opportunity_score
priority_label
recommended_action
primary_reason
risk_flags
created_at
updated_at
```

Proposed `priority_label` values:

```text
high
medium
low
watchlist
reject
```

### Example

Opportunity:

```text
Personalized nurse appreciation tumbler refresh
```

Inputs:

```text
demand_strength_score: 84
trend_score: 71
niche_confidence_score: 90
solution_fit_score: 88
catalog_gap_score: 76
execution_fit_score: 68
review_confidence_score: 80
```

Output:

```text
opportunity_score: 81
priority_label: high
recommended_action: refresh_existing
primary_reason: Strong profession gift demand with stale internal coverage
risk_flags: seasonal_timing, needs_design_review
```

### Required Database Tables

Current dependencies:

```sql
keyword_metrics_monthly
keyword_trend
```

New Sprint 4 dependencies:

```sql
demand_groups
niche_segments
solution_candidates
internal_product_mapping
internal_performance_metrics
review_decisions
```

New Sprint 4 output table:

```sql
opportunity_scores
```

## Proposed Database Model

Sprint 4 should introduce the following analytical tables:

| Table | Purpose | Grain |
| --- | --- | --- |
| `demand_groups` | Groups demand objects into reusable demand patterns | One row per demand pattern |
| `demand_group_members` | Preserves traceability from demand objects to demand groups | One row per demand object and group |
| `niche_segments` | Defines market niches from demand groups | One row per niche |
| `niche_demand_members` | Maps demand groups into niches | One row per niche and demand group |
| `solution_candidates` | Maps niches to product and customization solutions | One row per niche solution |
| `internal_catalog` | Stores internal product records | One row per internal product |
| `internal_product_assets` | Stores reusable internal design and production assets | One row per asset |
| `internal_collections` | Groups internal products into collections | One row per collection |
| `internal_performance_metrics` | Stores internal performance observations | One row per product and period |
| `internal_product_mapping` | Maps solution candidates to internal coverage status | One row per solution mapping |
| `opportunity_scores` | Scores and prioritizes opportunities | One row per opportunity |
| `review_decisions` | Captures human review decisions | One row per reviewed item |

## Scoring Components

The Opportunity Engine should compute final opportunity priority from separate,
auditable sub-scores.

### Demand Strength Score

Measures external market signal.

Inputs:

```text
best_rank
avg_rank
keyword_count
months_present
```

High score means the demand appears frequently, ranks well, and is not based on
a single weak keyword.

### Trend Score

Measures direction and durability.

Inputs:

```text
trend_label
rank_change
months_present
first_month
last_month
```

High score means the demand is growing, durable, or present in the latest month.

### Niche Confidence Score

Measures whether the market segment is specific enough to act on.

Inputs:

```text
niche_type
entity completeness
demand_group_count
unknown entity burden
review status
```

High score means the niche has clear buyer, recipient, use-case, or identity
signals.

### Solution Fit Score

Measures whether the product and customization proposal fits the demand.

Inputs:

```text
explicit product signal
customization signal
style signal
occasion fit
design angle fit
```

High score means the solution is directly supported by keyword and entity
evidence.

### Catalog Gap Score

Measures the size of the internal opportunity gap.

Inputs:

```text
coverage_status
matching_product_count
catalog_freshness
internal performance
asset availability
```

High score means the market demand is strong and internal coverage is missing,
weak, stale, or under-differentiated.

### Execution Fit Score

Measures whether the business can act on the opportunity.

Inputs:

```text
asset reuse level
production feasibility
owner availability
launch timing
operational constraints
```

High score means the opportunity can be executed with reasonable effort and
risk.

### Review Confidence Score

Measures human and data-quality confidence.

Inputs:

```text
manual review decisions
knowledge base confidence
candidate status
entity ambiguity
data freshness
```

High score means the recommendation is supported by reviewed taxonomy and low
ambiguity.

## Opportunity Engine Output Contract

The final analytical output should be a ranked opportunity list that can support
product decisions.

Minimum useful view:

```sql
opportunity_ranked_view
```

Expected columns:

```text
opportunity_id
opportunity_name
priority_label
opportunity_score
recommended_action
niche_name
recommended_product
recommended_customization
design_angle
coverage_status
demand_strength_score
trend_score
solution_fit_score
catalog_gap_score
execution_fit_score
primary_reason
risk_flags
example_keywords
```

This view should be optimized for product research review, not raw keyword
inspection.

## Non-Goals

Sprint 4 should not:

- Build another keyword matching pipeline.
- Automatically merge review candidates into the master knowledge base.
- Mutate raw import tables.
- Treat a search term as a final opportunity.
- Score opportunities without preserving the component scores.
- Hide internal catalog assumptions inside opaque logic.

## Success Criteria

Sprint 4 architecture is complete when:

- Demand groups can be traced back to demand objects.
- Niches can be traced back to demand groups.
- Solutions can be traced back to niches and demand evidence.
- Internal product mappings can explain coverage status and recommended action.
- Opportunity scores expose their component scores.
- The final opportunity list can explain why each opportunity is high, medium,
  low, watchlist, or reject.
