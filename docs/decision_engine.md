# Decision Engine

This document designs the MRnD Decision Engine for Amazon Personalized POD.

It is design only. It does not define implementation code, CSV exports,
database tables, pipelines, dashboard changes, or scoring formulas.

## Purpose

The Decision Engine transforms existing intelligence into actionable research
decisions.

It answers:

```text
Should MRnD research this niche?
Which child niche should be researched first?
Which product should be tested?
Which customization should be used?
How many listings should be created?
How difficult is execution?
How scalable is the opportunity?
How competitive is the market?
When should MRnD launch?
How much investment is required?
Should this create a new portfolio or expand an existing one?
What is the final recommendation?
```

The engine should not only rank opportunities. It should explain what action the
MRnD leader should take next.

## Decision Flow

The decision flow is:

```text
Market
  -> Demand
  -> Segment
  -> Competition
  -> Seasonality
  -> Product Fit
  -> Customization Fit
  -> Portfolio
  -> Decision
  -> Execution
```

Each stage reduces uncertainty.

```text
Market answers: Is the parent space worth attention?
Demand answers: Is there measurable buyer demand?
Segment answers: Which specific niche is actionable?
Competition answers: How hard will ranking and differentiation be?
Seasonality answers: When should research and launch happen?
Product Fit answers: What should be sold?
Customization Fit answers: How should it be personalized?
Portfolio answers: Is this new, expansion, or irrelevant?
Decision answers: What should MRnD do?
Execution answers: What should be built first?
```

## Inputs

The Decision Engine should consume existing intelligence layers conceptually,
not raw search terms directly.

Input categories:

```text
Market Intelligence
Demand Intelligence
Opportunity Scoring
Portfolio Intelligence
Research Knowledge Graph
Seasonality Intelligence
Product Fit Intelligence
Customization Fit Intelligence
Winner Evidence
```

The engine should prefer evidence from upstream layers over free-text keyword
inspection.

## Outputs

The engine should produce decision-ready answers:

```text
Research decision
Ranked child niche recommendation
Recommended product set
Recommended customization system
Listing count recommendation
Difficulty estimate
Scalability estimate
Competition estimate
Launch timing
Investment level
Portfolio strategy
Final recommendation
Decision rationale
Confidence level
Execution next step
```

## Decision 1: Should We Research This Niche?

Input:

```text
Parent market strength
Child niche opportunity evidence
Search rank strength
Trend direction
Active months
Seasonality
Portfolio fit
Product fit
Customization fit
```

Logic:

```text
Research if the niche has measurable demand, a clear buyer intent, a usable
product path, and enough evidence to justify analyst time.

Validate first if demand exists but product fit, customization fit, timing, or
competition is unclear.

Monitor if the niche has weak evidence or is too early.

Ignore if the niche lacks demand evidence, has poor product fit, or does not fit
MRnD's personalized POD model.
```

Output:

```text
Research
Validate First
Monitor
Ignore
```

Confidence:

```text
High when market, segment, product fit, and customization fit all agree.
Medium when demand exists but one or two supporting layers are weak.
Low when the decision depends mostly on inferred or sparse evidence.
```

Dependencies:

```text
Market strength
Segment evidence
Product fit
Customization fit
Portfolio strategy
```

## Decision 2: Which Child Niche Should Be Researched First?

Input:

```text
All child niches under the same parent market
Opportunity score
Best rank
Trend
Seasonality
Product fit
Customization fit
Portfolio coverage
Whitespace value
```

Logic:

```text
Prioritize child niches that combine strong demand evidence, good product fit,
clear personalization, and strategic portfolio value.

Prefer niches that create reusable learning across other markets.

Seasonal niches should move up only when the research calendar supports the
launch window.
```

Output:

```text
Ranked child niche list
Primary child niche
Secondary child niche
Backup niche
```

Confidence:

```text
High when the top child niche leads on both market evidence and execution fit.
Medium when several niches are close and timing determines priority.
Low when ranking depends on sparse or inconsistent evidence.
```

Dependencies:

```text
Parent market
Opportunity scorecard
Portfolio tree
Seasonality
Product and customization fit
```

## Decision 3: Which Products Fit Best?

Input:

```text
Child niche
Customer intent
Recipient or buyer identity
Emotional intensity
Seasonality
Existing product fit signals
Internal product capability
Winner patterns
```

Logic:

```text
Recommend products that naturally satisfy the buyer intent and can carry the
required personalization.

Emotional and memorial niches favor keepsake products.
Profession and appreciation niches favor daily-use products.
Seasonal niches favor ornament, mug, shirt, and decor products.
Family recipient niches often favor blanket, canvas, mug, or ornament.
Hobby niches often favor tumbler, mug, shirt, and canvas.
```

Output:

```text
Best product
Secondary products
Products to avoid
Reason for product fit
```

Confidence:

```text
High when product, intent, customization, and historical winner patterns align.
Medium when product fit is logical but not yet proven internally.
Low when the product is speculative or hard to personalize.
```

Dependencies:

```text
Customer intent
Customization fit
Design style feasibility
Production constraints
Winner evidence
```

## Decision 4: Which Customization Should Be Used?

Input:

```text
Child niche
Product format
Recipient relationship
Customer intent
Emotional intensity
Design style
Production complexity
Existing personalization systems
```

Logic:

```text
Use the simplest customization that makes the product meaningfully personal.

Name customization is broad and scalable.
Photo customization is strongest for pet, memorial, family, and keepsake niches.
Multiple Kids works for parent and grandparent family gifts.
Birth Flower works for mother, grandmother, birthday, and floral gift angles.
Clipart works for hobbies, professions, sports, and seasonal themes.
Hand Drawing and Line Art work when emotional value justifies higher production
complexity.
```

Output:

```text
Recommended customization
Secondary customization
Customization complexity
Personalization rationale
```

Confidence:

```text
High when customization directly matches the buyer intent.
Medium when customization is broadly applicable but not unique.
Low when customization may add complexity without improving buyer value.
```

Dependencies:

```text
Product format
Design style
Production system
Customer intent
Internal fulfillment capability
```

## Decision 5: Should We Create 1 Listing, 3 Listings, Or Multiple Product Families?

Input:

```text
Opportunity strength
Product fit breadth
Customization fit breadth
Portfolio stage
Competition level
Seasonality
Expected scalability
Internal production capacity
```

Logic:

```text
Create 1 listing when evidence is narrow, uncertainty is high, or the goal is a
small validation test.

Create 3 listings when one niche has strong evidence and three product or style
angles are plausible.

Create multiple product families when the parent market is strong, child niche
evidence is repeatable, product fit is broad, and customization systems can be
reused.
```

Output:

```text
1 Listing
3 Listings
Multiple Product Families
```

Confidence:

```text
High when market strength, portfolio need, and execution capacity align.
Medium when evidence supports expansion but internal capacity is uncertain.
Low when the listing count is based on exploratory assumptions.
```

Dependencies:

```text
Portfolio stage
Product fit matrix
Customization fit matrix
Research capacity
Winner patterns
```

## Decision 6: Expected Difficulty

Input:

```text
Competition level
Customization complexity
Design complexity
Listing complexity
Seasonality pressure
Product production difficulty
Internal experience with the niche
```

Logic:

```text
Easy when the niche uses familiar products, simple name or clipart
customization, clear listing language, and low timing pressure.

Medium when the niche has moderate competition, some design complexity, or
requires new research but uses familiar production systems.

Hard when the niche has high competition, emotional buyer expectations, photo or
hand drawing workflows, complex listing requirements, or seasonal urgency.
```

Output:

```text
Easy
Medium
Hard
```

Confidence:

```text
High when all execution complexity signals point in the same direction.
Medium when production is known but market competition is uncertain.
Low when internal capability or competition evidence is missing.
```

Dependencies:

```text
Competition
Customization
Product
Design style
Seasonality
Internal capability
```

## Decision 7: Expected Scalability

Input:

```text
Parent market size
Number of child niches
Reusable products
Reusable customization systems
Reusable design styles
Winner transfer potential
Portfolio whitespace
```

Logic:

```text
High scalability when the niche can support multiple products, repeated
customization systems, and adjacent child niches.

Medium scalability when the niche can support several designs or products but
does not clearly expand across many markets.

Low scalability when the idea is narrow, seasonal, hard to reuse, or dependent
on one product only.
```

Output:

```text
Low
Medium
High
```

Confidence:

```text
High when reusable product, customization, and market patterns are proven.
Medium when scalability is logical but not proven.
Low when scalability depends on untested assumptions.
```

Dependencies:

```text
Portfolio intelligence
Research Knowledge Graph
Winner evidence
Product fit
Customization fit
```

## Decision 8: Expected Competition

Input:

```text
Market maturity
Parent demand size
Best rank
Keyword breadth
Known competition estimate
Product saturation
Listing pattern saturation
Internal differentiation options
```

Logic:

```text
Low competition when demand exists but the niche is specific, under-covered, and
has clear differentiation.

Medium competition when the market is active but a clear product or
customization angle can create separation.

High competition when the parent market is large, mature, broad, and likely
crowded with similar products.
```

Output:

```text
Low
Medium
High
```

Confidence:

```text
High when competition indicators agree with market maturity and product
saturation.
Medium when competition is inferred from market size and ranking only.
Low when external marketplace evidence has not been reviewed.
```

Dependencies:

```text
Market maturity
Opportunity scoring
Portfolio coverage
External Amazon review when available
```

## Decision 9: Recommended Launch Month

Input:

```text
Customer intent
Seasonality type
Peak month
Research lead time
Listing build time
Ad testing lead time
Product complexity
```

Logic:

```text
Evergreen opportunities can launch after research and production readiness.

Seasonal opportunities should launch before the buying window, not during the
peak.

Complex custom products need more lead time than simple name or clipart
products.
```

Output:

```text
Recommended research month
Recommended listing month
Recommended ads month
Expected peak month
```

Confidence:

```text
High when the intent has a known calendar peak.
Medium when the seasonality is inferred from keyword evidence.
Low when timing depends on weak or emerging trends.
```

Dependencies:

```text
Seasonality
Customer intent
Product complexity
Customization complexity
Advertising plan
```

## Decision 10: Expected Investment Level

Input:

```text
Recommended listing count
Product complexity
Customization complexity
Design complexity
Advertising need
Research difficulty
Expected scalability
Portfolio strategy
```

Logic:

```text
Low investment for one listing, simple product, simple customization, and low
ad-testing need.

Medium investment for three listings, moderate design variation, or moderate ad
testing.

High investment for multiple product families, complex personalization, broad
creative exploration, or competitive launch needs.
```

Output:

```text
Low
Medium
High
```

Confidence:

```text
High when listing count and production complexity are clear.
Medium when investment depends on ad testing.
Low when product or customization workflows are unproven.
```

Dependencies:

```text
Listing count
Difficulty
Product fit
Customization fit
Advertising strategy
Internal capacity
```

## Decision 11: Portfolio Strategy

Input:

```text
Parent market coverage
Existing child segments
Whitespace opportunities
Market stage
Portfolio stage
Winner overlap
Internal catalog fit
```

Logic:

```text
Create new portfolio when the market is strategically distinct and not covered
by existing MRnD research.

Expand existing when the niche belongs to an active parent market or can reuse
existing products, customization, design systems, or listings.

Ignore when the niche is weak, off-model, redundant, or unlikely to produce
repeatable learning.
```

Output:

```text
Create New Portfolio
Expand Existing
Ignore
```

Confidence:

```text
High when parent market mapping and portfolio coverage are clear.
Medium when the niche can fit multiple portfolios.
Low when taxonomy or portfolio ownership is ambiguous.
```

Dependencies:

```text
Portfolio intelligence
Research Knowledge Graph
Internal catalog mapping
Winner evidence
```

## Decision 12: Final Recommendation

Input:

```text
Research decision
Child niche priority
Product fit
Customization fit
Listing count
Difficulty
Scalability
Competition
Launch timing
Investment level
Portfolio strategy
Confidence
```

Logic:

```text
Create now when demand evidence, product fit, customization fit, timing, and
portfolio strategy are all strong enough to execute.

Validate first when the opportunity is promising but has uncertainty in product
fit, customization, competition, or timing.

Monitor when the signal is not strong enough for active research but may improve
with future data.

Ignore when the niche is weak, off-model, over-complex, or strategically
irrelevant.
```

Output:

```text
Create Now
Validate First
Monitor
Ignore
```

Confidence:

```text
High when the final recommendation is supported by multiple independent layers.
Medium when the recommendation depends on one weak but acceptable assumption.
Low when the recommendation is exploratory or evidence is incomplete.
```

Dependencies:

```text
All prior decisions
Portfolio strategy
Execution capacity
Research timing
```

## Confidence Model

Confidence should describe evidence quality, not attractiveness.

Confidence levels:

```text
High
Medium
Low
```

High confidence:

```text
Market demand is clear.
Child niche evidence is clear.
Product fit is clear.
Customization fit is clear.
Seasonality is known or not relevant.
Portfolio action is clear.
```

Medium confidence:

```text
Demand exists but one major decision depends on inferred evidence.
The niche is promising but product or customization fit needs validation.
Seasonality or competition is partially uncertain.
```

Low confidence:

```text
Evidence is sparse.
The niche may be off-model.
The product path is unclear.
Customization may not add buyer value.
External competition is unknown.
```

## Decision Architecture

The Decision Engine should be a rule-governed layer above intelligence and
portfolio outputs.

Conceptual inputs:

```text
Market scorecard
Demand intelligence
Segment opportunity scoring
Product fit matrix
Customization fit matrix
Portfolio master
Portfolio tree
Whitespace analysis
Research knowledge graph
Winner evidence
```

Conceptual outputs:

```text
Decision profile
Research plan
Launch recommendation
Portfolio action
Execution brief
```

The engine should not replace analyst judgment. It should make the decision
logic visible so MRnD can review, override, and improve the rules.

## Decision Profile

Each evaluated niche should have one decision profile.

Recommended fields:

```text
parent_market
child_niche
customer_intent
recommended_product
recommended_customization
recommended_listing_count
expected_difficulty
expected_scalability
expected_competition
recommended_launch_month
expected_investment
portfolio_strategy
final_recommendation
confidence
decision_rationale
next_step
```

The profile is the executive-ready output.

## Execution Handoff

When the final recommendation is `Create Now`, the engine should hand off:

```text
Niche to research
Product to test
Customization to implement
Design style to explore
Listing count
Launch month
Investment level
Known risks
Next action
```

When the final recommendation is `Validate First`, the handoff should be:

```text
Validation question
Evidence gap
Minimum research needed
Decision date
Fallback action
```

When the final recommendation is `Monitor`, the handoff should be:

```text
Metric to watch
Next import date
Trigger for reconsideration
```

When the final recommendation is `Ignore`, the handoff should be:

```text
Reason for rejection
Condition that could reopen the niche
```

## Governance Rules

Rules:

```text
Do not make final recommendations from keyword count alone.
Do not recommend products before market and segment are known.
Do not recommend complex customization without buyer-intent justification.
Do not recommend multiple product families without scalability evidence.
Do not treat high demand as low competition.
Do not treat seasonality as bad; treat it as timing risk.
Do not call an idea scalable unless it can reuse products, customization, or
design systems.
Do not ignore analyst override notes.
```

## Example Decision Paths

### Christmas Teacher Gift

```text
Market: Teacher Gift
Demand: Gift
Segment: Christmas Teacher
Competition: Medium
Seasonality: Q4
Product Fit: Mug
Customization Fit: Name
Portfolio: Expand existing Teacher Gift portfolio
Decision: Create Now if launch timing is early enough; Validate First if the
seasonal window is too close.
Execution: Build one mug listing first, then test tumbler or ornament if early
evidence is strong.
```

### Dog Lover Mom Gift

```text
Market: Mom Gift
Demand: Gift
Segment: Dog Lover Mom
Competition: High
Seasonality: Evergreen
Product Fit: Blanket
Customization Fit: Photo or Name
Portfolio: Expand existing Mom Gift portfolio
Decision: Validate First
Execution: Validate photo blanket language and compare against name-based
drinkware before creating multiple listings.
```

### Fishing Mom Gift

```text
Market: Mom Gift
Demand: Gift
Segment: Fishing Mom
Competition: Medium
Seasonality: Evergreen with gift spikes
Product Fit: Tumbler
Customization Fit: Clipart or Name
Portfolio: Whitespace expansion
Decision: Validate First
Execution: Research search phrases and test a small tumbler concept before
building a broader fishing family collection.
```

## Final Principle

The Decision Engine should turn research data into a clear business action.

The final output should not be:

```text
This niche has a score of 78.
```

The final output should be:

```text
Validate Fishing Mom Gift first with a personalized tumbler concept in March.
Use name plus fishing clipart customization. Keep investment medium. Expand the
Mom Gift portfolio only if validation confirms product fit.
```
