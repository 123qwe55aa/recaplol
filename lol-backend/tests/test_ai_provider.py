import sys
from types import SimpleNamespace

import pytest

from app.services.ai_provider import AIProviderError, FakeAIProvider, OpenAIProvider


@pytest.mark.asyncio
async def test_fake_provider_returns_report_payload():
    provider = FakeAIProvider()
    context = {
        "match_count": 3,
        "recent_match_ids": ["NA1_1"],
        "averages": {"deaths": 7.0, "cs_per_minute": 4.0, "vision_score": 10.0},
    }
    findings = [
        {
            "category": "deaths",
            "title": "Reduce avoidable deaths",
            "severity": 0.7,
            "evidence": "7.0 average deaths.",
            "recommendation": "Reset earlier.",
        }
    ]

    report = await provider.generate_report(context, findings)

    assert report["summary"]
    assert report["confidence"] == "low"
    assert report["priorities"]


def test_openai_provider_requires_api_key():
    with pytest.raises(AIProviderError):
        OpenAIProvider(api_key="", model="gpt-4o-mini")


@pytest.mark.asyncio
async def test_openai_provider_uses_responses_api_by_default(monkeypatch):
    calls = {"responses": 0, "chat": 0}

    class FakeResponses:
        async def create(self, **kwargs):
            calls["responses"] += 1
            assert kwargs["text"] == {"format": {"type": "json_object"}}
            return SimpleNamespace(output_text='{"summary":"ok"}')

    class FakeChatCompletions:
        async def create(self, **kwargs):
            calls["chat"] += 1
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content='{"summary":"bad"}'))]
            )

    class FakeClient:
        def __init__(self, api_key, base_url=None):
            self.responses = FakeResponses()
            self.chat = SimpleNamespace(completions=FakeChatCompletions())

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(AsyncOpenAI=FakeClient))
    provider = OpenAIProvider(api_key="key", model="gpt-4o-mini")

    result = await provider.generate_report({"match_count": 1}, [])

    assert result == {"summary": "ok"}
    assert calls == {"responses": 1, "chat": 0}


@pytest.mark.asyncio
async def test_openai_provider_can_use_legacy_chat_completions(monkeypatch):
    calls = {"responses": 0, "chat": 0}

    class FakeResponses:
        async def create(self, **kwargs):
            calls["responses"] += 1
            return SimpleNamespace(output_text='{"summary":"bad"}')

    class FakeChatCompletions:
        async def create(self, **kwargs):
            calls["chat"] += 1
            assert kwargs["response_format"] == {"type": "json_object"}
            assert kwargs["messages"][0]["role"] == "system"
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content='{"summary":"ok"}'))]
            )

    class FakeClient:
        def __init__(self, api_key, base_url=None):
            self.responses = FakeResponses()
            self.chat = SimpleNamespace(completions=FakeChatCompletions())

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(AsyncOpenAI=FakeClient))
    provider = OpenAIProvider(api_key="key", model="gpt-4o-mini", api_mode="chat")

    result = await provider.generate_report({"match_count": 1}, [])

    assert result == {"summary": "ok"}
    assert calls == {"responses": 0, "chat": 1}


@pytest.mark.asyncio
async def test_openai_provider_includes_report_schema_in_prompt(monkeypatch):
    captured = {}

    class FakeChatCompletions:
        async def create(self, **kwargs):
            captured["messages"] = kwargs["messages"]
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content='{"summary":"ok"}'))]
            )

    class FakeClient:
        def __init__(self, api_key, base_url=None):
            self.chat = SimpleNamespace(completions=FakeChatCompletions())

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(AsyncOpenAI=FakeClient))
    provider = OpenAIProvider(api_key="key", model="MiniMax-M2.7", api_mode="chat")

    await provider.generate_report({"match_count": 1}, [])

    prompt = captured["messages"][1]["content"]
    assert '"summary": "string"' in prompt
    assert '"priorities": [' in prompt
    assert '"follow_up_questions": [' in prompt
    assert "Do not use report_summary, findings, or positive_highlights" in prompt


@pytest.mark.asyncio
async def test_openai_match_recap_prompt_requires_role_appropriate_analysis(monkeypatch):
    captured = {}

    class FakeChatCompletions:
        async def create(self, **kwargs):
            captured["messages"] = kwargs["messages"]
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content='{"summary":"ok"}'))]
            )

    class FakeClient:
        def __init__(self, api_key, base_url=None):
            self.chat = SimpleNamespace(completions=FakeChatCompletions())

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(AsyncOpenAI=FakeClient))
    provider = OpenAIProvider(api_key="key", model="MiniMax-M2.7", api_mode="chat")

    await provider.generate_match_recap(
        match_context={
            "participant": {"champion_name": "Soraka", "team_position": "UTILITY"},
            "role_profile": {
                "role": "UTILITY",
                "primary_focus": ["vision", "assists"],
                "avoid_as_primary": ["cs"],
            },
        },
        timeline_recap={"timeline_stats": {"cs_per_min_at_10": 1.0}, "insights": []},
    )

    system_prompt = captured["messages"][0]["content"]
    user_prompt = captured["messages"][1]["content"]
    assert "role_profile" in user_prompt
    assert "Do not make CS a primary criticism for UTILITY" in system_prompt


@pytest.mark.asyncio
async def test_openai_provider_passes_custom_base_url(monkeypatch):
    client_args = {}

    class FakeChatCompletions:
        async def create(self, **kwargs):
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content='{"summary":"ok"}'))]
            )

    class FakeClient:
        def __init__(self, api_key, base_url=None):
            client_args["api_key"] = api_key
            client_args["base_url"] = base_url
            self.chat = SimpleNamespace(completions=FakeChatCompletions())

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(AsyncOpenAI=FakeClient))
    provider = OpenAIProvider(
        api_key="key",
        model="MiniMax-M2.7",
        api_mode="chat",
        base_url="https://api.minimax.io/v1",
    )

    result = await provider.generate_report({"match_count": 1}, [])

    assert result == {"summary": "ok"}
    assert client_args == {
        "api_key": "key",
        "base_url": "https://api.minimax.io/v1",
    }


@pytest.mark.asyncio
async def test_openai_provider_parses_json_after_reasoning_tags(monkeypatch):
    class FakeChatCompletions:
        async def create(self, **kwargs):
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content="<think>reasoning text</think>\n\n{\"summary\":\"ok\"}"
                        )
                    )
                ]
            )

    class FakeClient:
        def __init__(self, api_key, base_url=None):
            self.chat = SimpleNamespace(completions=FakeChatCompletions())

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(AsyncOpenAI=FakeClient))
    provider = OpenAIProvider(api_key="key", model="MiniMax-M2.7", api_mode="chat")

    result = await provider.generate_report({"match_count": 1}, [])

    assert result == {"summary": "ok"}


@pytest.mark.asyncio
async def test_fake_provider_answers_question():
    provider = FakeAIProvider()
    answer = await provider.answer_question(
        {"priorities": [{"evidence": ["high deaths"]}]},
        {"match_count": 10},
        "How do I die less?",
    )

    assert "How do I die less?" in answer["answer"]
    assert answer["used_evidence"] == ["high deaths"]


@pytest.mark.asyncio
async def test_fake_provider_generates_match_recap():
    provider = FakeAIProvider()
    recap = await provider.generate_match_recap(
        match_context={
            "match_id": "NA1_123",
            "participant": {"champion_name": "Ahri", "team_position": "MID"},
            "result": "loss",
        },
        timeline_recap={
            "timeline_stats": {
                "early_deaths": 1,
                "resource_deaths": 1,
                "cs_per_min_at_10": 5.0,
            },
            "insights": [
                {
                    "title": "关键资源前阵亡",
                    "evidence": ["资源前 90 秒内死亡 1 次"],
                    "recommendation": "资源前 90 秒先补视野。",
                }
            ],
        },
    )

    assert recap["summary"]
    assert recap["next_game_focus"]
    assert recap["turning_points"][0]["title"] == "关键资源前阵亡"
    assert recap["mistakes"]
    assert recap["follow_up_questions"]
