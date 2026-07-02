# Sprint 14 - Intent Layer Refactor

Sprint 14 adds an Intent Layer before demand and market node construction.

The goal is to stop treating labels like `Boy Gift`, `Grandma Gift`, and
`Teacher Gift` as the demand itself. Gift is an intent. Boy, grandma, teacher,
pet, and interest are demand dimensions.

## Correct Hierarchy

```text
Intent
  -> Recipient / Profession / Pet / Interest
  -> Niche
  -> Product
  -> Customization
  -> Market Opportunity
```

Examples:

```text
soccer gifts for boys

intent = gift
recipient = boy
interest = soccer
```

```text
personalized fishing gifts for grandpa

intent = gift
recipient = grandpa
interest = fishing
customization = personalized
```

```text
teacher appreciation gifts

intent = appreciation
profession = teacher
```

```text
christmas gifts for grandma

intent = gift
holiday = christmas
recipient = grandma
```

## Inputs

Tables:

```text
demand_objects
demand_master_v2
market_nodes
keyword_entity_edges
```

`demand_objects` supplies keyword-level semantic fields.

`keyword_entity_edges` verifies that intent market nodes are backed by graph
entities.

`market_nodes` is read as legacy context only. Sprint 14 does not modify it.

## Output Tables

Sprint 14 creates only:

```text
intent_keywords
intent_summary
intent_market_nodes
```

Existing demand, graph, semantic relationship, and market node tables are not
modified.

## intent_keywords

Purpose:

```text
Preserve every original keyword row with its detected intent and market dimensions.
```

Key columns:

```text
keyword_id
raw_keyword
normalized_keyword
month
search_frequency_rank
reporting_date
intent
intent_rule
primary_audience_type
primary_audience_value
niche_type
niche_value
recipient
profession
pet
interest
theme
lifestyle
product
customization
style
holiday
occasion
age_group
gender
```

## Intent Types

Supported intent values:

```text
gift
personalized
matching
memorial
appreciation
birthday
christmas
retirement
graduation
wedding
anniversary
housewarming
sympathy
decor
apparel
unknown
```

## Intent Priority

Intent is detected before demand dimensions.

Priority:

```text
appreciation
memorial
matching
gift
personalized
birthday
christmas
retirement
graduation
wedding
anniversary
housewarming
sympathy
decor
apparel
unknown
```

This means:

```text
teacher appreciation gifts -> appreciation
christmas gifts for grandma -> gift
personalized fishing gifts for grandpa -> gift
custom fishing shirt -> personalized
christmas decorations -> christmas
```

## Demand Dimensions

Primary audience is selected deterministically:

```text
profession
recipient
pet
interest
```

Niche is selected from:

```text
interest
theme
lifestyle
```

If interest is already the primary audience, it is not repeated as the niche.

## intent_summary

Purpose:

```text
Rank intent types using ABA Search Frequency Rank.
```

Important metrics:

```text
keyword_count
distinct_keyword_count
best_rank
p25_rank
median_rank
top100_count
top1000_count
average_rank
active_months
example_keywords
```

Search Frequency Rank is the main strength signal. Lower rank is stronger.

## intent_market_nodes

Purpose:

```text
Build intent-aware market nodes from keyword evidence.
```

Market node identity:

```text
intent + primary audience + niche attribute
```

Examples:

```text
gift + boy + soccer
gift + grandma + fishing
appreciation + teacher
matching + family
```

Product and customization are not identity fields. They are context fields for
future solution and opportunity layers.

## CSV Exports

Reports export to:

```text
data/output/intent_layer/
```

Files:

```text
intent_keywords.csv
intent_summary.csv
intent_market_nodes.csv
top_intent_recipient.csv
top_intent_niche.csv
top_intent_product.csv
```

## CLI

Run:

```powershell
python src/pipeline/build_intent_layer.py --rebuild
```

Without `--rebuild`, the script exits if intent layer tables already exist.

## Safety

Sprint 14 does not:

- modify old demand tables
- modify old market node tables
- modify knowledge graph tables
- build Opportunity Score
- use AI clustering
- treat product as demand
- treat customization as demand

The layer is deterministic and can be rebuilt from current local tables.

## Future Use

Future market opportunity modeling should use:

```text
intent_keywords
intent_market_nodes
semantic_relationships
market_nodes
```

The next opportunity layer can then combine:

```text
intent strength
audience strength
niche strength
product fit
customization fit
internal catalog fit
```

Sprint 14 stops before Opportunity Score.
