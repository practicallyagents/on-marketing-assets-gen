"""Standalone entrypoint to run the agent pipeline with a mood board file."""

import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from agents.agent import root_agent

load_dotenv()


async def main(mood_board_path: str) -> None:
    resolved = Path(mood_board_path).resolve()
    if not resolved.is_file():
        print(f"Error: file not found: {resolved}", file=sys.stderr)
        sys.exit(1)

    session_service = InMemorySessionService()
    runner = Runner(
        agent=root_agent,
        app_name="instagram_post_generator",
        session_service=session_service,
    )

    session = await session_service.create_session(
        app_name="instagram_post_generator",
        user_id="cli_user",
    )

    prompt = f"Genrate ideas based on {resolved}"
    content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=prompt)],
    )

    print(f"Running pipeline with: {resolved}\n")

    async for event in runner.run_async(
        user_id=session.user_id,
        session_id=session.id,
        new_message=content,
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(part.text)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <mood_board.md>", file=sys.stderr)
        sys.exit(1)

    asyncio.run(main(sys.argv[1]))
