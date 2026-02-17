"""Shared Pydantic models for the JSON contract between agents."""

from pydantic import BaseModel


class PostIdea(BaseModel):
    id: str
    product_name: str
    product_sku: str
    product_image_url: str
    imagery_direction: str
    headline: str
    post_description: str
    mood: str


class IdeasOutput(BaseModel):
    mood_board_source: str
    generated_at: str
    ideas: list[PostIdea]


STATE_KEY_IDEAS = "ideas_output"
