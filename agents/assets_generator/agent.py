"""Assets Generator agent definition — iterates over each idea."""

import os
from collections.abc import AsyncGenerator

from google.adk.agents import BaseAgent, LlmAgent, SequentialAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event

from agents.assets_generator.retry_agent import RetryAgent
from agents.assets_generator.tools import (
    generate_image,
    save_all_assets,
    save_image_prompts,
)
from agents.shared.schemas import STATE_KEY_IDEAS, STATE_KEY_IMAGE_PROMPTS, STATE_KEY_IMAGE_RESULTS

TEXT_MODEL = os.environ.get("TEXT_GENERATION_MODEL", "gemini-2.5-flash")

PROMPT_GENERATOR_INSTRUCTION = """\
You are a visual designer for On, the Swiss running and athletic brand.
Your job is to create detailed image generation prompts for an Instagram post.

1. Read the current idea from state key `current_idea`.
2. For this idea, craft 3 detailed image generation prompts considering "imagery_direction" field of current idea.

IMPORTANT: Adhere to the instruction given in the "imagery_direction" field of current idea!

## Current idea:

{current_idea}
"""

IMAGE_GENERATOR_INSTRUCTION = """\
You are an image generator assistant. Your job is to generate an image for the current prompt.

Call the `generate_image` tool to generate the image. It reads the prompt and product
reference images from state automatically — you do not need to pass any arguments.
"""

ASSET_SAVER_INSTRUCTION = """\
You are a file manager. Your job is to save generated images to disk.

Call `save_all_assets` to save all the generated images from state to the output directory.
Report the results when done.
"""

prompt_generator_agent = LlmAgent(
    name="prompt_generator_agent",
    model=TEXT_MODEL,
    description="Creates detailed image generation prompts for the current idea.",
    instruction=PROMPT_GENERATOR_INSTRUCTION,
    tools=[save_image_prompts],
    include_contents="none",
)

image_generator_agent = LlmAgent(
    name="image_generator_agent",
    model=TEXT_MODEL,
    description="Generates images by calling the generate_image tool.",
    instruction=IMAGE_GENERATOR_INSTRUCTION,
    tools=[generate_image],
    include_contents="none",
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
    model=TEXT_MODEL,
    description="Saves generated image assets to disk.",
    instruction=ASSET_SAVER_INSTRUCTION,
    tools=[save_all_assets],
    include_contents="none",
)


class ForEachPromptAgent(BaseAgent):
    """Iterates over image prompts from state and runs sub-agents for each one."""

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        prompts = ctx.session.state.get(STATE_KEY_IMAGE_PROMPTS, [])
        accumulated_results: list[dict] = []

        for prompt_entry in prompts:
            # Set single prompt for image generator
            ctx.session.state["current_prompt"] = prompt_entry
            # Clear results so RetryAgent can detect fresh success/failure
            ctx.session.state.pop(STATE_KEY_IMAGE_RESULTS, None)

            for sub_agent in self.sub_agents:
                async for event in sub_agent.run_async(ctx):
                    yield event

            # Collect the single result produced by image generator
            results = ctx.session.state.get(STATE_KEY_IMAGE_RESULTS, [])
            if results:
                accumulated_results.append(results[0])

        # Store all accumulated results so asset_saver_agent works unchanged
        ctx.session.state[STATE_KEY_IMAGE_RESULTS] = accumulated_results


# Inner pipeline that processes a single idea
idea_pipeline = SequentialAgent(
    name="idea_pipeline",
    description="Processes a single idea: prompts, image generation, and saving.",
    sub_agents=[
        prompt_generator_agent,
        ForEachPromptAgent(
            name="for_each_prompt",
            description="Iterates over image prompts one by one.",
            sub_agents=[image_generator_with_retry],
        ),
        asset_saver_agent,
    ],
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
