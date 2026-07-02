# MRnD Research Framework

This document describes the complete Market Research and Demand Intelligence methodology for the Amazon POD market intelligence platform.

The framework separates raw search demand, market interpretation, product strategy, and execution planning into clear stages. Each stage has a specific job and produces structured outputs that can be reviewed, scored, and improved over time.

## 1. Intent Discovery

### Goal

Identify what shoppers are trying to accomplish when they search. This stage converts raw keyword language into understandable purchase intent.

### Input

- Imported Amazon Brand Analytics keywords
- Normalized keyword text
- Search frequency rank
- Reporting month and date
- Knowledge base entities such as recipient, profession, interest, occasion, product, customization, style, and modifier

### Output

- Normalized keyword records
- Matched intent entities
- Unknown entity review candidates
- Early intent groups such as gift intent, self-purchase intent, personalization intent, seasonal intent, and identity-based intent

### Key Metrics

- Keyword count by intent type
- Entity match coverage
- Unknown entity rate
- Average and minimum search frequency rank by intent
- Month coverage by intent

### Decision Criteria

- Keep intents that show repeated demand or strong rank signals
- Send unknown but frequent terms to knowledge review
- Treat vague or generic terms as low-confidence until additional entities are matched
- Prioritize intents that combine buyer, product, and occasion signals

### Future Engine

Intent Classification Engine

This engine will classify each normalized keyword into one or more intent types using rules, knowledge base matches, and eventually supervised review feedback.

## 2. Demand Discovery

### Goal

Find structured demand patterns in the market by transforming individual keywords into reusable demand objects.

### Input

- `normalized_keywords`
- Knowledge base master dictionaries
- Review dictionaries after curation
- Entity extraction results

### Output

- `demand_objects`
- Entity coverage summaries
- Demand candidates by recipient, profession, interest, pet, occasion, product, customization, style, and modifier

### Key Metrics

- Demand object count
- Search frequency rank distribution
- Entity match counts
- Month presence
- Raw keyword examples per demand object pattern
- Best rank by entity combination

### Decision Criteria

- Demand objects with clear product and buyer context are stronger than single-entity matches
- Demand objects appearing across multiple months are more durable
- High-rank keywords with missing entities should be reviewed quickly
- Multiple entities in one keyword indicate more actionable demand

### Future Engine

Demand Object Builder

This engine converts normalized keyword records into structured demand objects using knowledge base matching and review feedback.

## 3. Demand Prioritization

### Goal

Rank demand objects by commercial attractiveness so research attention goes to the strongest opportunities first.

### Input

- `demand_objects`
- `keyword_metrics_monthly`
- `keyword_trend`
- Entity coverage metrics
- Historical month availability

### Output

- Prioritized demand list
- Demand strength score
- Trend score
- Confidence score
- Review flags for ambiguous or incomplete opportunities

### Key Metrics

- Best search frequency rank
- Average search frequency rank
- Rank improvement or decline
- Months present
- Keyword count
- Entity completeness
- Seasonality concentration
- Unknown entity burden

### Decision Criteria

- Prioritize high-rank demand with clear entity structure
- Prefer improving or durable demand over one-off weak signals
- Penalize missing product or buyer context
- Promote seasonal demand only when the target launch window is relevant
- Flag declining demand for caution unless it is seasonal

### Future Engine

Demand Prioritization Engine

This engine will score demand objects using rank, trend, coverage, completeness, seasonality, and review-confidence features.

## 4. Solution Mapping

### Goal

Translate prioritized demand into possible product and design solutions.

### Input

- Prioritized demand objects
- Product knowledge base
- Style and customization knowledge
- Occasion and recipient context
- Historical product performance data when available

### Output

- Candidate product formats
- Suggested design angles
- Personalization opportunities
- Messaging themes
- Product-market fit hypotheses

### Key Metrics

- Product fit confidence
- Customization fit
- Design angle count
- Occasion fit
- Buyer-recipient clarity
- Reusability across related demand objects

### Decision Criteria

- Favor product formats explicitly present in demand
- Prefer solutions with clear buyer and use-case context
- Use customization only when keyword intent supports it
- Avoid mapping demand to products that create weak or forced relevance
- Group adjacent demand only when the same product solution can serve it

### Future Engine

Solution Mapping Engine

This engine will map demand objects to product and design solution candidates using product rules, knowledge base entities, and reviewed strategy templates.

## 5. Product Gap Analysis

### Goal

Identify where market demand exists but current product coverage is weak, missing, outdated, or poorly differentiated.

### Input

- Solution candidates
- Existing internal product catalog
- Marketplace product observations when available
- Demand priority scores
- Product attributes and design metadata

### Output

- Product gaps
- Saturation indicators
- Differentiation opportunities
- Missing product-format recommendations
- Refresh or expansion recommendations

### Key Metrics

- Demand strength versus internal coverage
- Number of matching internal products
- Product freshness
- Style coverage
- Customization coverage
- Occasion coverage
- Competitive density when available

### Decision Criteria

- High demand with no internal coverage becomes a new product gap
- High demand with stale or weak internal coverage becomes a refresh opportunity
- High demand with many similar internal products requires differentiation before action
- Low demand or unclear intent remains backlog-only

### Future Engine

Product Gap Analysis Engine

This engine will compare demand and solution candidates against internal and external product coverage to identify actionable product gaps.

## 6. Internal Mapping

### Goal

Connect external demand opportunities to internal business assets, teams, workflows, and execution constraints.

### Input

- Product gap analysis
- Internal product catalog
- Design libraries
- Brand rules
- Production capabilities
- Merchandising calendars
- Operational constraints

### Output

- Internal opportunity map
- Candidate owners
- Required assets
- Production requirements
- Launch readiness indicators
- Risk and dependency notes

### Key Metrics

- Existing asset reuse potential
- Production feasibility
- Time to launch
- Required design effort
- Brand fit
- Operational risk
- Calendar fit

### Decision Criteria

- Prefer opportunities with strong demand and low execution friction
- Escalate high-demand opportunities that require new capabilities
- Deprioritize opportunities that conflict with brand, quality, or production constraints
- Align seasonal opportunities to realistic launch timelines

### Future Engine

Internal Mapping Engine

This engine will map product gaps to internal assets, constraints, and execution paths.

## 7. Research Backlog

### Goal

Create a managed backlog of research and product opportunities that can move through review, validation, production, and measurement.

### Input

- Prioritized demand objects
- Solution mappings
- Product gaps
- Internal opportunity maps
- Human review feedback

### Output

- Research backlog items
- Status and owner fields
- Validation questions
- Recommended next action
- Opportunity history
- Review decisions

### Key Metrics

- Backlog size by status
- Opportunity score
- Confidence score
- Time in review
- Conversion from research to product action
- Rejected and deferred reason counts

### Decision Criteria

- Advance opportunities with strong demand, clear solution fit, and feasible execution
- Hold opportunities with missing evidence or unresolved review questions
- Reject opportunities with weak demand, poor fit, or unacceptable execution risk
- Revisit deferred opportunities when new demand or catalog data appears

### Future Engine

Research Backlog Engine

This engine will manage opportunity lifecycle status, review decisions, ownership, and research-to-production handoff.

## Methodology Flow

```text
Raw ABA Keywords
  -> Intent Discovery
  -> Demand Discovery
  -> Demand Prioritization
  -> Solution Mapping
  -> Product Gap Analysis
  -> Internal Mapping
  -> Research Backlog
```

The framework is deliberately staged so each engine can be built, tested, and reviewed independently.
