# Market Intelligence Knowledge Base

The knowledge base stores curated entities used to interpret Amazon POD keyword demand.
Master files live in:

```text
knowledge/master/
```

Each file is a CSV with the same schema:

```text
canonical,entity_type,aliases,priority,active,notes
```

## Schema

`canonical`

The preferred normalized value for an entity. Use lowercase unless a proper noun or brand rule later requires otherwise.

`entity_type`

The entity category. It should match the template purpose, such as `recipient`, `interest`, `profession`, `product`, `occasion`, `customization`, `style`, `modifier`, or `stopword`.

`aliases`

Alternate spellings, plural forms, abbreviations, and common query variants. Separate multiple aliases with `|`.

`priority`

Integer ranking for matching and review. Higher values represent more important or more common entities.

`active`

Boolean flag. Use `true` for active entities and `false` to keep an entity in the file but disable it from matching.

`notes`

Short human-readable context explaining why the entity exists or how it should be used.

## Templates

The current master templates are:

```text
recipient.csv
interest.csv
profession.csv
product.csv
occasion.csv
customization.csv
style.csv
modifier.csv
stopwords.csv
```

These are seed templates only. They are not AI logic, clustering logic, or dashboard configuration.
