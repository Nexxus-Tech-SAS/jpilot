from app.services.model_usage_service import (
    UsageAccumulator,
    _avg_tokens_per_request,
    extract_llm_usage_details,
    extract_token_usage,
)


def test_extract_llm_usage_details_openai():
    data = {"usage": {"prompt_tokens": 120, "completion_tokens": 80, "total_tokens": 200}}
    assert extract_llm_usage_details("OpenAI", data) == {
        "input_tokens": 120,
        "output_tokens": 80,
        "total_tokens": 200,
    }
    assert extract_token_usage("OpenAI", data) == 200


def test_extract_llm_usage_details_anthropic():
    data = {"usage": {"input_tokens": 50, "output_tokens": 25}}
    assert extract_llm_usage_details("Anthropic", data) == {
        "input_tokens": 50,
        "output_tokens": 25,
        "total_tokens": 75,
    }


def test_extract_llm_usage_details_gemini():
    data = {
        "usageMetadata": {
            "promptTokenCount": 10,
            "candidatesTokenCount": 15,
            "totalTokenCount": 25,
        }
    }
    assert extract_llm_usage_details("Gemini", data) == {
        "input_tokens": 10,
        "output_tokens": 15,
        "total_tokens": 25,
    }


def test_usage_accumulator_tracks_input_and_output():
    acc = UsageAccumulator()
    acc.add_llm_response(
        "OpenAI",
        {"usage": {"prompt_tokens": 120, "completion_tokens": 80, "total_tokens": 200}},
    )
    acc.add_llm_response("Anthropic", {"usage": {"input_tokens": 50, "output_tokens": 25}})
    assert acc.requests == 2
    assert acc.tokens == 275
    assert acc.input_tokens == 170
    assert acc.output_tokens == 105


def test_avg_tokens_per_request():
    assert _avg_tokens_per_request(7100000, 790) == 8987
    assert _avg_tokens_per_request(0, 0) is None
