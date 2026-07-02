# Sprint 8 - Demand Engine V1

Sprint 8 moves the MRnD Demand Intelligence Platform from keyword-centric
analysis to demand-centric analysis.

The Demand Engine aggregates many search terms into one market demand.

## Demand Philosophy

A Demand is a market need, not a keyword and not a product.

Examples:

```text
Grandma Gift
Teacher Gift
Nurse Gift
Dog Mom Gift
Best Friend Gift
Fishing Grandpa Gift
```

Products belong to the Solution Layer.

Examples:

```text
Grandma Gift -> mug, blanket, ornament
Teacher Gift -> tote bag, tumbler, mug
Dog Mom Gift -> shirt, mug, ornament
```

The Demand Engine should answer:

- What market need is represented by this keyword?
- Which keywords belong to the same demand?
- How strong is this demand by rank and frequency?
- Is the demand growing, declining, emerging, or stable?

It should not decide final product opportunities or build Opportunity Score.

## Input Tables

The engine reads:

```sql
normalized_keywords
keyword_metrics_monthly
keyword_trend
demand_objects
```

The primary source is `demand_objects`, because it already contains interpreted
semantic entities.

## Output Tables

The engine creates only these new tables:

```sql
demand_master
demand_keywords
demand_monthly
```

Existing source tables are not modified.

## Demand ID

Demand IDs are generated deterministically:

```text
DM000001
DM000002
DM000003
```

IDs are assigned by demand strength order:

1. best search rank
2. keyword count
3. demand key

## Demand Definition

Demand is built from:

```text
Intent + Primary Recipient
```

The engine uses deterministic priority rules to find the primary demand identity:

1. recipient
2. profession
3. pet role
4. interest identity
5. unclassified fallback

Products and customization are ignored when creating demand identity.

## Grouping Rules

### Grandma Gift

These keywords group into one demand:

```text
gift for grandma
grandma gifts
gift for nana
grandma christmas gifts
```

Output:

```text
Grandma Gift
```

Holiday context is retained in semantic fields, but it does not split the demand.

### Teacher Gift

These keywords group into one demand:

```text
teacher christmas gift
teacher appreciation gift
teacher gifts
```

Output:

```text
Teacher Gift
```

Profession is used when recipient is missing.

### Nurse Gift

These keywords group into one demand:

```text
gift for nurse
nurse appreciation gifts
nurse christmas gifts
```

Output:

```text
Nurse Gift
```

### Fishing Grandpa Gift

These keywords can form a recipient demand with an interest qualifier:

```text
fishing gifts for grandpa
grandpa fishing gift
```

Output:

```text
Fishing Grandpa Gift
```

The primary identity is still the recipient. The interest becomes a demand
qualifier because it is not a product or customization.

## demand_master

One row per demand.

Columns:

```text
demand_id
demand_name
recipient
profession
interest
pet
occasion
holiday
theme
lifestyle
age_group
gender
primary_intent
keyword_count
best_search_rank
avg_search_rank
first_month
last_month
active_months
growth_percent
trend_label
```

Purpose:

```text
Canonical demand list with metrics and semantic context.
```

## demand_keywords

Every keyword belongs to one demand.

Columns:

```text
demand_id
raw_keyword
normalized_keyword
month
search_frequency_rank
```

Purpose:

```text
Traceability from demand back to keyword evidence.
```

## demand_monthly

Aggregates demand metrics by month.

Columns:

```text
demand_id
month
keyword_count
best_rank
avg_rank
```

Purpose:

```text
Month-level demand tracking for trend and planning.
```

## Reports

CSV reports are exported to:

```text
data/output/demand/
```

Files:

```text
demand_master.csv
demand_keywords.csv
demand_monthly.csv
top_demands.csv
```

`top_demands.csv` is sorted by:

1. best rank
2. keyword count
3. trend label

## Trend Logic

Trend is deterministic.

Initial labels:

```text
emerging
growing
stable
declining
```

The engine uses first-month and last-month keyword counts plus keyword trend
signals from `keyword_trend`.

This is not Opportunity Score.

## CLI

Run:

```powershell
python src/pipeline/build_demand_engine.py --rebuild
```

Without `--rebuild`, the script protects existing demand tables and exits if
they already exist.

## Future Opportunity Engine

The Demand Engine feeds future opportunity analysis.

Expected future flow:

```text
demand_master
  -> demand-to-product solution mapping
  -> internal catalog mapping
  -> opportunity scoring
  -> research backlog
```

Sprint 8 stops at demand-centric tables and reports.

## Non-Goals

Sprint 8 does not:

- implement Opportunity Score
- implement AI clustering
- create product solutions
- use product names as demand identity
- use customization as demand identity
- modify previous tables
- modify the import pipeline
- modify the research model

## Success Criteria

Sprint 8 is complete when:

- `demand_master` exists
- `demand_keywords` exists
- `demand_monthly` exists
- every keyword row has one `demand_id`
- product and customization are excluded from demand identity
- demand reports are exported
- the MRnD team can review top demands for six-month research planning
