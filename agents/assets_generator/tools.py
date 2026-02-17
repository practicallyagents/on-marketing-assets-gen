"""Tools for the Assets Generator agent."""

import base64
import json
import logging
import os
from pathlib import Path

from google.adk.tools import ToolContext
from google.genai import types
from PIL import Image

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).parent.parent.parent / "output"
IMAGE_MODEL = os.environ.get("IMAGE_GENERATION_MODEL", "gemini-2.5-flash-image")


def generate_image(tool_context: ToolContext) -> str:
    """Generates an image using the Gemini image generation API.

    Reads `current_prompt` and `current_idea` from state, loads product
    reference images from disk, calls the Gemini image generation model
    directly, and stores the result in state.

    Returns:
        Success or error message.
    """
    from google import genai

    from agents.shared.schemas import STATE_KEY_IMAGE_RESULTS

    current_prompt = tool_context.state.get("current_prompt", {})
    current_idea = tool_context.state.get("current_idea", {})

    prompt_text = current_prompt.get("prompt", "")
    idea_id = current_prompt.get("idea_id", "")
    version = current_prompt.get("version", 0)

    if not prompt_text:
        return "Error: no prompt text found in current_prompt state."

    # Load product reference images from disk
    image_paths = current_idea.get("product_image_urls", [])
    reference_images: list[Image.Image] = []
    for path_str in image_paths:
        path = Path(path_str)
        if not path.is_file():
            logger.warning("[generate_image] Skipping missing file: %s", path_str)
            continue
        try:
            img = Image.open(path)
            reference_images.append(img)
            logger.info("[generate_image] Loaded reference image: %s", path.name)
        except Exception as e:
            logger.warning("[generate_image] Failed to load %s: %s", path_str, e)

    # Build contents: text prompt + reference images
    full_prompt = (
        "Generate exactly one image for the prompt below. "
        "The image should be square (1080x1080).\n\n"
        "Product reference photos are provided as input images. Use them as visual "
        "reference to accurately depict the product's real appearance, colors, shape, "
        "and details.\n\n"
        f"## Prompt:\n\n{prompt_text}"
    )
    contents: list = [full_prompt, *reference_images]

    logger.info(
        "[generate_image] Calling %s with %d reference image(s) for %s v%s",
        IMAGE_MODEL,
        len(reference_images),
        idea_id,
        version,
    )

    # Debug output
    print("\n" + "=" * 80)
    print("[DEBUG] IMAGE GENERATION API CALL:")
    print(f"  Model: {IMAGE_MODEL}")
    print(f"  Idea: {idea_id} v{version}")
    print(f"  Reference images: {len(reference_images)}")
    print(f"  Prompt: {prompt_text[:200]}...")
    print("=" * 80 + "\n")

    # Call the Gemini API directly
    client = genai.Client()
    try:
        response = client.models.generate_content(
            model=IMAGE_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"],
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
                image_config=types.ImageConfig(aspect_ratio="1:1"),
            ),
        )
    except Exception as e:
        logger.error("[generate_image] API call failed: %s", e)
        return f"Error: API call failed — {e}"

    # Extract the generated image from response
    if not response.candidates:
        logger.warning("[generate_image] No candidates in response.")
        return "Error: no candidates in API response."

    for part in response.candidates[0].content.parts:
        if part.inline_data and part.inline_data.data:
            image_b64 = base64.b64encode(part.inline_data.data).decode("utf-8")
            tool_context.state[STATE_KEY_IMAGE_RESULTS] = [
                {
                    "idea_id": idea_id,
                    "version": version,
                    "image_base64": image_b64,
                }
            ]
            logger.info(
                "[generate_image] Successfully generated image for %s v%s",
                idea_id,
                version,
            )
            return f"Successfully generated image for {idea_id} v{version}."

    logger.warning("[generate_image] No image found in response parts.")
    return "Error: no image found in API response."


def save_image_prompts(prompts_json: str, tool_context: ToolContext) -> str:
    """Saves the list of image generation prompts for the current idea to shared state.

    Args:
        prompts_json: JSON string containing a list of prompt objects.
            Each object must have: idea_id (str), version (int), prompt (str).
        tool_context: ADK tool context for state access.

    Returns:
        Confirmation message.
    """
    from agents.shared.schemas import STATE_KEY_IMAGE_PROMPTS

    prompts = json.loads(prompts_json)
    if not isinstance(prompts, list) or not prompts:
        return "Error: prompts_json must be a non-empty JSON array."

    for entry in prompts:
        if not all(k in entry for k in ("idea_id", "version", "prompt")):
            return "Error: each prompt entry must have idea_id, version, and prompt."

    tool_context.state[STATE_KEY_IMAGE_PROMPTS] = prompts

    # Debug: print saved image prompts
    print("\n" + "=" * 80)
    print("[DEBUG] SAVED IMAGE PROMPTS:")
    print("=" * 80)
    for entry in prompts:
        print(f"\n--- {entry['idea_id']} v{entry['version']} ---")
        print(entry["prompt"])
    print("=" * 80 + "\n")

    return f"Saved {len(prompts)} image prompts to state."


def save_all_assets(tool_context: ToolContext) -> str:
    """Reads generated image results from state and saves them all to disk.

    Returns:
        Summary of saved files.
    """
    from agents.shared.schemas import STATE_KEY_IMAGE_RESULTS

    results = tool_context.state.get(STATE_KEY_IMAGE_RESULTS)
    if not results:
        return "Error: no image results found in state."

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    saved = []
    for entry in results:
        idea_id = entry["idea_id"]
        version = entry["version"]
        image_b64 = entry["image_base64"]
        filename = f"{idea_id}_v{version}.png"
        output_path = OUTPUT_DIR / filename
        image_bytes = base64.b64decode(image_b64)
        with open(output_path, "wb") as f:
            f.write(image_bytes)
        saved.append(f"{filename} ({len(image_bytes)} bytes)")

    return f"Saved {len(saved)} images: {', '.join(saved)}"


def save_asset(image_base64: str, idea_id: str, version: int) -> str:
    """Saves a generated image asset to the output directory.

    Args:
        image_base64: Base64-encoded PNG image data.
        idea_id: The ID of the post idea this image is for.
        version: Version number of this image variation (1, 2, or 3).

    Returns:
        Confirmation message with the saved file path.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{idea_id}_v{version}.png"
    output_path = OUTPUT_DIR / filename

    image_bytes = base64.b64decode(image_base64)
    with open(output_path, "wb") as f:
        f.write(image_bytes)

    return f"Saved image to {output_path} ({len(image_bytes)} bytes)"
