"""ADK app entry point — root agent definition."""

from google.adk.agents import SequentialAgent

from agents.ideation.agent import ideation_agent
from agents.assets_generator.agent import assets_generator_agent

root_agent = SequentialAgent(
    name="instagram_post_generator",
    description="End-to-end Instagram post generation pipeline: ideation then asset creation.",
    sub_agents=[ideation_agent, assets_generator_agent],
)
