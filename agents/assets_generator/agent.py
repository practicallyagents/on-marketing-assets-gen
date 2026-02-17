"""Assets Generator agent definition — sequential pipeline."""

from google.adk.agents import LlmAgent, SequentialAgent

from agents.assets_generator.callbacks import extract_images_to_state
from agents.assets_generator.tools import (
    load_ideas,
    save_all_assets,
    save_image_prompts,
)

PROMPT_GENERATOR_INSTRUCTION = """\
You are a visual designer for On, the Swiss running and athletic brand.
Your job is to create detailed image generation prompts for Instagram posts.

## Your workflow:

1. Use `load_ideas` to retrieve the post ideas from the ideation step.
2. For each of the 3 post ideas, craft 3 detailed image generation prompts (9 total).
   - Version 1: Product-focused hero shot
   - Version 2: Lifestyle/action shot with the product
   - Version 3: Artistic/mood-driven composition
3. Each prompt should describe the image in detail, referencing:
   - The product's appearance and key features
   - On's brand aesthetic: clean, minimal, athletic, premium
   - The idea's imagery_direction and mood
   - Square 1080x1080 Instagram format
   - On brand colors: black, white, and accent colors from the product
   - Natural lighting, outdoor/urban settings
4. Use `save_image_prompts` to save all 9 prompts as a JSON array.
   Each entry must have: idea_id (str), version (int 1-3), prompt (str).
"""

IMAGE_GENERATOR_INSTRUCTION = """\
You are an image generator. Generate one image for each of the prompts below.
Generate all images in a single response. Each image should be square (1080x1080).

## Prompts:

{image_prompts}
"""

ASSET_SAVER_INSTRUCTION = """\
You are a file manager. Your job is to save generated images to disk.

Call `save_all_assets` to save all the generated images from state to the output directory.
Report the results when done.
"""

prompt_generator_agent = LlmAgent(
    name="prompt_generator_agent",
    model="gemini-2.5-flash",
    description="Creates detailed image generation prompts from post ideas.",
    instruction=PROMPT_GENERATOR_INSTRUCTION,
    tools=[load_ideas, save_image_prompts],
)

image_generator_agent = LlmAgent(
    name="image_generator_agent",
    model="gemini-2.5-flash-image",
    description="Generates images from prompts using native image generation.",
    instruction=IMAGE_GENERATOR_INSTRUCTION,
    tools=[],
    include_contents="none",
    after_model_callback=extract_images_to_state,
)

asset_saver_agent = LlmAgent(
    name="asset_saver_agent",
    model="gemini-2.5-flash",
    description="Saves generated image assets to disk.",
    instruction=ASSET_SAVER_INSTRUCTION,
    tools=[save_all_assets],
    include_contents="none",
)

assets_generator_agent = SequentialAgent(
    name="assets_generator_agent",
    description="Visual designer that generates Instagram post images based on post ideas.",
    sub_agents=[prompt_generator_agent, image_generator_agent, asset_saver_agent],
)
