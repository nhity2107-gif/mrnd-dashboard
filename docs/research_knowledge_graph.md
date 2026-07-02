# Research Knowledge Graph

This document defines the MRnD research model for Amazon Personalized POD.

It is design only. It does not define a new pipeline, database migration, CSV
export, dashboard change, or implementation task.

## Purpose

The Research Knowledge Graph organizes market research into reusable layers.
The goal is to help MRnD decide what to research, what to design, what to list,
what to advertise, and what to repeat after a winner is proven.

The graph moves from market demand to execution evidence:

```text
Market
  -> Child Niche
  -> Customer Intent
  -> Product
  -> Customization
  -> Design Style
  -> Listing
  -> Advertising
  -> Winner
```

Each level should remain separate. A "Mom Gift" market is not the same thing as
a "Blanket" product. A "Photo" customization is not the same thing as a
"Watercolor" design style. Keeping the layers separate allows MRnD to reuse
winning products, personalization systems, and listing patterns across multiple
markets.

## Level 1: Market

Definition:

```text
A long-term customer demand category.
```

Examples:

```text
Mom Gift
Dad Gift
Teacher Gift
Grandma Gift
Dog Memorial
Christmas Decor
```

Purpose:

```text
Decide which broad markets deserve research investment.
```

Typical signals:

```text
ABA rank strength
active months
trend
number of child niches
repeatability across products
```

Dashboard use:

```text
Primary dashboard filter.
Portfolio planning filter.
Executive reporting group.
```

Should be scored:

```text
Yes. Score market size, trend, maturity, seasonality, and expansion potential.
```

## Level 2: Child Niches

Definition:

```text
A specific sub-market formed by adding one meaningful semantic dimension to a
parent market.
```

Examples:

```text
Fishing Mom
Gardening Mom
Dog Mom
Coffee Dad
Teacher Appreciation
Christmas Grandma
Soccer Boy
```

Purpose:

```text
Identify the specific niches MRnD should research first within a parent market.
```

Important rule:

```text
Child niches do not include products or customization.
```

Good:

```text
Fishing Mom
Dog Mom
Teacher Appreciation
```

Bad:

```text
Fishing Mom Blanket
Dog Mom Photo Blanket
Teacher Mug
```

Dashboard use:

```text
Primary research queue filter.
Portfolio tree level.
Opportunity comparison level.
```

Should be scored:

```text
Yes. Score opportunity strength, product fit, personalization fit, seasonality,
and whitespace value.
```

## Level 3: Customer Intent

Definition:

```text
The reason the buyer is searching.
```

Examples:

```text
Birthday
Christmas
Wedding
Memorial
Retirement
Sympathy
Graduation
Appreciation
Anniversary
Housewarming
```

Purpose:

```text
Explain the buying occasion and timing behind demand.
```

Customer intent can attach to a market or child niche:

```text
Mom Gift + Birthday
Teacher Gift + Appreciation
Dog Gift + Memorial
Grandma Gift + Christmas
```

Dashboard use:

```text
Seasonal planning filter.
Research calendar filter.
Listing-angle filter.
```

Should be scored:

```text
Yes. Score seasonality, urgency, timing risk, and repeatability.
```

Reusable:

```text
Highly reusable. Christmas, birthday, memorial, and appreciation can be applied
across many markets.
```

## Level 4: Products

Definition:

```text
The physical or printable POD format used to satisfy the demand.
```

Examples:

```text
Blanket
Mug
Tumbler
Canvas
Shirt
Doormat
Ornament
Poster
Tote Bag
```

Purpose:

```text
Decide which product formats should be tested for a market or niche.
```

Product is not demand. It belongs after market, niche, and intent are known.

Examples:

```text
Fishing Mom -> Tumbler
Dog Memorial -> Blanket
Christmas Teacher -> Mug
Grandma Gift -> Blanket
Christmas Family -> Ornament
```

Dashboard use:

```text
Product-fit filter.
Portfolio gap filter.
Research roadmap filter.
```

Should be scored:

```text
Yes. Score product fit, emotional fit, seasonal fit, production fit, and
portfolio coverage.
```

Reusable:

```text
Highly reusable. A winning blanket system can transfer from Mom Gift to Grandma
Gift, Dog Memorial, and Wedding Gift with different personalization and style.
```

## Level 5: Customization

Definition:

```text
The personalization mechanism that makes the product specific to the buyer or
recipient.
```

Examples:

```text
Photo
Name
Multiple Kids
Birth Flower
Hand Drawing
Clipart
Line Art
Date
Pet Name
Family Names
```

Purpose:

```text
Determine how MRnD turns a market demand into a personalized product system.
```

Examples:

```text
Dog Memorial + Blanket -> Photo
Mom Gift + Mug -> Name
Grandma Gift + Blanket -> Multiple Kids
Birthday Mom + Canvas -> Birth Flower
Fishing Dad + Tumbler -> Clipart
```

Dashboard use:

```text
Customization filter.
Production-complexity filter.
Internal catalog reuse filter.
```

Should be scored:

```text
Yes. Score personalization fit, production complexity, repeatability, and
template reuse.
```

Reusable:

```text
Highly reusable. Photo, name, and clipart systems should become reusable
production modules across many products and markets.
```

## Level 6: Design Style

Definition:

```text
The visual language applied to a product and customization system.
```

Examples:

```text
Minimal
Vintage
Watercolor
Cartoon
Line Art
Retro
Floral
Boho
Funny
Patriotic
```

Purpose:

```text
Create design differentiation without changing the underlying market, product,
or personalization system.
```

Examples:

```text
Dog Memorial + Blanket + Photo + Watercolor
Fishing Dad + Tumbler + Clipart + Vintage
Mom Birth Flower + Canvas + Minimal
Teacher Appreciation + Mug + Cartoon
```

Dashboard use:

```text
Design direction filter.
Creative testing filter.
Style coverage filter.
```

Should be scored:

```text
Yes, but after product and customization fit. Score style fit, novelty,
portfolio saturation, and transferability.
```

Reusable:

```text
Reusable as design systems. A style can move across markets if the product and
customization structure is similar.
```

## Level 7: Listing

Definition:

```text
The Amazon listing execution layer.
```

Components:

```text
Title
Bullet
Image
Variation
Pricing
A+ Content
Backend Terms
Offer Structure
```

Purpose:

```text
Convert a researched product concept into a search-optimized Amazon offer.
```

Dependencies:

```text
Listing depends on market, niche, intent, product, customization, and design
style.
```

Examples:

```text
Title uses market, niche, product, and intent.
Images prove product, customization, and style.
Variations group product options or personalization options.
Pricing reflects product cost, perceived value, and competitive range.
```

Dashboard use:

```text
Listing readiness filter.
Launch checklist status.
Post-launch performance comparison.
```

Should be scored:

```text
Yes. Score listing completeness, keyword alignment, image coverage, variation
quality, and pricing fit.
```

Reusable:

```text
Partially reusable. Listing frameworks are reusable, but final titles, images,
and bullets must match the exact market and product.
```

## Level 8: Advertising

Definition:

```text
The traffic strategy used to test or scale a listing.
```

Channels:

```text
Organic
Sponsored
External
```

Purpose:

```text
Determine how the listing will be discovered and validated.
```

Advertising depends on listing readiness and market timing.

Examples:

```text
Organic -> keyword-indexing and search rank validation.
Sponsored -> controlled keyword and product-target tests.
External -> seasonal pushes, social proof, or creator traffic.
```

Dashboard use:

```text
Traffic strategy filter.
Launch phase filter.
Testing budget filter.
```

Should be scored:

```text
Yes. Score traffic readiness, CPC risk, seasonality timing, listing readiness,
and expected learning value.
```

Reusable:

```text
Reusable at the playbook level. Campaign structures can repeat, but bids,
keywords, and targeting should be market-specific.
```

## Level 9: Winner

Definition:

```text
A proven listing or product system with repeatable business evidence.
```

Signals:

```text
Revenue
Orders
CVR
CTR
Repeatability
Profit
Review velocity
Ad efficiency
Organic rank stability
```

Purpose:

```text
Identify what should be scaled, copied, adapted, or retired.
```

Winner evidence should feed back into earlier layers:

```text
Winning product -> reusable product fit signal
Winning customization -> reusable personalization module
Winning style -> reusable creative system
Winning listing -> reusable listing framework
Winning ad structure -> reusable launch playbook
```

Dashboard use:

```text
Winner filter.
Repeatability filter.
Revenue and conversion reporting.
Portfolio scaling view.
```

Should be scored:

```text
Yes. Score commercial performance, repeatability, margin quality, and transfer
potential.
```

## Relationship Model

The graph should support many-to-many relationships.

```text
One Market can have many Child Niches.
One Child Niche can connect to many Customer Intents.
One Customer Intent can apply to many Markets.
One Product can serve many Child Niches.
One Customization can work across many Products.
One Design Style can be reused across many Markets.
One Listing belongs to one product concept but can use reusable templates.
One Advertising playbook can test many Listings.
One Winner can generate reusable evidence for many future concepts.
```

Recommended relationship types:

```text
market_has_niche
niche_has_intent
niche_fits_product
product_supports_customization
customization_supports_style
concept_has_listing
listing_uses_advertising
listing_becomes_winner
winner_reuses_pattern
```

## Dependency Rules

Research should flow in this order:

```text
1. Validate Market
2. Select Child Niche
3. Identify Customer Intent
4. Choose Product
5. Choose Customization
6. Choose Design Style
7. Build Listing
8. Launch Advertising
9. Measure Winner Evidence
```

Dependency rules:

```text
Product selection depends on market, child niche, and intent.
Customization depends on product and emotional/customer fit.
Design style depends on niche, customization, and target buyer expectations.
Listing depends on every upstream research choice.
Advertising depends on listing readiness and timing.
Winner status depends on actual commercial performance.
```

Do not skip levels. For example, choosing "Blanket" before identifying the
market and child niche creates product-centric research, which is not the target
architecture.

## Reusable Layers

Most reusable:

```text
Customer Intent
Products
Customization
Design Style
Listing frameworks
Advertising playbooks
Winner patterns
```

Less reusable:

```text
Exact child niches
Exact titles
Exact image sets
Exact pricing
Exact ad bids
```

Market and child niche evidence should guide what gets tested. Product,
customization, style, listing, and advertising systems should become reusable
assets once they prove repeatable.

## Layers To Score

Scoring should exist at multiple levels, but each score must answer a different
business question.

```text
Market Score
  Question: Is this parent market worth investment?

Child Niche Score
  Question: Which niche should be researched first?

Intent Score
  Question: Is the buying occasion large, urgent, seasonal, or repeatable?

Product Fit Score
  Question: Which product format best satisfies this demand?

Customization Fit Score
  Question: Which personalization mechanism is most relevant and scalable?

Design Style Score
  Question: Which style is most likely to differentiate the product?

Listing Readiness Score
  Question: Is the offer ready to launch?

Advertising Readiness Score
  Question: Is the listing ready for paid or external traffic?

Winner Score
  Question: Is this concept proven enough to scale or repeat?
```

## Dashboard Filters

Core filters:

```text
Market
Child Niche
Customer Intent
Product
Customization
Design Style
Portfolio Stage
Research Priority
Seasonality
Winner Status
```

Operational filters:

```text
Listing Status
Advertising Channel
Launch Month
Peak Month
Product Fit Tier
Customization Fit Tier
Design Status
Research Owner
```

Performance filters:

```text
Revenue Tier
Order Tier
CVR Tier
CTR Tier
Repeatability Tier
Organic Rank Status
Ad Efficiency Tier
```

## Example Graph Paths

### Mom Gift Path

```text
Market: Mom Gift
Child Niche: Gardening Mom
Customer Intent: Birthday
Product: Tumbler
Customization: Name
Design Style: Watercolor
Listing: Title + bullets + lifestyle images + personalized variation
Advertising: Sponsored keyword test
Winner: Revenue, orders, CVR, CTR, repeatability
```

### Dog Memorial Path

```text
Market: Dog Memorial
Child Niche: Dog Memorial
Customer Intent: Sympathy
Product: Blanket
Customization: Photo
Design Style: Line Art
Listing: Memorial title + emotional images + photo personalization
Advertising: Organic and sponsored exact-match tests
Winner: Revenue, orders, CVR, CTR, repeatability
```

### Teacher Appreciation Path

```text
Market: Teacher Gift
Child Niche: Teacher Appreciation
Customer Intent: Appreciation
Product: Mug
Customization: Name
Design Style: Minimal
Listing: Appreciation title + classroom use images + name variation
Advertising: Sponsored seasonal test before teacher appreciation windows
Winner: Revenue, orders, CVR, CTR, repeatability
```

## Research Decision Output

The final research decision should combine:

```text
Market strength
Child niche opportunity
Intent timing
Product fit
Customization fit
Design differentiation
Listing readiness
Advertising readiness
Winner evidence or expected repeatability
```

The recommended output should answer:

```text
What parent market should MRnD invest in?
Which child niche should be researched first?
Which product should be tested first?
Which customization system should be used?
Which design style should be explored?
When should the listing be prepared?
How should traffic be tested?
What evidence proves the concept is a winner?
Can the winning pattern be repeated elsewhere?
```

## Governance

The graph should remain evidence-led.

Rules:

```text
Do not merge product into demand.
Do not merge customization into product.
Do not treat a design style as a market.
Do not treat listing text as market evidence.
Do not call a concept a winner without commercial evidence.
Do not make dashboard filters from unstable free-text fields without review.
```

Manual review should be required before adding new canonical entities to master
knowledge dictionaries. The graph can recommend candidates, but it should not
automatically rewrite the taxonomy.
