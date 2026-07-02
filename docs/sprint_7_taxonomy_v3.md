# Sprint 7 - Taxonomy V3 Expansion

Sprint 7 upgrades the MRnD Market Intelligence Platform taxonomy from simple
keyword matching toward a semantic market taxonomy for Amazon Personalized POD
research.

This sprint does not modify the import pipeline, research model, Opportunity
Engine, or Opportunity Score.

## Goal

Taxonomy V3 expands demand interpretation so keywords can express buyer context,
recipient context, age group, gender, holiday, theme, lifestyle, product, and
customization at the same time.

The target is not to turn every keyword into a product. The target is to make
market demand easier to segment for POD research.

## New Master Dictionaries

Sprint 7 adds five master dictionary files under:

```text
knowledge/master/
```

New files:

```text
age_group.csv
gender.csv
holiday.csv
theme.csv
lifestyle.csv
```

All files use the existing master schema:

```text
canonical,entity_type,aliases,priority,active,notes
```

## Taxonomy Layers

Taxonomy V3 supports these demand object dimensions:

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
age_group
gender
holiday
theme
lifestyle
```

The first nine dimensions are existing Sprint 3 demand object fields. Sprint 7
adds the last five fields.

## Demand Object Extension

`demand_objects` is extended with:

```text
age_group
gender
holiday
theme
lifestyle
```

Existing demand object columns are preserved.

Expected V3 demand object shape:

```text
demand_id
raw_keyword
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
age_group
gender
holiday
theme
lifestyle
month
search_frequency_rank
reporting_date
```

## Matching Rules

Taxonomy V3 still uses master dictionary aliases as the core matching mechanism.

The demand builder loads active rows from `knowledge/master/*.csv` and matches
canonical values plus aliases against `normalized_keyword`.

When multiple values match the same entity type, the builder keeps the match
with:

1. highest priority
2. longest alias
3. canonical sort order

Sprint 7 also adds a small semantic overlay for cases that require more than a
simple dictionary row.

## Semantic Overlay

The semantic overlay handles examples that the original taxonomy could not
represent cleanly.

### Teen Girl Gift

Keyword:

```text
teen girl gift
```

Expected interpretation:

```text
recipient = girl
age_group = teen
gender = female
```

Why:

- `girl` is the recipient wording in the keyword.
- `teen` is the age group.
- `girl` also implies female gender.

### Funny Christmas Gift for Nurse

Keyword:

```text
funny christmas gift for nurse
```

Expected interpretation:

```text
profession = nurse
holiday = christmas
theme = funny
```

Why:

- `nurse` is a profession.
- `christmas` is a holiday.
- `funny` is a gift theme.

### Gift for Mom Who Loves Gardening

Keyword:

```text
gift for mom who loves gardening
```

Expected interpretation:

```text
recipient = mom
interest = gardening
```

Why:

- `mom` is the recipient.
- `gardening` is the interest.

### Gift for Dog Mom

Keyword:

```text
gift for dog mom
```

Expected interpretation:

```text
recipient = dog mom
pet = dog
lifestyle = dog lover
```

Why:

- `dog mom` is a recipient identity.
- `dog` is the pet.
- `dog mom` also belongs to the dog-lover lifestyle market.

## New Dictionary Scope

### Age Group

Initial canonical values:

```text
baby
toddler
kid
teen
adult
senior
```

Purpose:

Segment gift demand by life stage and age context.

### Gender

Initial canonical values:

```text
boy
girl
male
female
man
woman
```

Purpose:

Capture gender-coded shopper language without treating gender as the only
recipient signal.

### Holiday

Initial canonical values:

```text
christmas
halloween
thanksgiving
easter
valentine
independence day
new year
mother's day
father's day
```

Purpose:

Separate holiday timing from broader occasion intent.

### Theme

Initial canonical values:

```text
funny
retro
vintage
minimalist
floral
watercolor
boho
patriotic
faith
american
```

Purpose:

Capture design and message themes that influence POD creative direction.

### Lifestyle

Initial canonical values:

```text
coffee lover
wine lover
rv life
lake life
beach life
farm life
country girl
cowgirl
book lover
dog lover
cat lover
```

Purpose:

Capture identity and lifestyle markets that are stronger than generic interests.

## Knowledge Discovery Engine V3

The Knowledge Discovery Engine now supports the V3 taxonomy.

It can generate:

```text
age_group_candidates.csv
gender_candidates.csv
holiday_candidates.csv
theme_candidates.csv
lifestyle_candidates.csv
```

It continues to generate:

```text
recipient_candidates.csv
profession_candidates.csv
interest_candidates.csv
occasion_candidates.csv
product_candidates.csv
customization_candidates.csv
ignore_candidates.csv
```

All discovery outputs remain manual-review files. They are not automatically
merged into `knowledge/master/`.

## Coverage Report V3

The discovery coverage report includes:

```text
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
customization
product
```

The coverage report helps identify which entity types need taxonomy expansion
after each ABA refresh.

## Safety Rules

Sprint 7 follows these safety rules:

- Do not overwrite existing reviewed knowledge.
- Do not automatically merge discovery candidates into master dictionaries.
- Do not modify the import pipeline.
- Do not modify the research model.
- Do not modify the Opportunity Engine.
- Do not build Opportunity Score.
- Preserve existing demand object columns.
- Add new taxonomy fields only as extensions.

## Future Expansion

Future taxonomy versions can add:

```text
relationship_type
buyer_persona
recipient_identity
sentiment
design_motif
humor_type
personalization_depth
price_intent
gift_format
```

Potential examples:

```text
relationship_type = in law
buyer_persona = last minute shopper
recipient_identity = first time mom
sentiment = memorial
design_motif = highland cow
humor_type = sarcastic
personalization_depth = photo plus name
price_intent = under 25
gift_format = stocking stuffer
```

These should be added only when real ABA demand and manual review justify them.

## Validation Checklist

Sprint 7 is valid when:

- new master files exist with the required schema
- `demand_objects` includes V3 columns
- existing demand object columns remain intact
- example classifications work
- discovery output includes V3 candidate files
- coverage report includes V3 entity types
- `knowledge/master/` is not modified except for the new V3 master files
- import, research, and Opportunity Engine code remain unchanged
