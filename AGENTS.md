# MRnD Dashboard

## Rules

- Inspect existing code before making changes.
- Read relevant docs before modifying architecture.
- Never modify data/ files unless explicitly requested.
- Never run pipeline scripts unless explicitly requested.
- Never regenerate CSV outputs unless explicitly requested.
- Never edit generated CSV files manually.
- Only edit app.py or files under src/pipeline when requested.
- Explain exactly which files will be modified before editing.
- Keep pipeline logic deterministic.
- Keep demand, segment, opportunity, product, customization and portfolio as separate concepts.
- Preserve backward compatibility unless explicitly asked to refactor.

## Project Architecture

- app.py is a read-only Streamlit dashboard.
- src/pipeline builds all deterministic CSV layers.
- data/output contains generated artifacts only.
- docs/ defines architecture and terminology.
- CSV outputs are never the source of truth.
