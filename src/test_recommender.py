"""Pure-Python assertions for Day 4 recommendation and reply generation."""

from __future__ import annotations

import os
import urllib.error
from unittest.mock import patch

from recommender import KEY_MODELS, recommend
from reply_generator import generate_reply


def _friction_depth(depth_value: str) -> float:
    parts = depth_value.split("/")
    return float(parts[-1])


def run_tests() -> None:
    deep_results = recommend(60, 2000, max_results=15)
    assert deep_results
    assert deep_results[0]["model"] == "ZR300D"
    assert deep_results[0]["required_config"] == "Interlock Kelly"
    assert all(
        _friction_depth(item["depth_value"]) >= 60
        and float(item["diameter_value"]) >= 2000
        for item in deep_results
    )
    key_flags = [item["model"] in KEY_MODELS for item in deep_results]
    assert key_flags == sorted(key_flags, reverse=True)

    shallow_results = recommend(40, 1300)
    assert shallow_results[0]["required_config"] == "Interlock Kelly"

    assert recommend(200, 5000) == []

    facts = {
        **deep_results[0],
        "required_depth_m": 60,
        "required_diameter_mm": 2000,
        "project_type": "foundation piling",
        "market": "UAE",
    }
    with patch.dict(os.environ, {"DEEPSEEK_API_KEY": ""}):
        with patch("reply_generator._read_env_value", return_value=""):
            reply = generate_reply(facts, "en", "Foundation project")
    assert reply["mode"] == "template"
    assert reply["note"] == "No API key configured"
    assert facts["depth_value"] in reply["reply_text"]
    assert facts["model"] in reply["reply_text"]

    with patch("reply_generator._get_api_key", return_value="test-key"):
        with patch("reply_generator._llm_reply", return_value="LLM reply"):
            llm_reply = generate_reply(facts, "en", "Foundation project")
    assert llm_reply == {
        "reply_text": "LLM reply",
        "mode": "llm",
        "note": "",
    }

    with patch("reply_generator._get_api_key", return_value="test-key"):
        with patch(
            "reply_generator._llm_reply",
            side_effect=TimeoutError("simulated timeout for test-key"),
        ):
            fallback = generate_reply(facts, "ar", "Foundation project")
    assert fallback["mode"] == "template"
    assert fallback["note"] == (
        "LLM unavailable (TimeoutError: simulated timeout for [REDACTED]), "
        "used template instead"
    )
    assert "test-key" not in fallback["note"]
    assert facts["model"] in fallback["reply_text"]

    http_error = urllib.error.HTTPError(
        "https://example.invalid",
        429,
        "Too Many Requests",
        None,
        None,
    )
    with patch("reply_generator._get_api_key", return_value="test-key"):
        with patch("reply_generator._llm_reply", side_effect=http_error):
            http_fallback = generate_reply(facts, "en", "")
    assert "HTTPError" in http_fallback["note"]
    assert "HTTP status 429" in http_fallback["note"]
    assert "test-key" not in http_fallback["note"]

    print("All Day 4 recommendation tests passed.")


if __name__ == "__main__":
    run_tests()
