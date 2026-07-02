# Knowledge Base v2 Gift Expansion

This workflow expands the market taxonomy through manual review candidates.
It does not merge anything into `knowledge/master/`.

## Input

The workflow reads:

```text
data/output/gift_intent/unmatched_gift_keywords.csv
```

This file is produced by:

```powershell
python notebooks/gift_intent_explorer.py
```

## Run

Generate candidate review files:

```powershell
python notebooks/knowledge_base_v2_gift_expansion.py
```

The workflow protects existing candidate files. To regenerate after review files
already exist:

```powershell
python notebooks/knowledge_base_v2_gift_expansion.py --overwrite
```

## Outputs

Review files are written to:

```text
knowledge/review/
```

Generated files:

```text
recipient_candidates.csv
profession_candidates.csv
interest_candidates.csv
occasion_candidates.csv
product_candidates.csv
gender_candidates.csv
theme_candidates.csv
ignore_candidates.csv
```

`product_candidates.csv` is included because New Product is one of the Knowledge
Base v2 review groups.

## Schema

Each candidate file uses this schema:

```text
candidate
frequency
example_keywords
recommended_aliases
confidence
```

## Review Policy

These files are review inputs only.

- Do not treat candidates as accepted taxonomy.
- Do not bulk-copy candidates into `knowledge/master/`.
- Review `recommended_aliases` before accepting them.
- Keep `ignore_candidates.csv` out of the master taxonomy unless a reviewer
  decides a term is strategically useful.
- Add accepted entities to the appropriate master CSV manually.
