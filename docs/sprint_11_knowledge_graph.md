# Sprint 11 - Knowledge Graph Layer

Sprint 11 creates an entity-based Knowledge Graph layer for the MRnD Demand
Intelligence Platform.

The goal is to move beyond flat keyword matching and represent Amazon search
terms as relationships between market entities.

## Philosophy

Current taxonomy matching produces columns such as:

```text
recipient
profession
interest
product
customization
holiday
theme
```

The Knowledge Graph turns those flat columns into:

```text
entity nodes
keyword-to-entity edges
entity-to-entity co-occurrence
```

This makes it possible to later build demand, niche, solution, and catalog
models from entity relationships rather than one keyword row at a time.

## Inputs

Tables:

```text
demand_objects
normalized_keywords
```

Files:

```text
knowledge/master/*.csv
```

The master CSV schema is:

```text
canonical
entity_type
aliases
priority
active
notes
```

`stopwords.csv` is ignored because stopwords are filtering terms, not market
entities.

## Output Tables

Sprint 11 creates only these tables:

```text
entity_master
keyword_entity_edges
entity_cooccurrence
```

No previous demand, taxonomy, import, or opportunity tables are modified.

## entity_master

Purpose:

```text
Canonical entity node list for the graph.
```

Columns:

```text
entity_id
entity_type
canonical
aliases
priority
active
```

Source:

```text
knowledge/master/*.csv
demand_objects observed entity values
```

If an entity appears in `demand_objects` but is missing from the master
dictionary, it is added as an observed-only graph entity with:

```text
aliases = empty
priority = 0
active = true
```

This keeps graph edges complete without automatically modifying
`knowledge/master/`.

## keyword_entity_edges

Purpose:

```text
Connect every keyword row to every entity detected in that row.
```

Columns:

```text
keyword_id
normalized_keyword
raw_keyword
entity_id
entity_type
entity_value
month
search_frequency_rank
```

Rules:

```text
one keyword can have many entities
product is an entity but not demand
customization is an entity but not demand
```

Example:

```text
teacher christmas gift mug
```

Can create edges like:

```text
profession = teacher
holiday = christmas
product = mug
```

## entity_cooccurrence

Purpose:

```text
Measure which entities appear together in the same keyword rows.
```

Columns:

```text
entity_a_type
entity_a_value
entity_b_type
entity_b_value
keyword_count
best_rank
top_1000_count
example_keywords
```

Primary strength signal:

```text
best_rank
```

Lower Search Frequency Rank is stronger.

`keyword_count` is retained as supporting evidence, but it is not the main
strength signal.

Example:

```text
profession = teacher
product = mug
best_rank = 1015
example_keywords = teacher gift | teacher mug | teacher christmas mug
```

## Entity Types

The graph currently supports the entity columns already present in
`demand_objects`:

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

Product and customization are graph entities. They are intentionally not
demand identities.

## CSV Exports

Reports export to:

```text
data/output/knowledge_graph/
```

Files:

```text
entity_master.csv
keyword_entity_edges.csv
entity_cooccurrence.csv
top_entity_pairs.csv
```

`top_entity_pairs.csv` is the first 1,000 co-occurrence rows sorted by:

```text
best_rank
top_1000_count
keyword_count
```

## CLI

Run:

```powershell
python src/pipeline/build_knowledge_graph.py --rebuild
```

Without `--rebuild`, the script exits if graph tables already exist.

## Safety

Sprint 11 does not:

- modify old demand tables
- modify `demand_objects`
- modify `normalized_keywords`
- modify `knowledge/master/`
- build Opportunity Score
- use AI clustering
- turn product into demand
- turn customization into demand

The graph is deterministic and can be rebuilt from the current database and
master knowledge files.

## Future Use

Future demand and niche modeling can use the graph as:

```text
keyword_entity_edges
  -> demand identity candidates
  -> niche clusters
  -> solution layer
  -> internal catalog mapping
  -> opportunity score
```

Examples:

```text
recipient=grandma + holiday=christmas + product=ornament
```

Could support a future niche:

```text
Grandma Christmas Ornament
```

But Sprint 11 stops at graph construction and co-occurrence analysis.
