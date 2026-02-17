# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Instagram post generator for the On brand, built with [Google ADK](https://google.github.io/adk-docs/). Uses scraped product catalog data from on.com to generate marketing assets. Python 3.11+, managed with `uv`.

## Commands

```bash
make setup    # uv sync + build product index
make index    # Rebuild data/product_index.json from scraped data
make run      # Run agent pipeline in CLI mode (uv run adk run agents)
make web      # Start ADK web UI (uv run adk web .)
make clean    # Remove output/*.png and output/*.json
```

Requires `GOOGLE_API_KEY` in `.env` (see `.env.example`).

## Architecture

Two-agent sequential pipeline (`agents/agent.py` defines the root `SequentialAgent`):

1. **Ideation Agent** (`agents/ideation/`) — `gemini-2.5-flash`
   - Reads a mood board markdown file from `mood_boards/`
   - Searches `data/product_index.json` via keyword matching
   - Outputs `output/ideas.json` with 3 post concepts (validated against `PostIdea` schema)

2. **Assets Generator Agent** (`agents/assets_generator/`) — `gemini-2.5-flash-image`
   - Reads `output/ideas.json`
   - Generates 3 image variations per idea (9 images total) using Gemini native image generation
   - Saves as `output/<idea_id>_v<n>.png`

Agents communicate via a JSON contract defined in `agents/shared/schemas.py` (`PostIdea` and `IdeasOutput` Pydantic models). Each agent's tools are in its `tools.py`.

### Product Index

`scripts/build_product_index.py` builds `data/product_index.json` from scraped product/collection JSON files. It extracts data in two phases: first from JSON-LD structured data (richer), then supplements from content fields. The index is the sole data source the ideation agent searches against — it does NOT read raw product files at runtime.

## Data Architecture

All data lives under `./data/` (~17GB, 9500+ files) organized into:

- **products/** — ~3500 product JSON files + `assets/` subdirectory with ~4750 product images
- **pages/** — ~723 static page JSONs (company info, store locations, athlete listings, etc.)
- **collections/** — ~43 collection JSONs (product groupings like Cloud series, Active Life)
- **stories/** — ~436 editorial/blog content JSONs
- **sitemap/** — sitemap data
- **product_index.json** — lightweight search index built by `scripts/build_product_index.py`

### Common JSON Schema

All scraped data files follow this structure:

```json
{
  "url": "https://www.on.com/...",
  "type": "product|page|collection|story",
  "extractedAt": "ISO timestamp",
  "metadata": { "title", "description", "canonical", "openGraph" },
  "structuredData": { "jsonLd": [...], "schemaOrg": { ... } },
  "content": { ... }
}
```

## File Naming Conventions

Files are prefixed by their type: `products-*.json`, `collection-*.json`, `stories-*.json`. Product filenames include the SKU identifier at the end (e.g., `products-3-core-shorts-1wf1015-womens-black-apparel-1WF10150553.json`).

## Mood Boards

Input mood boards go in `mood_boards/` as markdown files. See `mood_boards/sample_mood_board.md` for the expected structure (sections: Theme, Products to Consider, Visual Direction, Tone).
