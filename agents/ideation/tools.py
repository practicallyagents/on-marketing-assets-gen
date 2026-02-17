"""Tools for the Ideation agent."""

import json
from datetime import datetime, timezone
from pathlib import Path

from google.adk.tools import ToolContext

PROJECT_ROOT = Path(__file__).parent.parent.parent
PRODUCT_INDEX_PATH = PROJECT_ROOT / "data" / "product_index.json"
OUTPUT_DIR = PROJECT_ROOT / "output"

_product_index_cache: dict | None = None


def _load_product_index() -> dict:
    global _product_index_cache
    if _product_index_cache is None:
        with open(PRODUCT_INDEX_PATH) as f:
            _product_index_cache = json.load(f)
    return _product_index_cache


def read_mood_board(path: str) -> str:
    """Reads a mood board markdown file and returns its contents.

    Args:
        path: Path to the mood board markdown file, relative to the project root.

    Returns:
        The contents of the mood board file.
    """
    full_path = PROJECT_ROOT / path
    with open(full_path) as f:
        return f.read()


def search_products(query: str) -> str:
    """Searches the product index by keyword and returns matching products.

    Use this to find specific products from the On catalog that match the
    mood board's themes or product requirements. Search by product name,
    category, color, or description.

    Args:
        query: Search query string (e.g. "Cloud 6", "running shoes", "black apparel").

    Returns:
        JSON string with matching products (max 20 results).
    """
    index = _load_product_index()
    query_lower = query.lower()
    keywords = query_lower.split()

    matches = []
    for product in index["products"]:
        searchable = " ".join([
            product.get("name", ""),
            product.get("product_group", ""),
            product.get("description", ""),
            product.get("color", ""),
            product.get("category", ""),
        ]).lower()

        if all(kw in searchable for kw in keywords):
            matches.append({
                "name": product["name"],
                "sku": product["sku"],
                "product_group": product.get("product_group", ""),
                "description": product.get("description", ""),
                "color": product.get("color", ""),
                "price": product.get("price"),
                "image_url": product.get("image_url", ""),
                "product_url": product.get("product_url", ""),
                "category": product.get("category", ""),
            })

        if len(matches) >= 20:
            break

    result = {
        "query": query,
        "match_count": len(matches),
        "products": matches,
    }

    if not matches:
        # Also include collection info for context
        matching_collections = [
            c for c in index.get("collections", [])
            if query_lower in c.get("name", "").lower()
            or query_lower in c.get("description", "").lower()
        ]
        if matching_collections:
            result["related_collections"] = matching_collections[:5]

    return json.dumps(result, indent=2)


def save_ideas(ideas_json: str, tool_context: ToolContext) -> str:
    """Validates and saves the generated post ideas to output/ideas.json.

    The ideas_json must be a valid JSON string matching the IdeasOutput schema:
    {
        "mood_board_source": "path to mood board",
        "generated_at": "ISO timestamp",
        "ideas": [
            {
                "id": "unique id",
                "product_name": "product name",
                "product_sku": "SKU code",
                "product_image_url": "URL to product image",
                "imagery_direction": "visual concept description",
                "headline": "post headline",
                "post_description": "Instagram caption",
                "mood": "visual mood/tone"
            }
        ]
    }

    Args:
        ideas_json: JSON string containing the post ideas.

    Returns:
        Confirmation message with the output file path.
    """
    from agents.shared.schemas import IdeasOutput, STATE_KEY_IDEAS

    data = json.loads(ideas_json)
    # Validate against schema
    validated = IdeasOutput(**data)
    validated_dict = validated.model_dump()

    # Store in session state for downstream agents
    tool_context.state[STATE_KEY_IDEAS] = validated_dict

    # Also write to filesystem as a debug artifact
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "ideas.json"
    with open(output_path, "w") as f:
        json.dump(validated_dict, f, indent=2)

    return f"Saved {len(validated.ideas)} ideas to {output_path}"
