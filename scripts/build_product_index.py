#!/usr/bin/env python3
"""Build a lightweight SKU → file path index from scraped product data."""

import json
import glob
import re
import os
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
PRODUCTS_DIR = DATA_DIR / "products"
OUTPUT_PATH = DATA_DIR / "product_index.json"


def extract_sku_from_filename(filename: str) -> str | None:
    """Extract SKU identifier from a product filename as fallback."""
    # Filename pattern: products-...-SKU.json
    match = re.search(r"-([A-Z0-9]{5,})\.json$", filename, re.IGNORECASE)
    if match:
        return match.group(1)
    return None


def extract_skus_from_structured_data(data: dict) -> list[str]:
    """Extract all SKUs from a product file's JSON-LD structured data."""
    skus = []
    json_ld = data.get("structuredData", {}).get("jsonLd", [])
    for ld in json_ld:
        graph = ld.get("@graph", [])
        for node in graph:
            if node.get("@type") == "ProductGroup":
                for variant in node.get("hasVariant", []):
                    sku = variant.get("sku", "")
                    if sku:
                        skus.append(sku)
            # Also check ItemList wrapping ProductGroups
            if node.get("@type") == "ItemList":
                for list_item in node.get("itemListElement", []):
                    item = list_item.get("item", {})
                    if item.get("@type") == "ProductGroup":
                        for variant in item.get("hasVariant", []):
                            sku = variant.get("sku", "")
                            if sku:
                                skus.append(sku)
    return skus


def main():
    print("Building product index...")

    product_files = sorted(glob.glob(str(PRODUCTS_DIR / "*.json")))
    print(f"Found {len(product_files)} product files")

    index: dict[str, str] = {}

    for filepath in product_files:
        rel_path = os.path.relpath(filepath, DATA_DIR.parent)
        with open(filepath) as f:
            data = json.load(f)

        skus = extract_skus_from_structured_data(data)

        if skus:
            for sku in skus:
                if sku not in index:
                    index[sku] = rel_path
        else:
            # Fallback: extract SKU from filename
            sku = extract_sku_from_filename(os.path.basename(filepath))
            if sku and sku not in index:
                index[sku] = rel_path

    print(f"Indexed {len(index)} SKUs from {len(product_files)} files")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(index, f, indent=2)

    size_kb = os.path.getsize(OUTPUT_PATH) / 1024
    print(f"Written to {OUTPUT_PATH} ({size_kb:.0f} KB)")


if __name__ == "__main__":
    main()
