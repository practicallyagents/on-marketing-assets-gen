"""Tests for ADK state-based handoff between ideation and assets_generator agents."""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from agents.shared.schemas import STATE_KEY_IDEAS, IdeasOutput

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_IDEAS = {
    "mood_board_source": "mood_boards/sample_mood_board.md",
    "generated_at": "2026-02-17T00:00:00Z",
    "ideas": [
        {
            "id": "idea_1",
            "product_name": "Cloud 6",
            "product_sku": "SKU001",
            "product_image_url": "https://example.com/cloud6.jpg",
            "imagery_direction": "Minimalist hero shot on white background",
            "headline": "Run on Clouds",
            "post_description": "Experience the next generation of running.",
            "mood": "clean and energetic",
        }
    ],
}


@pytest.fixture()
def mock_tool_context():
    """Create a mock ToolContext with a plain dict as state."""
    ctx = MagicMock()
    ctx.state = {}
    return ctx


@pytest.fixture()
def output_dir(tmp_path, monkeypatch):
    """Redirect OUTPUT_DIR to a temp directory for both tool modules."""
    import agents.ideation.tools as ideation_tools
    import agents.assets_generator.tools as assets_tools

    monkeypatch.setattr(ideation_tools, "OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(assets_tools, "OUTPUT_DIR", tmp_path)
    # Also patch PROJECT_ROOT for fallback path in load_ideas
    monkeypatch.setattr(assets_tools, "PROJECT_ROOT", tmp_path)
    (tmp_path / "output").mkdir(exist_ok=True)
    return tmp_path


# ---------------------------------------------------------------------------
# save_ideas tests
# ---------------------------------------------------------------------------


class TestSaveIdeas:
    def test_stores_ideas_in_state(self, mock_tool_context, output_dir):
        from agents.ideation.tools import save_ideas

        result = save_ideas(json.dumps(SAMPLE_IDEAS), mock_tool_context)

        assert STATE_KEY_IDEAS in mock_tool_context.state
        stored = mock_tool_context.state[STATE_KEY_IDEAS]
        assert len(stored["ideas"]) == 1
        assert stored["ideas"][0]["id"] == "idea_1"
        assert "Saved 1 ideas" in result

    def test_writes_file_as_debug_artifact(self, mock_tool_context, output_dir):
        from agents.ideation.tools import save_ideas

        save_ideas(json.dumps(SAMPLE_IDEAS), mock_tool_context)

        ideas_file = output_dir / "ideas.json"
        assert ideas_file.exists()
        data = json.loads(ideas_file.read_text())
        assert data["ideas"][0]["product_name"] == "Cloud 6"

    def test_state_and_file_match(self, mock_tool_context, output_dir):
        from agents.ideation.tools import save_ideas

        save_ideas(json.dumps(SAMPLE_IDEAS), mock_tool_context)

        file_data = json.loads((output_dir / "ideas.json").read_text())
        assert mock_tool_context.state[STATE_KEY_IDEAS] == file_data

    def test_rejects_invalid_json(self, mock_tool_context, output_dir):
        from agents.ideation.tools import save_ideas

        with pytest.raises(json.JSONDecodeError):
            save_ideas("not json", mock_tool_context)

    def test_rejects_invalid_schema(self, mock_tool_context, output_dir):
        from agents.ideation.tools import save_ideas

        with pytest.raises(Exception):
            save_ideas(json.dumps({"bad": "data"}), mock_tool_context)


# ---------------------------------------------------------------------------
# load_ideas tests
# ---------------------------------------------------------------------------


class TestLoadIdeas:
    def test_reads_from_state(self, mock_tool_context):
        from agents.assets_generator.tools import load_ideas

        mock_tool_context.state[STATE_KEY_IDEAS] = SAMPLE_IDEAS

        result = json.loads(load_ideas(mock_tool_context))
        assert result["ideas"][0]["id"] == "idea_1"

    def test_falls_back_to_file(self, mock_tool_context, output_dir):
        from agents.assets_generator.tools import load_ideas

        # State is empty, write fallback file
        fallback_path = output_dir / "output" / "ideas.json"
        fallback_path.parent.mkdir(parents=True, exist_ok=True)
        fallback_path.write_text(json.dumps(SAMPLE_IDEAS))

        result = json.loads(load_ideas(mock_tool_context))
        assert result["ideas"][0]["id"] == "idea_1"

    def test_state_preferred_over_file(self, mock_tool_context, output_dir):
        from agents.assets_generator.tools import load_ideas

        # Put different data in state vs file
        state_ideas = {**SAMPLE_IDEAS, "mood_board_source": "from_state"}
        file_ideas = {**SAMPLE_IDEAS, "mood_board_source": "from_file"}

        mock_tool_context.state[STATE_KEY_IDEAS] = state_ideas
        fallback_path = output_dir / "output" / "ideas.json"
        fallback_path.parent.mkdir(parents=True, exist_ok=True)
        fallback_path.write_text(json.dumps(file_ideas))

        result = json.loads(load_ideas(mock_tool_context))
        assert result["mood_board_source"] == "from_state"

    def test_raises_when_no_state_and_no_file(self, mock_tool_context, output_dir):
        from agents.assets_generator.tools import load_ideas

        with pytest.raises(FileNotFoundError):
            load_ideas(mock_tool_context)


# ---------------------------------------------------------------------------
# End-to-end: save_ideas → load_ideas via shared state
# ---------------------------------------------------------------------------


class TestEndToEndHandoff:
    def test_save_then_load_via_state(self, mock_tool_context, output_dir):
        from agents.ideation.tools import save_ideas
        from agents.assets_generator.tools import load_ideas

        save_ideas(json.dumps(SAMPLE_IDEAS), mock_tool_context)
        result = json.loads(load_ideas(mock_tool_context))

        assert len(result["ideas"]) == 1
        assert result["ideas"][0]["headline"] == "Run on Clouds"
