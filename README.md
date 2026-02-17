# On Marketing Assets Generator

Instagram post generator for the On brand, built with [Google ADK](https://google.github.io/adk-docs/).

`./data` folder contains all publicly available data from On online catalogue which can be used for assets generation.

Two agents chain together via a JSON contract:

1. **Ideation Agent** — reads a mood board + searches the product catalog, outputs `ideas.json` with 3 post concepts
2. **Assets Generator Agent** — takes each idea, generates 3 image variations per idea (9 images total) using Gemini native image generation

## Quick start

```bash
# 1. Set your API key
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY

# 2. Install deps + build product index
make setup

# 3. Run the pipeline
make run
# or launch the web UI:
make web
```

## Commands

```
make help     Show all commands
make setup    Install dependencies and build product index
make index    Rebuild the product index from scraped data
make run      Run the agent pipeline in CLI mode
make web      Start the ADK web UI (browser-based)
make clean    Remove generated output files
```

## Usage

When the agent starts, tell it which mood board to use:

```
Generate Instagram posts from mood_boards/sample_mood_board.md
```

The pipeline will:
1. Read the mood board
2. Search the product catalog for matching products
3. Generate 3 post ideas with real product data, saved to `output/ideas.json`
4. Generate 3 image variations per idea, saved as `output/<idea_id>_v<n>.png`

## Creating mood boards

Add markdown files to `mood_boards/`. Structure:

```markdown
# Campaign Name

## Theme
What the campaign is about

## Products to Consider
- Specific products or categories

## Visual Direction
- Lighting, settings, composition notes

## Tone
The feeling / brand voice for this campaign
```

## Project structure

```
agents/
  agent.py              # Root SequentialAgent (entry point)
  ideation/agent.py     # Ideation agent (gemini-2.5-flash)
  ideation/tools.py     # read_mood_board, search_products, save_ideas
  assets_generator/     # Assets agent (gemini-2.5-flash-image)
  shared/schemas.py     # PostIdea / IdeasOutput Pydantic models
scripts/
  build_product_index.py  # Builds data/product_index.json from scraped data
mood_boards/              # Input mood board markdown files
output/                   # Generated ideas JSON + images
data/                     # Scraped product catalog (~17GB)
```
