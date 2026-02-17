"""Callbacks for the Assets Generator sub-agents."""

import base64
import logging
import mimetypes
from pathlib import Path

from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.genai import types
from google.genai.types import GenerateContentResponse

from agents.shared.schemas import STATE_KEY_IMAGE_PROMPTS, STATE_KEY_IMAGE_RESULTS

logger = logging.getLogger(__name__)


def inject_product_images(
    callback_context: CallbackContext, llm_request: LlmRequest
) -> None:
    """before_model_callback for image_generator_agent.

    Reads the current idea's product_image_urls from state, loads each image
    file from disk, and prepends them as inline_data parts to the LLM request
    so the image generation model can use them as visual reference.
    """
    current_idea = callback_context.state.get("current_idea", {})
    image_paths = current_idea.get("product_image_urls", [])

    if not image_paths:
        return None

    image_parts = []
    for path_str in image_paths:
        path = Path(path_str)
        if not path.is_file():
            print(f"[inject_product_images] Skipping missing file: {path_str}")
            continue

        mime_type, _ = mimetypes.guess_type(path_str)
        if not mime_type or not mime_type.startswith("image/"):
            mime_type = "image/jpeg"

        image_data = path.read_bytes()
        image_parts.append(
            types.Part(inline_data=types.Blob(mime_type=mime_type, data=image_data))
        )
        print(f"[inject_product_images] Loaded {path.name} ({mime_type})")

    if not image_parts:
        return None

    text_part = types.Part(
        text="Here are the product reference photos — use these as visual reference for accurate product appearance:"
    )
    reference_content = types.Content(
        role="user", parts=[text_part, *image_parts]
    )
    llm_request.contents.insert(0, reference_content)
    print(f"[inject_product_images] Injected {len(image_parts)} product image(s)")

    return None


def extract_images_to_state(
    callback_context: CallbackContext, llm_response: GenerateContentResponse
) -> None:
    """after_model_callback for image_generator_agent.

    Iterates over the model response parts, finds inline_data parts
    (generated images), base64-encodes them, maps each to the corresponding
    prompt entry by index, and stores the list in state["image_results"].
    Returns None so the original LLM response is preserved.
    """
    prompts = callback_context.state.get(STATE_KEY_IMAGE_PROMPTS, [])

    # Log response metadata
    candidates = getattr(llm_response, "candidates", None)
    if candidates:
        for i, candidate in enumerate(candidates):
            finish_reason = getattr(candidate, "finish_reason", None)
            safety_ratings = getattr(candidate, "safety_ratings", None)
            logger.info(
                "[extract_images_to_state] candidate %d: finish_reason=%s",
                i,
                finish_reason,
            )
            if safety_ratings:
                for rating in safety_ratings:
                    logger.info(
                        "[extract_images_to_state]   safety: %s = %s",
                        getattr(rating, "category", "?"),
                        getattr(rating, "probability", "?"),
                    )

    # Handle error/empty responses gracefully
    if not llm_response.content or not llm_response.content.parts:
        error_code = getattr(llm_response, "error_code", None)
        finish_reason = getattr(llm_response, "finish_reason", None)
        logger.warning(
            "[extract_images_to_state] No content in response. "
            "finish_reason=%s, error_code=%s, expected %d image(s)",
            finish_reason,
            error_code,
            len(prompts),
        )
        return None

    image_results = []
    image_index = 0

    for part in llm_response.content.parts:
        if part.inline_data and part.inline_data.data:
            image_b64 = base64.b64encode(part.inline_data.data).decode("utf-8")
            if image_index < len(prompts):
                prompt_entry = prompts[image_index]
                image_results.append(
                    {
                        "idea_id": prompt_entry["idea_id"],
                        "version": prompt_entry["version"],
                        "image_base64": image_b64,
                    }
                )
            image_index += 1

    if image_results:
        callback_context.state[STATE_KEY_IMAGE_RESULTS] = image_results

    return None
