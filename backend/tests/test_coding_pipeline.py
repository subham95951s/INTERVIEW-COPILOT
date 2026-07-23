"""
Unit & Integration tests for Upgrade Phase G: Coding Question Pipeline (`backend/tests/test_coding_pipeline.py`).
Tests JSON parsing, Groq Vision extraction, NVIDIA API fallback, code generation, and WebSocket control handling.
"""

import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.coding import CodingProblemAnalysis, CodingQuestionPipeline


@pytest.mark.asyncio
async def test_parse_response_valid_json():
    """Verify _parse_response cleanly converts valid markdown JSON into CodingProblemAnalysis."""
    pipeline = CodingQuestionPipeline()
    sample_json = json.dumps({
        "problem_summary": "Find two numbers that sum to target",
        "input_format": "List of integers nums and integer target",
        "output_format": "List of two indices [i, j]",
        "constraints": ["2 <= nums.length <= 10^4", "-10^9 <= nums[i] <= 10^9"],
        "examples": [{"input": "nums = [2,7,11,15], target = 9", "output": "[0,1]", "explanation": "2+7=9"}],
        "approach": "Use a hash map to store seen numbers and their indices. For each num, check if target - num exists in map.",
        "pseudocode": "map = {}\nfor i, num in enumerate(nums):\n  if target - num in map:\n    return [map[target - num], i]\n  map[num] = i",
        "time_complexity": "O(N)",
        "space_complexity": "O(N)",
        "edge_cases": ["Duplicate numbers", "Negative target"],
        "follow_up_considerations": ["What if array is sorted? Use two pointers."]
    })
    markdown_wrapped = f"Here is your analysis:\n```json\n{sample_json}\n```"

    analysis = pipeline._parse_response(markdown_wrapped)
    assert analysis.problem_summary == "Find two numbers that sum to target"
    assert analysis.time_complexity == "O(N)"
    assert analysis.space_complexity == "O(N)"
    assert len(analysis.constraints) == 2
    assert "Duplicate numbers" in analysis.edge_cases


@pytest.mark.asyncio
async def test_parse_response_invalid_json_fallback():
    """Verify malformed text gracefully falls back to raw approach text without throwing errors."""
    pipeline = CodingQuestionPipeline()
    raw_text = "This is not valid JSON, just a plain text explanation of LRU Cache."

    analysis = pipeline._parse_response(raw_text)
    assert analysis.problem_summary == "Extracted problem (raw text)"
    assert analysis.approach == raw_text
    assert analysis.time_complexity == "O(?)"


@pytest.mark.asyncio
async def test_analyze_screenshot_groq_primary():
    """Verify analyze_screenshot calls Groq Vision primary and returns analysis."""
    pipeline = CodingQuestionPipeline()

    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content='{"problem_summary": "Reverse linked list", "time_complexity": "O(N)", "space_complexity": "O(1)"}'))
    ]

    pipeline._groq_client.chat.completions.create = AsyncMock(return_value=mock_response)

    analysis = await pipeline.analyze_screenshot("base64_fake_data")
    assert analysis.problem_summary == "Reverse linked list"
    assert analysis.time_complexity == "O(N)"
    pipeline._groq_client.chat.completions.create.assert_called_once()


@pytest.mark.asyncio
async def test_analyze_screenshot_nvidia_fallback():
    """Verify analyze_screenshot automatically falls back to NVIDIA API when Groq fails."""
    pipeline = CodingQuestionPipeline()

    # Simulate Groq failure
    pipeline._groq_client.chat.completions.create = AsyncMock(side_effect=Exception("Groq rate limit exceeded"))

    mock_nvidia_response = MagicMock()
    mock_nvidia_response.choices = [
        MagicMock(message=MagicMock(content='{"problem_summary": "NVIDIA Vision Result", "time_complexity": "O(log N)", "space_complexity": "O(1)"}'))
    ]
    pipeline._nvidia_client.chat.completions.create = AsyncMock(return_value=mock_nvidia_response)

    with patch("app.services.coding.pipeline.settings.nvidia_api_key", "nvapi-fake-key-123"):
        analysis = await pipeline.analyze_screenshot("base64_fake_data")
        assert analysis.problem_summary == "NVIDIA Vision Result"
        assert analysis.time_complexity == "O(log N)"
        pipeline._nvidia_client.chat.completions.create.assert_called_once()


@pytest.mark.asyncio
async def test_generate_solution_code_groq_and_nvidia_fallback():
    """Verify code generation primary Groq and fallback to NVIDIA API."""
    pipeline = CodingQuestionPipeline()
    analysis = CodingProblemAnalysis(
        problem_summary="Test Problem",
        input_format="", output_format="", constraints=[], examples=[],
        approach="Hash set", pseudocode="set()", time_complexity="O(N)", space_complexity="O(N)",
        edge_cases=[], follow_up_considerations=[]
    )

    # Groq fails
    pipeline._groq_client.chat.completions.create = AsyncMock(side_effect=Exception("Groq error"))

    mock_nvidia_code_resp = MagicMock()
    mock_nvidia_code_resp.choices = [
        MagicMock(message=MagicMock(content="```python\ndef solve(nums):\n    return set(nums)\n```"))
    ]
    pipeline._nvidia_client.chat.completions.create = AsyncMock(return_value=mock_nvidia_code_resp)

    with patch("app.services.coding.pipeline.settings.nvidia_api_key", "nvapi-fake-key"):
        code = await pipeline.generate_solution_code(analysis)
        assert "def solve(nums):" in code
        assert "```" not in code
