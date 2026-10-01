from __future__ import annotations

from app.core.config import settings
from app.services.llm import OpenAICompatibleLLMProvider


def test_ollama_generation_uses_recorded_bounded_settings(monkeypatch) -> None:
    captured = {}

    class Response:
        def raise_for_status(self):
            return None

        @staticmethod
        def json():
            return {"choices": [{"message": {"content": '{"answer":"hello"}'}}]}

    def fake_post(url, *, json, headers, timeout):
        captured.update(url=url, body=json, timeout=timeout)
        return Response()

    monkeypatch.setattr("app.services.llm.httpx.post", fake_post)
    provider = OpenAICompatibleLLMProvider()

    assert provider._request_json("system", "user") == {"answer": "hello"}
    assert captured["body"]["temperature"] == settings.LLM_TEMPERATURE == 0.1
    assert captured["body"]["top_p"] == settings.LLM_TOP_P == 0.9
    assert captured["body"]["max_tokens"] == settings.LLM_MAX_TOKENS == 768
    assert captured["body"]["seed"] == settings.LLM_SEED == 42
