"""Tools for the Ideation agent."""

import glob
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from google.adk.tools import ToolContext

PROJECT_ROOT = Path(__file__).parent.parent.parent
PRODUCT_INDEX_PATH = PROJECT_ROOT / "data" / "product_index.json"
PRODUCTS_DIR = PROJECT_ROOT / "data" / "products"
COLLECTIONS_DIR = PROJECT_ROOT / "data" / "collections"
OUTPUT_DIR = PROJECT_ROOT / "output"

_sku_index_cache: dict[str, str] | None = None
_products_cache: list[dict] | None = None


def _load_sku_index() -> dict[str, str]:
    """Load the SKU → file path index."""
    global _sku_index_cache
    if _sku_index_cache is None:
        with open(PRODUCT_INDEX_PATH) as f:
            _sku_index_cache = json.load(f)
    return _sku_index_cache


def _extract_category_from_url(url: str) -> str:
    """Infer category (shoes/apparel/accessories) from URL."""
    url_lower = url.lower()
    if "shoes" in url_lower:
        return "shoes"
    elif "apparel" in url_lower:
        return "apparel"
    elif "accessories" in url_lower:
        return "accessories"
    return "other"


def _extract_products_from_file(filepath: str) -> list[dict]:
    """Extract product variants from a single product file."""
    with open(filepath) as f:
        data = json.load(f)

    products = []
    json_ld = data.get("structuredData", {}).get("jsonLd", [])

    for ld in json_ld:
        graph = ld.get("@graph", [])
        for node in graph:
            groups = []
            if node.get("@type") == "ProductGroup":
                groups.append(node)
            elif node.get("@type") == "ItemList":
                for list_item in node.get("itemListElement", []):
                    item = list_item.get("item", {})
                    if item.get("@type") == "ProductGroup":
                        groups.append(item)

            for group in groups:
                group_name = group.get("name", "")
                group_desc = group.get("description", "")
                group_url = group.get("url", "")

                for variant in group.get("hasVariant", []):
                    sku = variant.get("sku", "")
                    if not sku:
                        continue
                    offers = variant.get("offers", {})
                    product_url = offers.get("url", group_url)
                    products.append({
                        "name": variant.get("name", ""),
                        "sku": sku,
                        "product_group": group_name,
                        "description": group_desc,
                        "color": variant.get("color", ""),
                        "price": offers.get("price"),
                        "image_url": variant.get("image", ""),
                        "product_url": product_url,
                        "category": _extract_category_from_url(product_url),
                    })

    # Fallback: if no structured data, try content fields
    if not products:
        url = data.get("url", "")
        content = data.get("content", {})
        name = content.get("name", "")
        if name and name != "Shop all":
            match = re.search(r"-([A-Z0-9]{5,})$", url.rstrip("/").split("/")[-1], re.IGNORECASE)
            sku = match.group(1) if match else ""
            if sku:
                price = None
                sku_field = content.get("sku", "")
                price_match = re.search(r"\$(\d+(?:\.\d{2})?)", sku_field)
                if price_match:
                    price = float(price_match.group(1))

                products.append({
                    "name": name,
                    "sku": sku,
                    "product_group": "",
                    "description": "",
                    "color": "",
                    "price": price,
                    "image_url": "",
                    "product_url": url,
                    "category": _extract_category_from_url(url),
                })

    return products


def _load_all_products() -> list[dict]:
    """Load and cache all product data from product files."""
    global _products_cache
    if _products_cache is not None:
        return _products_cache

    sku_index = _load_sku_index()
    # Get unique file paths from the index
    unique_paths = set(sku_index.values())

    all_products: list[dict] = []
    seen_skus: set[str] = set()

    for rel_path in sorted(unique_paths):
        filepath = str(PROJECT_ROOT / rel_path)
        for product in _extract_products_from_file(filepath):
            if product["sku"] not in seen_skus:
                seen_skus.add(product["sku"])
                all_products.append(product)

    _products_cache = all_products
    return _products_cache


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
    """Searches the product catalog by keyword and returns matching products.

    Use this to find specific products from the On catalog that match the
    mood board's themes or product requirements. Search by product name,
    category, color, or description.

    Args:
        query: Search query string (e.g. "Cloud 6", "running shoes", "black apparel").

    Returns:
        JSON string with matching products (max 20 results).
    """
    products = _load_all_products()
    query_lower = query.lower()
    keywords = query_lower.split()

    matches = []
    for product in products:
        searchable = " ".join([
            product.get("name", ""),
            product.get("product_group", ""),
            product.get("description", ""),
            product.get("color", ""),
            product.get("category", ""),
        ]).lower()

        if all(kw in searchable for kw in keywords):
            matches.append(product)

        if len(matches) >= 20:
            break

    result = {
        "query": query,
        "match_count": len(matches),
        "products": matches,
    }

    if not matches:
        # Search collection files directly for context
        matching_collections = []
        collection_files = sorted(glob.glob(str(COLLECTIONS_DIR / "*.json")))
        for cpath in collection_files:
            with open(cpath) as f:
                cdata = json.load(f)
            metadata = cdata.get("metadata", {})
            og = metadata.get("openGraph", {})
            content = cdata.get("content", {})
            title = content.get("title") or og.get("og:title") or metadata.get("title", "")
            description = og.get("og:description") or metadata.get("description", "")
            if query_lower in title.lower() or query_lower in description.lower():
                matching_collections.append({
                    "name": title,
                    "description": description,
                    "url": cdata.get("url", ""),
                    "image_url": og.get("og:image", ""),
                })
            if len(matching_collections) >= 5:
                break
        if matching_collections:
            result["related_collections"] = matching_collections

    return json.dumps(result, indent=2)


def save_ideas(ideas_json: str, tool_context: ToolContext) -> str:
    """Validates and saves the generated post ideas to output/ideas.json.

    The ideas_json must be a valid JSON string matching the IdeasOutput schema:
    {
        "mood_board_source": "path to mood board",
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
    data["generated_at"] = datetime.now(timezone.utc).isoformat()
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
