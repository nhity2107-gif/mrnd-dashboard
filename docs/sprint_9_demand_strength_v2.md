# Sprint 9 - Demand Strength V2

Sprint 9 upgrades demand ranking from keyword-count led analysis to
rank-based demand strength.

Amazon Brand Analytics Search Frequency Rank is the core demand signal.
Lower rank means stronger demand.

## Goal

Build a deterministic analytical layer that answers:

```text
Which demands are strongest by ABA search rank?
Which demands are improving or declining by rank?
Which contextual dimensions surround each demand?
```

This sprint does not build Opportunity Score.

## Inputs

The V2 builder reads and validates:

```text
demand_objects
normalized_keywords
keyword_metrics_monthly
```

`demand_objects` is the primary semantic source because it already contains:

```text
normalized_keyword
search_frequency_rank
month
reporting_date
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
product
customization
```

## Demand Definition

A Demand is:

```text
Intent + Primary Recipient / Profession / Pet Role / Interest Identity
```

Examples:

```text
Grandma Gift
Teacher Gift
Nurse Gift
Dog Mom Gift
Best Friend Gift
Fishing Gift
```

Product is not demand.

Examples:

```text
Grandma Gift -> mug, blanket, ornament
Teacher Gift -> tumbler, tote bag, mug
Dog Mom Gift -> shirt, mug, ornament
```

Products belong to the Solution Layer and are stored in
`demand_profile_v2`, not in `demand_master_v2`.

## Grouping Rules

The grouping is deterministic.

Primary identity priority:

```text
pet role
recipient
profession
interest identity
unclassified
```

Pet role is evaluated first so phrases like `dog mom gift` become
`Dog Mom Gift` instead of a generic `Mom Gift`.

Teacher and nurse terms are treated as professions when detected.

Products and customization are ignored when creating the demand key.

Unclassified rows are retained for audit and keyword traceability, but they
are not scored as valid demand opportunities and are excluded from top-demand
reports.

Examples:

```text
gift for grandma
grandma gifts
gift for nana
grandma christmas gifts

-> Grandma Gift
```

```text
teacher christmas gift
teacher appreciation gift
teacher gifts

-> Teacher Gift
```

```text
gift for dog mom
dog mom gifts

-> Dog Mom Gift
```

```text
fishing gifts
fishing present

-> Fishing Gift
```

## Output Tables

Sprint 9 creates only V2 tables:

```text
demand_master_v2
demand_keywords_v2
demand_monthly_v2
demand_profile_v2
```

The older Sprint 8 tables are not modified:

```text
demand_master
demand_keywords
demand_monthly
```

## demand_master_v2

One row per demand.

Columns:

```text
demand_id
demand_name
primary_type
primary_value
primary_intent
best_rank
p10_rank
p25_rank
median_rank
top_100_count
top_500_count
top_1000_count
top_5000_count
top_50000_count
active_months
first_month
last_month
rank_momentum
stability_score
demand_strength_score
trend_label
```

This table does not store fixed interest, theme, holiday, product, or
customization values. Those dimensions can vary inside one demand and are
stored in `demand_profile_v2`.

## demand_keywords_v2

Traceability from every ABA keyword row back to one demand.

Columns:

```text
demand_id
raw_keyword
normalized_keyword
month
search_frequency_rank
reporting_date
```

## demand_monthly_v2

Month-level rank aggregation.

Columns:

```text
demand_id
month
best_rank
p10_rank
p25_rank
median_rank
top_100_count
top_500_count
top_1000_count
top_5000_count
keyword_count
```

`keyword_count` is retained for diagnostics, but it is not the main ranking
metric.

## demand_profile_v2

Context dimensions around each demand.

Columns:

```text
demand_id
dimension
value
keyword_count
best_rank
top_1000_count
```

Dimensions:

```text
holiday
occasion
interest
theme
lifestyle
age_group
gender
product
customization
```

## Demand Strength Score

The score is rank-based.

Formula:

```text
35% best_rank_score
20% p25_rank_score
15% top_1000_coverage_score
15% rank_momentum_score
10% stability_score
5% keyword_diversity_score
```

Rank scores use logarithmic normalization:

```text
rank 1 -> strongest
larger ranks -> progressively weaker
```

`keyword_diversity_score` is included only as a small supporting signal.
It must not dominate demand ranking.

## Trend Logic

Trend uses monthly `best_rank` and `p25_rank`.

Labels:

```text
growing
declining
stable
emerging
```

Rules:

```text
rank improves across months -> growing
rank worsens across months -> declining
little movement -> stable
appears only in late months -> emerging
```

Positive `rank_momentum` means the demand improved because the rank moved
lower.

## CSV Reports

Reports export to:

```text
data/output/demand_v2/
```

Files:

```text
demand_master_v2.csv
demand_keywords_v2.csv
demand_monthly_v2.csv
demand_profile_v2.csv
top_demands_by_strength.csv
top_demands_by_best_rank.csv
top_growing_demands.csv
```

Top-demand reports exclude unclassified rows because unclassified search terms
do not meet the Demand definition.

## CLI

Run:

```powershell
python src/pipeline/build_demand_strength_v2.py --rebuild
```

Without `--rebuild`, the script exits if V2 tables already exist.

## Safety

Sprint 9 does not:

- modify old demand tables
- modify `demand_objects`
- modify import logic
- modify taxonomy matching logic
- build Opportunity Score
- use AI clustering
- use product names as demand identity
- use customization as demand identity

## Future Opportunity Engine

Demand Strength V2 feeds the future Opportunity Engine:

```text
demand_master_v2
  -> demand_profile_v2
  -> solution mapping
  -> internal catalog mapping
  -> opportunity score
  -> research backlog
```

Opportunity Score should combine demand strength with solution fit,
customization fit, competition, production feasibility, and MRnD catalog fit.
