# Sprint 3 - Demand Builder

This sprint builds structured market intelligence demand objects from `normalized_keywords`.

## Scope

Input table:

```sql
normalized_keywords
```

Knowledge input:

```text
knowledge/master/*.csv
```

Output table:

```sql
demand_objects
```

This sprint does not implement clustering, opportunity scoring, AI, or dashboard features.

## Demand Object Columns

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
month
search_frequency_rank
reporting_date
```

## Matching Rules

The builder loads every CSV in `knowledge/master/`.

Active knowledge rows are used when:

- `active` is true
- `entity_type` is one of `recipient`, `profession`, `interest`, `pet`, `occasion`, `product`, `customization`, `style`, or `modifier`

The builder matches each canonical value and each `|`-separated alias against `normalized_search_term`.

If multiple aliases match the same entity type, the builder keeps the canonical value with the highest `priority`. Ties are resolved by longer alias length, then canonical value.

One keyword can produce multiple entity values across different entity columns.

## Unknown Review Files

The builder does not modify master dictionaries.

When a demand object has no match for an entity type, the normalized keyword is appended as a distinct review candidate to:

```text
knowledge/review/unknown_recipient.csv
knowledge/review/unknown_profession.csv
knowledge/review/unknown_interest.csv
knowledge/review/unknown_pet.csv
knowledge/review/unknown_occasion.csv
knowledge/review/unknown_product.csv
knowledge/review/unknown_customization.csv
knowledge/review/unknown_style.csv
knowledge/review/unknown_modifier.csv
```

Review files are append-only and de-duplicate by `candidate`.

## Run

Build demand objects:

```powershell
python src/pipeline/build_demand_objects.py
```

Rebuild the `demand_objects` table:

```powershell
python src/pipeline/build_demand_objects.py --rebuild
```

Log file:

```text
logs/build_demand_objects.log
```

## Validate

Confirm the table exists:

```sql
SHOW TABLES;
```

Check row count:

```sql
SELECT count(*) FROM demand_objects;
```

Compare against the source:

```sql
SELECT
  (SELECT count(*) FROM normalized_keywords) AS normalized_keywords,
  (SELECT count(*) FROM demand_objects) AS demand_objects;
```

Inspect entity coverage:

```sql
SELECT
  count(*) AS rows,
  count(product) AS product_matches,
  count(recipient) AS recipient_matches,
  count(occasion) AS occasion_matches,
  count(modifier) AS modifier_matches
FROM demand_objects;
```

Inspect sample demand objects:

```sql
SELECT
  raw_keyword,
  normalized_keyword,
  recipient,
  profession,
  interest,
  pet,
  occasion,
  product,
  customization,
  style,
  modifier,
  month,
  search_frequency_rank
FROM demand_objects
ORDER BY search_frequency_rank
LIMIT 25;
```
