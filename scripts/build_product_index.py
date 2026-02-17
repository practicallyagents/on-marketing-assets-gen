#!/usr/bin/env python3
"""Build a lightweight product index from the scraped data."""

import json
import glob
import re
import os
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
PRODUCTS_DIR = DATA_DIR / "products"
COLLECTIONS_DIR = DATA_DIR / "collections"
OUTPUT_PATH = DATA_DIR / "product_index.json"


def extract_sku_from_url(url: str) -> str | None:
    """Extract SKU identifier from a product variant URL."""
    # URL pattern: .../color-type-SKU
    parts = url.rstrip("/").split("/")
    if len(parts) >= 1:
        last = parts[-1]
        # SKU is usually the last hyphen-separated segment
        match = re.search(r"-([A-Z0-9]{5,})$", last, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def extract_category_from_url(url: str) -> str:
    """Infer category (shoes/apparel/accessories) from URL."""
    url_lower = url.lower()
    if "shoes" in url_lower:
        return "shoes"
    elif "apparel" in url_lower:
        return "apparel"
    elif "accessories" in url_lower:
        return "accessories"
    return "other"


def extract_from_structured_data(files: list[str]) -> dict[str, dict]:
    """Extract product data from structured data (richest source)."""
    products = {}

    for filepath in files:
        with open(filepath) as f:
            data = json.load(f)

        json_ld = data.get("structuredData", {}).get("jsonLd", [])
        if not json_ld:
            continue

        for ld in json_ld:
            graph = ld.get("@graph", [])
            for node in graph:
                if node.get("@type") != "ItemList":
                    continue
                for list_item in node.get("itemListElement", []):
                    item = list_item.get("item", {})
                    if item.get("@type") != "ProductGroup":
                        continue

                    group_id = item.get("productGroupID", "")
                    group_name = item.get("name", "")
                    group_desc = item.get("description", "")
                    group_url = item.get("url", "")

                    for variant in item.get("hasVariant", []):
                        sku = variant.get("sku", "")
                        if sku in products:
                            continue

                        offers = variant.get("offers", {})
                        products[sku] = {
                            "name": variant.get("name", ""),
                            "sku": sku,
                            "product_group": group_name,
                            "product_group_id": group_id,
                            "description": group_desc,
                            "color": variant.get("color", ""),
                            "image_url": variant.get("image", ""),
                            "product_url": offers.get("url", group_url),
                            "price": offers.get("price"),
                            "currency": offers.get("priceCurrency", "USD"),
                            "availability": "InStock" if "InStock" in offers.get("availability", "") else "OutOfStock",
                            "category": extract_category_from_url(offers.get("url", group_url)),
                        }
    return products


def extract_from_content_files(files: list[str], existing_skus: set[str]) -> dict[str, dict]:
    """Extract product data from content fields of individual files."""
    products = {}

    for filepath in files:
        with open(filepath) as f:
            data = json.load(f)

        url = data.get("url", "")
        content = data.get("content", {})
        name = content.get("name", "")

        if not name or name == "Shop all":
            continue

        sku = extract_sku_from_url(url)
        if not sku or sku in existing_skus or sku in products:
            continue

        # Try to extract price from the garbled sku field
        price = None
        sku_field = content.get("sku", "")
        price_match = re.search(r"\$(\d+(?:\.\d{2})?)", sku_field)
        if price_match:
            price = float(price_match.group(1))

        products[sku] = {
            "name": name,
            "sku": sku,
            "product_group": "",
            "product_group_id": "",
            "description": "",
            "color": "",
            "image_url": "",
            "product_url": url,
            "price": price,
            "currency": "USD",
            "availability": "Unknown",
            "category": extract_category_from_url(url),
        }
    return products


def extract_collections(files: list[str]) -> list[dict]:
    """Extract collection summaries."""
    collections = []
    for filepath in files:
        with open(filepath) as f:
            data = json.load(f)

        metadata = data.get("metadata", {})
        og = metadata.get("openGraph", {})
        content = data.get("content", {})

        title = content.get("title") or og.get("og:title") or metadata.get("title", "")
        description = og.get("og:description") or metadata.get("description", "")
        image = og.get("og:image", "")

        collections.append({
            "name": title,
            "description": description,
            "url": data.get("url", ""),
            "image_url": image,
        })
    return collections


def main():
    print("Building product index...")

    product_files = sorted(glob.glob(str(PRODUCTS_DIR / "*.json")))
    collection_files = sorted(glob.glob(str(COLLECTIONS_DIR / "*.json")))

    print(f"Found {len(product_files)} product files, {len(collection_files)} collection files")

    # Phase 1: Extract from structured data (richest source)
    structured_products = extract_from_structured_data(product_files)
    print(f"Extracted {len(structured_products)} products from structured data")

    # Phase 2: Supplement from individual file content
    content_products = extract_from_content_files(product_files, set(structured_products.keys()))
    print(f"Extracted {len(content_products)} additional products from content fields")

    # Merge
    all_products = {**structured_products, **content_products}
    print(f"Total unique products: {len(all_products)}")

    # Extract collections
    collections = extract_collections(collection_files)
    print(f"Extracted {len(collections)} collections")

    # Build index
    index = {
        "generated_at": "2026-02-17",
        "product_count": len(all_products),
        "collection_count": len(collections),
        "products": list(all_products.values()),
        "collections": collections,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(index, f, indent=2)

    size_kb = os.path.getsize(OUTPUT_PATH) / 1024
    print(f"Written to {OUTPUT_PATH} ({size_kb:.0f} KB)")


if __name__ == "__main__":
    main()
