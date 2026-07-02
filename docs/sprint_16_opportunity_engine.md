# Sprint 16 - Opportunity Engine V1

Sprint 16 creates the first Opportunity Engine for the MRnD Demand Intelligence
Platform.

The purpose is to identify composite demands that are strong enough to review for
MRnD research. V1 uses only internal ABA-derived signals. It does not use
competition, product-gap, catalog-fit, or dashboard logic yet.

## Philosophy

```text
Search Term
  -> Intent
  -> Composite Demand
  -> Ranked Evidence
  -> Opportunity
  -> Research Backlog
```

An opportunity is not a product idea by itself. It is a ranked market demand that
deserves research.

Examples:

```text
Mom Gift
Grandma Gift
Teacher Appreciation
Christmas Nurse Gift
Dog Memorial
```

## Inputs

Tables:

```text
composite_demands
composite_keywords
demand_strength_v3
demand_profile_v2
market_nodes
intent_summary
```

`demand_strength_v3` is the primary source for composite demand strength.

`composite_keywords` preserves the keyword evidence and Search Frequency Rank.

`market_nodes` is used for limited pet enrichment when available.

`demand_profile_v2` and `intent_summary` are validated as upstream context for
the V1 opportunity layer, but V1 does not use them for product gap or catalog
fit.

## Output Tables

Sprint 16 creates only:

```text
opportunity_master
research_backlog
```

Existing composite, demand, intent, semantic, graph, and market node tables are
not modified.

## opportunity_master

Purpose:

```text
One row per composite demand, scored as an opportunity candidate.
```

Required columns:

```text
opportunity_id
demand_id
demand_name
intent
recipient
profession
interest
pet
occasion
holiday
best_rank
p25_rank
median_rank
keyword_count
active_months
trend
demand_strength_score
rank_quality_score
trend_score
active_month_score
evidence_score
competition_score
product_gap_score
internal_gap_score
opportunity_score
priority
evidence_keywords
recommendation_note
```

Reserved V2+ columns:

```text
competition_score = 0
product_gap_score = 0
internal_gap_score = 0
```

These are placeholders for later work. They are not included in the V1 score.

## research_backlog

Purpose:

```text
A review queue for MRnD research planning.
```

The backlog includes P1, P2, P3, growing, emerging, and seasonal opportunities.
Each row includes the opportunity score, priority, keyword evidence, and a
recommended next action.

## Scoring

V1 uses only internal dataset signals:

```text
opportunity_score =
  40% demand_strength_score
  20% rank_quality_score
  15% trend_score
  15% active_month_score
  10% evidence_score
```

Search Frequency Rank is the main signal. Lower rank is stronger.

`demand_strength_score` is calibrated from `demand_strength_v3.strength_score`
onto a 0-100 range within the current composite demand corpus.

`rank_quality_score` uses best rank, p25 rank, and median rank. Lower ranks
increase the score.

`trend_score` maps deterministic trend labels:

```text
growing = 100
emerging = 85
stable = 70
declining = 30
unknown = 50
```

`active_month_score` rewards demands that appear across more monthly imports.

`evidence_score` uses rank-qualified evidence such as Top 100, Top 500, Top
1000, and Top 5000 appearances. Keyword count is a minor evidence input only; it
is not the main ranking signal.

## Priority

```text
P1        opportunity_score >= 85
P2        opportunity_score >= 70
P3        opportunity_score >= 55
Watchlist otherwise
```

Priority is a research triage label, not a launch decision.

## Recommendation Notes

Examples:

```text
High demand strength and consistent ranking across months.
Growing demand with strong best-rank signal.
Seasonal opportunity; validate timing before research.
Demand has rank signal but is declining; validate before prioritizing.
Qualified demand signal; review niche, product gap, and catalog fit.
```

## CSV Exports

Output folder:

```text
data/output/opportunity/
```

Files:

```text
opportunity_master.csv
research_backlog.csv
top_100_opportunities.csv
top_growing_opportunities.csv
top_seasonal_opportunities.csv
```

## Run

From the project root:

```powershell
python src/pipeline/build_opportunity_engine.py --rebuild
```

## Safety

This sprint does not modify old tables.

This sprint does not implement dashboard logic.

This sprint does not use AI clustering.

This sprint does not use competition, product gap, or internal catalog data.

The implementation is deterministic.

## Future Expansion

Future versions can add:

```text
competition_score
product_gap_score
internal_gap_score
catalog coverage
estimated product fit
research owner/status workflow
dashboard views
```
