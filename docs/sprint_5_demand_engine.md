# Sprint 5 - Demand Engine

This sprint designs the Demand Engine for the MRnD Market Intelligence Platform.

Sprint 5 does not build the Opportunity Score. Its job is to create a durable
Demand data model that helps the MRnD team decide what to research for the next
six months.

## Goal

The Demand Engine converts interpreted search behavior into stable market demand
concepts.

It should answer:

- What recurring demand exists in the market?
- Which demand areas are growing, stable, seasonal, or declining?
- Which demands are specific enough to research?
- Which demands should connect to product solutions, customization, internal
  catalog coverage, and the research backlog?

## Demand Definition

A Demand is a recurring market need expressed by shoppers.

A Demand is not a product.

Demand describes what the shopper is looking for at the intent or market-context
level. Products are possible solutions to that demand.

Examples of Demand:

```text
Grandma Gift
Teacher Gift
Nurse Gift
Dog Mom Gift
Fishing Gift
```

These are not products because each one could be satisfied by many possible
products:

```text
Grandma Gift
  -> mug
  -> blanket
  -> ornament
  -> shirt
  -> personalized photo frame
```

```text
Teacher Gift
  -> tote bag
  -> tumbler
  -> mug
  -> shirt
  -> classroom sign
```

Demand is the research object. Product is the execution object.

## Demand Hierarchy

The Demand Engine uses this hierarchy:

```text
Intent
  ↓
Demand
  ↓
Niche
  ↓
Solution
  ↓
Customization
```

### Intent

Intent describes the shopper's broad purpose.

Examples:

```text
gift
self purchase
memorial
appreciation
seasonal celebration
personalization
```

For Sprint 5, the primary active intent is:

```text
gift
```

### Demand

Demand is the stable market need inside an intent.

Examples:

```text
Grandma Gift
Teacher Gift
Nurse Gift
Dog Mom Gift
Fishing Gift
```

Demand should be broad enough to persist across months but specific enough to
guide research.

### Niche

Niche is a more specific segment inside a Demand.

Examples:

```text
Grandma Christmas Gift
Personalized Grandma Gift
Funny Teacher Gift
Nurse Graduation Gift
Dog Mom Memorial Gift
Fishing Father's Day Gift
```

A Demand can contain many niches.

### Solution

Solution is a product-format or design-strategy answer to a Demand or Niche.

Examples:

```text
Grandma Gift -> personalized blanket
Teacher Gift -> canvas tote bag
Nurse Gift -> insulated tumbler
Dog Mom Gift -> custom pet portrait shirt
Fishing Gift -> funny fishing mug
```

### Customization

Customization describes how a solution can be personalized.

Examples:

```text
name
photo
pet name
family name
year
message
portrait
coordinates
```

Customization is not required for every solution, but it is important when
search demand explicitly includes personalization signals.

## Core Tables

Sprint 5 introduces three Demand Engine tables:

```sql
demand_master
demand_keywords
demand_summary
```

These tables should be derived from existing keyword and entity data. They should
not mutate raw import tables or master knowledge files.

## 1. demand_master

### Purpose

`demand_master` defines the canonical Demand concepts that MRnD wants to track
over time.

It is the controlled Demand taxonomy.

This table answers:

- What demand concepts exist?
- What intent does each demand belong to?
- What entity drives the demand?
- Is this demand active, under review, ignored, or retired?
- Who should review it?

### Grain

One row per canonical Demand.

### Required Columns

```text
demand_id
demand_name
intent
demand_type
primary_entity_type
primary_entity_value
secondary_entity_type
secondary_entity_value
parent_demand_id
status
priority
review_owner
review_notes
created_at
updated_at
```

### Column Definitions

`demand_id`

Stable unique identifier for the Demand.

`demand_name`

Human-readable canonical name.

Examples:

```text
Grandma Gift
Teacher Gift
Nurse Gift
Dog Mom Gift
Fishing Gift
```

`intent`

Broad shopper purpose.

Expected initial values:

```text
gift
self_purchase
memorial
appreciation
seasonal
personalization
```

`demand_type`

The main type of demand.

Expected values:

```text
recipient
profession
interest
pet
occasion
theme
hybrid
```

`primary_entity_type`

The main entity category behind the demand.

Examples:

```text
recipient
profession
interest
pet
occasion
theme
```

`primary_entity_value`

The main entity value behind the demand.

Examples:

```text
grandma
teacher
nurse
dog mom
fishing
```

`secondary_entity_type`

Optional second entity category.

Example:

```text
pet
```

`secondary_entity_value`

Optional second entity value.

Example:

```text
dog
```

`parent_demand_id`

Optional parent Demand for hierarchy.

Example:

```text
Dog Mom Gift -> parent demand: Dog Gift
```

`status`

Manual lifecycle status.

Expected values:

```text
active
review
watchlist
ignored
retired
```

`priority`

Manual priority hint before scoring.

Expected values:

```text
high
medium
low
unknown
```

`review_owner`

Person or team responsible for reviewing the Demand.

`review_notes`

Human notes explaining inclusion, exclusion, ambiguity, or strategy.

`created_at`

Demand creation timestamp.

`updated_at`

Last update timestamp.

### Examples

```text
demand_id: DMD-000001
demand_name: Grandma Gift
intent: gift
demand_type: recipient
primary_entity_type: recipient
primary_entity_value: grandma
secondary_entity_type:
secondary_entity_value:
parent_demand_id:
status: active
priority: high
```

```text
demand_id: DMD-000002
demand_name: Teacher Gift
intent: gift
demand_type: profession
primary_entity_type: profession
primary_entity_value: teacher
secondary_entity_type:
secondary_entity_value:
parent_demand_id:
status: active
priority: high
```

```text
demand_id: DMD-000003
demand_name: Dog Mom Gift
intent: gift
demand_type: hybrid
primary_entity_type: recipient
primary_entity_value: dog mom
secondary_entity_type: pet
secondary_entity_value: dog
parent_demand_id:
status: review
priority: medium
```

## 2. demand_keywords

### Purpose

`demand_keywords` maps search keywords to canonical Demand records.

This table provides traceability from Demand back to the search terms that prove
the demand exists.

It answers:

- Which keywords support each Demand?
- Which month did each keyword appear?
- How strong was the rank signal?
- Was the keyword mapped by rule, manual review, or another method?

### Grain

One row per Demand and keyword observation.

The same normalized keyword can appear in multiple months and can support more
than one Demand if manual review allows it.

### Required Columns

```text
demand_keyword_id
demand_id
demand_id_confidence
demand_match_method
demand_match_reason
demand_id_review_status
demand_object_id
normalized_keyword
raw_keyword
month
reporting_date
search_frequency_rank
source_file
recipient
profession
interest
pet
occasion
product
customization
style
modifier
created_at
```

### Column Definitions

`demand_keyword_id`

Stable unique identifier for the Demand-keyword link.

`demand_id`

Foreign key to `demand_master`.

`demand_id_confidence`

Confidence that the keyword belongs to the Demand.

Expected values:

```text
high
medium
low
```

`demand_match_method`

How the keyword was linked to the Demand.

Expected values:

```text
entity_rule
manual_review
knowledge_base
hybrid_rule
backfill
```

`demand_match_reason`

Short explanation of the match.

Examples:

```text
recipient=grandma and intent=gift
profession=teacher and normalized_keyword contains gift
interest=fishing and intent=gift
```

`demand_id_review_status`

Review status for the link.

Expected values:

```text
unreviewed
approved
rejected
needs_review
```

`demand_object_id`

Source `demand_objects.demand_id` when available.

`normalized_keyword`

Normalized keyword text.

`raw_keyword`

Original keyword text.

`month`

Reporting month.

`reporting_date`

ABA reporting date.

`search_frequency_rank`

ABA rank for the keyword observation. Lower rank means stronger demand.

`source_file`

Source ABA file when available.

Entity columns:

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

These preserve the interpreted keyword context at the time the Demand mapping was
created.

`created_at`

Timestamp when the Demand-keyword link was created.

### Examples

```text
demand_id: DMD-000001
normalized_keyword: grandma christmas gift
raw_keyword: grandma christmas gifts
month: 2025-12
search_frequency_rank: 8,420
demand_match_method: entity_rule
demand_match_reason: recipient=grandma and intent=gift
```

```text
demand_id: DMD-000002
normalized_keyword: teacher appreciation gift
raw_keyword: teacher appreciation gifts
month: 2025-05
search_frequency_rank: 1,240
demand_match_method: entity_rule
demand_match_reason: profession=teacher and intent=gift
```

```text
demand_id: DMD-000005
normalized_keyword: fishing gifts for men
raw_keyword: fishing gifts for men
month: 2025-12
search_frequency_rank: 6,300
demand_match_method: entity_rule
demand_match_reason: interest=fishing and intent=gift
```

## 3. demand_summary

### Purpose

`demand_summary` stores monthly and rolling metrics for each Demand.

This is the main table MRnD should use to decide what to research over the next
six months.

It answers:

- Which Demands are strongest right now?
- Which Demands are growing?
- Which Demands are seasonal?
- Which Demands have enough evidence to research?
- Which Demands need knowledge base review before product research?

### Grain

One row per Demand per summary period.

The initial period should be monthly:

```text
demand_id + month
```

Future summary periods can include:

```text
rolling_3_month
rolling_6_month
year_to_date
seasonal_window
```

### Required Columns

```text
demand_summary_id
demand_id
summary_period
month
keyword_count
distinct_keyword_count
best_rank
avg_rank
median_rank
rank_score
months_present
first_seen_month
last_seen_month
rank_change
trend_label
seasonality_label
top_products
top_customizations
top_occasions
top_styles
top_modifiers
example_keywords
coverage_flags
research_readiness
recommended_research_action
created_at
updated_at
```

### Column Definitions

`demand_summary_id`

Stable unique identifier for the summary row.

`demand_id`

Foreign key to `demand_master`.

`summary_period`

The aggregation period.

Expected initial values:

```text
monthly
rolling_3_month
rolling_6_month
```

`month`

Month represented by the summary row. For rolling periods, this is the ending
month of the window.

`keyword_count`

Number of keyword observations linked to the Demand.

`distinct_keyword_count`

Number of distinct normalized keywords linked to the Demand.

`best_rank`

Best observed ABA rank in the period.

`avg_rank`

Average ABA rank in the period.

`median_rank`

Median ABA rank in the period.

`rank_score`

Normalized strength score derived from rank. This is not the Opportunity Score.
It is only a demand-strength feature.

`months_present`

Number of months where the Demand has appeared.

`first_seen_month`

First observed month for the Demand.

`last_seen_month`

Most recent observed month for the Demand.

`rank_change`

Change in rank over the comparison window. Negative means rank improved.

`trend_label`

Demand trend.

Expected values:

```text
emerging
growing
stable
declining
seasonal
insufficient_data
```

`seasonality_label`

Seasonal behavior.

Expected values:

```text
evergreen
q4_peak
spring_peak
summer_peak
back_to_school
event_driven
unknown
```

`top_products`

Most common product entities connected to the Demand.

Example:

```text
mug|tumbler|blanket|ornament
```

`top_customizations`

Most common customization entities connected to the Demand.

Example:

```text
name|photo|message
```

`top_occasions`

Most common occasion entities connected to the Demand.

Example:

```text
christmas|birthday|mother's day
```

`top_styles`

Most common style entities connected to the Demand.

Example:

```text
funny|cute|vintage
```

`top_modifiers`

Most common modifier entities connected to the Demand.

Example:

```text
personalized|custom|unique
```

`example_keywords`

Representative raw keyword examples.

`coverage_flags`

Data quality and coverage flags.

Examples:

```text
missing_product_signal
missing_customization_signal
low_keyword_count
needs_knowledge_review
strong_seasonality
```

`research_readiness`

Whether the Demand is ready for research.

Expected values:

```text
ready
needs_review
watchlist
not_ready
```

`recommended_research_action`

Recommended next research step.

Expected values:

```text
research_now
monitor_next_month
expand_knowledge_base
map_products
review_internal_catalog
defer
ignore
```

`created_at`

Summary creation timestamp.

`updated_at`

Last update timestamp.

### Examples

```text
demand_id: DMD-000001
demand_name: Grandma Gift
summary_period: rolling_6_month
month: 2025-12
keyword_count: 1,840
distinct_keyword_count: 620
best_rank: 320
trend_label: growing
seasonality_label: q4_peak
top_products: blanket|mug|ornament
top_customizations: photo|name|message
research_readiness: ready
recommended_research_action: research_now
```

```text
demand_id: DMD-000002
demand_name: Teacher Gift
summary_period: rolling_6_month
month: 2025-12
keyword_count: 2,300
distinct_keyword_count: 760
best_rank: 180
trend_label: seasonal
seasonality_label: back_to_school
top_products: tote bag|mug|tumbler
top_customizations: name|message
research_readiness: ready
recommended_research_action: map_products
```

```text
demand_id: DMD-000005
demand_name: Fishing Gift
summary_period: rolling_6_month
month: 2025-12
keyword_count: 940
distinct_keyword_count: 310
best_rank: 1,120
trend_label: stable
seasonality_label: evergreen
top_products: mug|shirt|tumbler
top_customizations: name
research_readiness: ready
recommended_research_action: review_internal_catalog
```

## Monthly Update Workflow

The Demand Engine should refresh after every monthly ABA import.

### Step 1. Import ABA Data

Run the existing import workflow for the new month.

Input:

```text
data/raw/*.csv
```

Output:

```sql
raw_keywords
import_history
```

### Step 2. Refresh Research Tables

Refresh the normalized keyword and trend tables.

Output:

```sql
normalized_keywords
keyword_metrics_monthly
keyword_trend
```

### Step 3. Refresh Demand Objects

Refresh the interpreted keyword layer.

Output:

```sql
demand_objects
knowledge/review/unknown_*.csv
```

This step still performs entity extraction. Sprint 5 does not replace or
duplicate that matching pipeline.

### Step 4. Review Knowledge Gaps

Review unknown entities and candidate files before updating Demand mappings.

Inputs:

```text
knowledge/review/unknown_*.csv
knowledge/review/*_candidates.csv
```

Manual output:

```text
knowledge/master/*.csv
```

Only reviewed and approved taxonomy changes should be added to master knowledge
files.

### Step 5. Update demand_master

Create or update canonical Demand records.

Rules:

- New Demand records require review.
- Existing Demand records keep stable `demand_id` values.
- Retired or ignored Demands remain in the table for history.
- Demand names should be human-readable and stable.
- Demand should not be created for every keyword variation.

Examples:

```text
gift for grandma -> Grandma Gift
teacher appreciation gift -> Teacher Gift
fishing gifts for men -> Fishing Gift
```

### Step 6. Rebuild demand_keywords

Map current keyword observations to canonical Demands.

Rules:

- Preserve month-level keyword evidence.
- Preserve raw keyword examples.
- Preserve entity values used during mapping.
- Mark low-confidence mappings as `needs_review`.
- Allow a keyword to map to more than one Demand only when review policy allows
  it.

### Step 7. Rebuild demand_summary

Aggregate Demand metrics by month and rolling windows.

Required outputs:

```text
monthly summary
rolling 3 month summary
rolling 6 month summary
```

The six-month view should be the main planning view for MRnD research decisions.

### Step 8. Produce Demand Research Review

Create a ranked review view for the MRnD team.

This is not the Opportunity Score. It is a Demand research planning view.

Recommended columns:

```text
demand_id
demand_name
intent
demand_type
keyword_count
distinct_keyword_count
best_rank
trend_label
seasonality_label
top_products
top_customizations
research_readiness
recommended_research_action
example_keywords
```

The team uses this view to decide what to research over the next six months.

## Demand Connections

## Demand to Products

Demand connects to products through observed product signals and future solution
mapping.

Example:

```text
Demand: Grandma Gift
Observed products: blanket, mug, ornament, shirt
Possible product research: personalized blanket, grandma mug, photo ornament
```

Demand does not become a product. Demand provides evidence for which product
formats may be worth researching.

Useful bridge fields:

```text
demand_id
product
keyword_count
best_rank
example_keywords
```

Future table:

```sql
demand_product_signals
```

Potential columns:

```text
demand_id
product
keyword_count
best_rank
months_present
example_keywords
```

## Demand to Customization

Demand connects to customization through explicit personalization signals.

Example:

```text
Demand: Dog Mom Gift
Observed customization: pet name, portrait, photo
Research direction: custom pet portrait shirt or personalized dog mom mug
```

Useful bridge fields:

```text
demand_id
customization
keyword_count
best_rank
example_keywords
```

Future table:

```sql
demand_customization_signals
```

Potential columns:

```text
demand_id
customization
keyword_count
best_rank
months_present
example_keywords
```

## Demand to Internal Catalog

Demand connects to the internal catalog after product and customization signals
are understood.

Example:

```text
Demand: Teacher Gift
Observed product signal: tote bag
Observed customization signal: name
Internal catalog question: Do we already have personalized teacher tote bags?
```

The Demand Engine should not decide final opportunity priority. It should
prepare the evidence needed for catalog mapping.

Useful bridge fields:

```text
demand_id
product
customization
style
occasion
research_readiness
recommended_research_action
```

Future tables:

```sql
internal_catalog
internal_product_mapping
```

## Demand to Research Backlog

Demand should feed the research backlog when it is ready for human research.

Example backlog item:

```text
Demand: Nurse Gift
Research question: Which nurse gift product formats should MRnD prioritize for the next six months?
Evidence: strong rank, recurring monthly demand, product signals for tumbler and mug, customization signal for name
Status: new
Owner: research
```

Backlog items should not be created for every Demand automatically. They should
be created when `demand_summary.research_readiness` and manual review indicate
that research is worthwhile.

Future table:

```sql
research_backlog
```

Demand-related columns:

```text
backlog_id
demand_id
research_question
evidence_summary
status
owner
priority_hint
created_at
updated_at
```

## Six-Month Research Planning View

The final Demand Engine planning output should help MRnD choose research targets
for the next six months.

Proposed view:

```sql
demand_research_planning_view
```

Expected columns:

```text
demand_id
demand_name
intent
demand_type
summary_period
month
keyword_count
distinct_keyword_count
best_rank
trend_label
seasonality_label
top_products
top_customizations
top_occasions
research_readiness
recommended_research_action
coverage_flags
example_keywords
```

Recommended filters:

```text
summary_period = rolling_6_month
research_readiness in ('ready', 'needs_review', 'watchlist')
status in ('active', 'review', 'watchlist')
```

Recommended review order:

1. High rank and growing Demands.
2. High rank seasonal Demands for the next launch window.
3. Demands with strong product and customization signals.
4. Demands with strong market evidence but weak knowledge coverage.
5. Watchlist Demands that need another month of evidence.

## Non-Goals

Sprint 5 should not:

- Build the Opportunity Score.
- Treat Demand as a product.
- Create a new keyword matching pipeline.
- Automatically merge review candidates into `knowledge/master/`.
- Automatically create backlog items for every Demand.
- Mutate raw import tables.
- Hide demand-to-keyword traceability.

## Success Criteria

Sprint 5 architecture is complete when:

- Demand is clearly defined as market need, not product.
- Demand hierarchy is documented from Intent through Customization.
- `demand_master`, `demand_keywords`, and `demand_summary` have required columns.
- Demand examples are clear enough for manual review.
- Monthly ABA update workflow is defined.
- Demand connections to Products, Customization, Internal Catalog, and Research
  Backlog are explicit.
- The MRnD team has a six-month planning view for choosing research priorities.
