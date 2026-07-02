# Sprint 17 - Demand Segment Engine

Sprint 17 adds the Demand Segment layer.

The goal is to stop treating only top-level demands as opportunities. A demand
such as `Mom Gift` is useful, but MRnD research usually needs the next level of
specificity, such as `Fishing Mom Gift`, `Dog Mom Gift`, or `Christmas Mom Gift`.

## Hierarchy

```text
Intent
  -> Demand
  -> Demand Segment
  -> Solution
  -> Customization
  -> Opportunity
```

## Definitions

Demand:

```text
A long-term market need.
```

Examples:

```text
Mom Gift
Dad Gift
Teacher Gift
Grandma Gift
Dog Memorial
Camping Gift
Coffee Lover
Fishing
Christmas Decor
```

Demand Segment:

```text
A specialization of one parent demand created by adding exactly one semantic dimension.
```

Examples:

```text
Fishing Mom Gift
Coffee Mom Gift
Dog Mom Gift
Nurse Mom Gift
Christmas Mom Gift
Teacher Appreciation Gift
Camping Dad Gift
Golf Grandpa Gift
```

Product and customization are excluded from this layer.

Good:

```text
Fishing Mom Gift
```

Bad:

```text
Fishing Mom Blanket
Fishing Mom Photo Blanket
```

## Physical Inputs

Requested conceptual inputs:

```text
demand_master_v3
composite_demands
semantic_relationships
entity_master
market_nodes
intent_layer
knowledge_graph
```

Current physical table mapping:

```text
demand_master_v3 -> demand_strength_v3 when demand_master_v3 is not present
intent_layer     -> intent_keywords
knowledge_graph  -> keyword_entity_edges
```

The current database does not contain a physical `demand_master_v3` table, so
the builder uses `demand_strength_v3` as the V3 demand source.

## Output Tables

Sprint 17 creates only:

```text
demand_segments
segment_keywords
```

Previous tables are not modified.

## demand_segments

Purpose:

```text
One row per demand segment.
```

Columns:

```text
segment_id
parent_demand_id
parent_demand
segment_name
intent
recipient
profession
interest
pet
holiday
occasion
theme
lifestyle
keyword_count
best_rank
median_rank
active_months
trend
segment_strength
evidence_keywords
```

## segment_keywords

Purpose:

```text
Preserve the search-term evidence behind each demand segment.
```

Key columns:

```text
segment_id
parent_demand_id
parent_demand
segment_name
intent
segment_dimension
segment_value
raw_keyword
normalized_keyword
month
search_frequency_rank
```

## Segment Rules

A segment inherits exactly one parent demand.

A segment adds exactly one of:

```text
interest
profession
pet
holiday
occasion
theme
lifestyle
recipient refinement
```

Product and customization are not segment dimensions.

Examples:

```text
Parent: Mom Gift
Segments:
Fishing Mom Gift
Coffee Mom Gift
Dog Mom Gift
Camping Mom Gift
Teacher Mom Gift
```

```text
Parent: Grandpa Gift
Segments:
Golf Grandpa Gift
Fishing Grandpa Gift
Retired Grandpa Gift
```

```text
Parent: Teacher Gift
Segments:
Math Teacher Gift
Music Teacher Gift
Science Teacher Gift
Teacher Appreciation Gift
```

## Parent Demand Selection

Parent demands come from the V3 demand source.

A parent demand must be a top-level demand with one core semantic dimension:

```text
recipient
profession
pet
interest
```

Rows that already contain holiday, occasion, theme, or lifestyle are treated as
segment-level rows, not parent rows.

`apparel` and `personalized` parent intents are excluded from this layer because
they belong closer to Solution and Customization.

## Evidence Rules

Segment evidence is built from keyword-level intent evidence.

Rows are excluded when they contain:

```text
product
customization
```

This keeps product phrases such as `blanket`, `mug`, or `shirt` out of the
Demand Segment layer.

## Scoring

`segment_strength` reuses the Demand Strength V3 rank signals:

```text
best_rank
p25_rank
median_rank
active_months
```

It uses the same rank-based weighting pattern as Demand Strength V3:

```text
45% best rank
30% p25 rank
15% median rank
10% active months
```

Search Frequency Rank remains the primary signal. Lower rank is stronger.

Keyword count is retained as supporting evidence, not the main scoring signal.

## Validation

The builder validates:

```text
Every segment has one parent demand.
No duplicate segment names exist.
No product or customization segment dimensions are generated.
```

## CSV Exports

Output folder:

```text
data/output/demand_segments/
```

Files:

```text
demand_segments.csv
segment_keywords.csv
top_200_segments.csv
```

`top_200_segments.csv` is sorted by:

```text
segment_strength
best_rank
active_months
trend
```

## Run

From the project root:

```powershell
python src/pipeline/build_demand_segments.py --rebuild
```

## Safety

This sprint only creates the new Demand Segment layer.

It does not modify previous demand, intent, graph, semantic, composite,
opportunity, or research tables.

It does not build product solutions.

It does not build customization logic.

It does not use AI clustering.
