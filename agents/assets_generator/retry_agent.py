"""RetryAgent — wraps a sub-agent with exponential-backoff retries."""

import asyncio
import logging
from collections.abc import AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event

from agents.shared.schemas import STATE_KEY_IMAGE_RESULTS

logger = logging.getLogger(__name__)


class RetryAgent(BaseAgent):
    """Runs a single sub-agent and retries on failure with exponential backoff.

    A "failure" is defined as the sub-agent finishing without populating
    ``STATE_KEY_IMAGE_RESULTS`` in session state.
    """

    max_retries: int = 3
    base_delay: float = 2.0

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        sub_agent = self.sub_agents[0]

        for attempt in range(1, self.max_retries + 1):
            logger.info(
                "[RetryAgent] Attempt %d/%d for '%s'",
                attempt,
                self.max_retries,
                sub_agent.name,
            )

            async for event in sub_agent.run_async(ctx):
                yield event

            results = ctx.session.state.get(STATE_KEY_IMAGE_RESULTS)
            if results:
                logger.info(
                    "[RetryAgent] Success on attempt %d — got %d image(s).",
                    attempt,
                    len(results),
                )
                return

            if attempt < self.max_retries:
                delay = self.base_delay * (2 ** (attempt - 1))
                logger.warning(
                    "[RetryAgent] No images produced on attempt %d. "
                    "Retrying in %.1fs…",
                    attempt,
                    delay,
                )
                # Clear stale results so the next attempt starts fresh
                ctx.session.state.pop(STATE_KEY_IMAGE_RESULTS, None)
                await asyncio.sleep(delay)
            else:
                logger.error(
                    "[RetryAgent] All %d attempts exhausted — no images produced.",
                    self.max_retries,
                )
