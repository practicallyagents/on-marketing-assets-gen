"""Assets Generator agent definition — iterates over each idea."""

import os
from collections.abc import AsyncGenerator

from google.adk.agents import BaseAgent, LlmAgent, SequentialAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.genai import types

from agents.assets_generator.callbacks import extract_images_to_state, inject_product_images
from agents.assets_generator.retry_agent import RetryAgent
from agents.assets_generator.tools import (
    save_all_assets,
    save_image_prompts,
)
from agents.shared.schemas import STATE_KEY_IDEAS

IMAGE_MODEL = os.environ.get("IMAGE_GENERATION_MODEL", "gemini-2.5-flash-image")

PROMPT_GENERATOR_INSTRUCTION = """\
You are a visual designer for On, the Swiss running and athletic brand.
Your job is to create detailed image generation prompts for an Instagram post.

## Your workflow:

1. Read the current idea from state key `current_idea`.
2. For this idea, craft 3 detailed image generation prompts considering product images, imagery direction and the idea. Some directions you can use:
   - Version 1: Product-focused hero shot
   - Version 2: Lifestyle/action shot with the product
3. Each prompt should describe the image in detail, referencing:
   - The product's appearance and key features
   - On's brand aesthetic: clean, minimal, athletic, premium
   - The idea's imagery_direction and mood
   - Square 1080x1080 Instagram format
   - On brand colors: black, white, and accent colors from the product
   - Natural lighting, outdoor/urban settings
   Note: The image generator will receive the actual product photos as visual
   reference, so your prompts can instruct it to match the real product's
   colors, shapes, and details faithfully.
4. Use `save_image_prompts` to save the 3 prompts as a JSON array.
   Each entry must have: idea_id (str), version (int 1-3), prompt (str).

## Current idea:

{current_idea}
"""

IMAGE_GENERATOR_INSTRUCTION = """\
You are an image generator. Generate one image for each of the prompts below.
Generate all images in a single response. Each image should be square (1080x1080).

Product reference photos are provided as input images. Use them as visual reference
to accurately depict the product's real appearance, colors, shape, and details.

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
    description="Creates detailed image generation prompts for the current idea.",
    instruction=PROMPT_GENERATOR_INSTRUCTION,
    tools=[save_image_prompts],
    include_contents="none",
)

image_generator_agent = LlmAgent(
    name="image_generator_agent",
    model=IMAGE_MODEL,
    description="Generates images from prompts using native image generation.",
    instruction=IMAGE_GENERATOR_INSTRUCTION,
    tools=[],
    include_contents="none",
    before_model_callback=inject_product_images,
    after_model_callback=extract_images_to_state,
    generate_content_config=types.GenerateContentConfig(
        safety_settings=[
            types.SafetySetting(
                category=c, threshold=types.HarmBlockThreshold.BLOCK_NONE
            )
            for c in [
                types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                types.HarmCategory.HARM_CATEGORY_CIVIC_INTEGRITY,
            ]
        ],
    ),
)

image_generator_with_retry = RetryAgent(
    name="image_generator_with_retry",
    description="Retries image generation on failure.",
    sub_agents=[image_generator_agent],
    max_retries=3,
    base_delay=2.0,
)

asset_saver_agent = LlmAgent(
    name="asset_saver_agent",
    model="gemini-2.5-flash",
    description="Saves generated image assets to disk.",
    instruction=ASSET_SAVER_INSTRUCTION,
    tools=[save_all_assets],
    include_contents="none",
)

# Inner pipeline that processes a single idea
idea_pipeline = SequentialAgent(
    name="idea_pipeline",
    description="Processes a single idea: prompts, image generation, and saving.",
    sub_agents=[prompt_generator_agent, image_generator_with_retry, asset_saver_agent],
)


class ForEachIdeaAgent(BaseAgent):
    """Iterates over ideas from state and runs the sub-agent pipeline for each."""

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        ideas_output = ctx.session.state.get(STATE_KEY_IDEAS, {})
        ideas = ideas_output.get("ideas", [])

        for idea in ideas:
            ctx.session.state["current_idea"] = idea
            for sub_agent in self.sub_agents:
                async for event in sub_agent.run_async(ctx):
                    yield event


assets_generator_agent = ForEachIdeaAgent(
    name="assets_generator_agent",
    description="Visual designer that generates Instagram post images, processing each idea in a loop.",
    sub_agents=[idea_pipeline],
)
