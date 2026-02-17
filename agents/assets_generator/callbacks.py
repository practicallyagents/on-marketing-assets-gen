"""Callbacks for the Assets Generator sub-agents."""

import base64

from google.adk.agents.callback_context import CallbackContext
from google.genai.types import GenerateContentResponse

from agents.shared.schemas import STATE_KEY_IMAGE_PROMPTS, STATE_KEY_IMAGE_RESULTS


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

    image_results = []
    image_index = 0

    parts = []
    if llm_response.content and llm_response.content.parts:
        parts = llm_response.content.parts
    elif llm_response.candidates:
        for candidate in llm_response.candidates:
            if candidate.content and candidate.content.parts:
                parts.extend(candidate.content.parts)

    for part in parts:
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
