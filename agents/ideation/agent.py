"""Ideation agent definition — sequential pipeline."""

import os

from google.adk.agents import LlmAgent, SequentialAgent

from agents.ideation.tools import read_mood_board, search_products, get_product_details, save_ideas

TEXT_MODEL = os.environ.get("TEXT_GENERATION_MODEL", "gemini-2.5-flash")

# --- Step 1: Read the mood board ---

MOOD_BOARD_READER_INSTRUCTION = """\
You are a mood board reader. Use `read_mood_board` with the path the user provided
to load the mood board file. Return its full contents unchanged.
"""

mood_board_reader = LlmAgent(
    name="mood_board_reader",
    model=TEXT_MODEL,
    description="Reads a mood board markdown file.",
    instruction=MOOD_BOARD_READER_INSTRUCTION,
    tools=[read_mood_board],
    output_key="mood_board_content",
)

# --- Step 2: Search for products ---

PRODUCT_SEARCHER_INSTRUCTION = """\
You are a product researcher for On, the Swiss running brand. Your job is to find
products from the On catalog that match a mood board.

The mood board content is available in the session state:
{mood_board_content}

Follow these steps:

Scan the mood board for any SKU codes (alphanumeric
codes like "1WE30701756"). If you find any return an array of SKU codes.
"""

product_searcher = LlmAgent(
    name="product_searcher",
    model=TEXT_MODEL,
    description="Searches the On product catalog for products matching the mood board.",
    instruction=PRODUCT_SEARCHER_INSTRUCTION,
    tools=[search_products, get_product_details],
    output_key="product_search_results",
)

# --- Step 3: Generate ideas ---

IDEA_GENERATOR_INSTRUCTION = """\
You are a creative marketing strategist for On, the Swiss running and athletic brand.
Generate exactly 3 Instagram post ideas based on the mood board and product search results.

Mood board:
{mood_board_content}

Available product SKU codes:
{product_search_results}

Each idea must:
- Feature a specific real product from the search results (use actual product name, SKU, and image URL)
- Have a clear imagery direction describing the visual concept for the post image
- Include a compelling headline and Instagram caption
- Specify the visual mood/tone

Guidelines:
- Match the mood board's tone and visual direction
- Use available product SKUs (use get_product_details tool to get product details)
- Write captions in On's brand voice: confident, clean, aspirational, athletic
- Make imagery directions specific enough to guide image generation
- Use real product data (names, SKUs, image URLs) from the search results

Return your output as a valid JSON object with this exact structure:
{{
  "mood_board_source": "<path to the mood board file from the mood board content>",
  "ideas": [
    {{
      "id": "idea_1",
      "product_name": "...",
      "product_sku": "...",
      "product_image_urls": ["...", "...", "..."],
      "imagery_direction": "...",
      "headline": "...",
      "post_description": "...",
      "mood": "..."
    }}
  ]
}}

Return ONLY the JSON, no other text.
"""

idea_generator = LlmAgent(
    name="idea_generator",
    model=TEXT_MODEL,
    description="Generates 3 Instagram post ideas from the mood board and product catalog.",
    instruction=IDEA_GENERATOR_INSTRUCTION,
    output_key="generated_ideas",
    tools=[get_product_details],
)

# --- Step 4: Save ideas ---

IDEA_SAVER_INSTRUCTION = """\
You are a data pipeline step. Your job is to save the generated ideas to disk.

The generated ideas JSON is:
{generated_ideas}

Use `save_ideas` to save this JSON. Pass the JSON string exactly as-is to the tool.
"""

idea_saver = LlmAgent(
    name="idea_saver",
    model=TEXT_MODEL,
    description="Validates and saves the generated post ideas.",
    instruction=IDEA_SAVER_INSTRUCTION,
    tools=[save_ideas],
    output_key="ideation_output",
)

# --- Composite sequential agent ---

ideation_agent = SequentialAgent(
    name="ideation_agent",
    description="Creative marketing strategist that generates Instagram post ideas from a mood board and the On product catalog.",
    sub_agents=[mood_board_reader, product_searcher, idea_generator, idea_saver],
)
