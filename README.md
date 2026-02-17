# On Marketing Assets Generator

Instagram post generator for the On brand, built with [Google ADK](https://google.github.io/adk-docs/).

`./data` folder contains all publicly available data from On online catalogue which can be used for assets generation.

> **Important:** To generate marketing assets, this project requires On's publicly available product catalog data placed in the `data/` folder at the project root. Without this data, the ideation agent cannot search for products and the pipeline will not produce results.

Two agents chain together via a JSON contract:

1. **Ideation Agent** — reads a mood board + searches the product catalog, outputs `ideas.json` with 3 post concepts
2. **Assets Generator Agent** — takes each idea, generates 3 image variations per idea (9 images total) using Gemini native image generation

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- A `GOOGLE_API_KEY` (see `.env.example`)

## Data setup

The pipeline requires On's publicly available product catalog data. To populate it:

1. Scrape or obtain the public On catalog data (product pages, collections, stories, etc.)
2. Place the JSON files under `data/` following the directory structure:
   ```
   data/
     products/       # ~3500 product JSON files
     collections/    # ~43 collection JSONs
     pages/          # ~723 static page JSONs
     stories/        # ~436 editorial content JSONs
   ```
3. Build the product index (maps SKUs to file paths):
   ```bash
   make index
   ```
   This runs `scripts/build_product_index.py` and writes `data/product_index.json` — the sole data source the ideation agent searches at runtime.

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

You can run the pipeline in two ways:

**CLI (non-interactive)** — pass a mood board file directly:

```bash
make run-file FILE=mood_boards/pants.md
```

**Interactive mode** — start the agent and tell it which mood board to use:

```bash
make run
# Then type: Generate Instagram posts from mood_boards/pants.md
```

The pipeline will:
1. Read the mood board
2. Search the product catalog for matching products
3. Generate 3 post ideas with real product data, saved to `output/ideas.json`
4. Generate 3 image variations per idea, saved as `output/<idea_id>_v<n>.png`

## Creating mood boards

Add markdown files to `mood_boards/`. Mood boards **must include product SKU references** so the ideation agent can look up the correct products from the catalog. See `mood_boards/pants.md` for an example.

Structure:

```markdown
# Campaign Name

Campaign description, creative direction, and any constraints.

The product SKUs: [1WE30701756, 1WD10570462, 1WF11290069]
```

## Sample generations

Below are example outputs from running the pipeline against the `mood_boards/pants.md` mood board.

### Ideas (output/ideas.json)

```json
{
  "mood_board_source": "mood_boards/pants.md",
  "generated_at": "2026-02-17T22:04:48.474644+00:00",
  "ideas": [
    {
      "id": "idea_1",
      "product_name": "Women's Open Club Pants Crater",
      "product_sku": "1WE30701756",
      "imagery_direction": "A runner, mid-stride and radiating athleticism, is wearing the 'Women's Open Club Pants Crater' in a surreal, urban marathon setting...",
      "headline": "Marathon Morning, Cosmic Mood.",
      "post_description": "Who says sweatpants can't win races? Push your limits and embrace the unexpected...",
      "mood": "Happy, energetic, irreverent"
    },
    {
      "id": "idea_2",
      "product_name": "Women's Weather Vest White | Black",
      "product_sku": "1WD10570462",
      "imagery_direction": "A runner in the 'Women's Weather Vest White | Black' is captured sprinting through a fantastical, slightly chilly street race...",
      "headline": "Out of This World Run.",
      "post_description": "Weather or not, the universe is calling! Our Weather Vest keeps you agile and warm, no matter how wild your run gets...",
      "mood": "Happy, energetic, irreverent"
    },
    {
      "id": "idea_3",
      "product_name": "Women's Court Skirt Side Pleat White",
      "product_sku": "1WF11290069",
      "imagery_direction": "A runner wearing the 'Women's Court Skirt Side Pleat White' is depicted in a dynamic, mid-air leap, as if playfully bounding over an invisible obstacle...",
      "headline": "Leap into the Laps of Joy.",
      "post_description": "Skirt the ordinary, embrace the extraordinary! The Zurich Marathon 2026 is an open invitation to run, leap, and defy gravity...",
      "mood": "Happy, energetic, irreverent"
    }
  ]
}
```

### Generated images

**Idea 1** — "Marathon Morning, Cosmic Mood."

![Idea 1 variation 1](sample_generations/idea_1_v1.png)

**Idea 2** — "Out of This World Run."

![Idea 2 variation 1](sample_generations/idea_2_v1.png)

**Idea 3** — "Leap into the Laps of Joy."

| Variation 1 | Variation 2 |
|---|---|
| ![Idea 3 v1](sample_generations/idea_3_v1.png) | ![Idea 3 v2](sample_generations/idea_3_v2.png) |

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
