"""AI provider abstraction for coach report generation."""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from typing import Any

from app.core.config import settings
from app.services.coach_rule_engine import build_fallback_report

REPORT_SCHEMA_INSTRUCTIONS = """
Return exactly one JSON object with this shape:
{
  "summary": "string",
  "confidence": "low|medium|high",
  "data_window": {
    "match_count": 0,
    "recent_match_ids": [],
    "primary_role": "string|null",
    "primary_champions": []
  },
  "priorities": [
    {
      "category": "string",
      "title": "string",
      "severity": "low|medium|high",
      "evidence": ["string"],
      "problem": "string",
      "impact": "string",
      "recommendation": "string",
      "actions": ["string"]
    }
  ],
  "notes": "string|null",
  "follow_up_questions": ["string"]
}
Use 1-3 priorities. Evidence must quote supplied stats or match context. Do not use report_summary, findings, or positive_highlights.
""".strip()

CHAT_SCHEMA_INSTRUCTIONS = """
Return exactly one JSON object with this shape:
{
  "answer": "string",
  "used_evidence": ["string"],
  "suggested_next_question": "string|null"
}
Do not include markdown or extra keys.
""".strip()


class AIProviderError(Exception):
    """Raised when an AI provider cannot complete a coach request."""


class AIProvider(ABC):
    model: str

    @abstractmethod
    async def generate_report(self, context: dict, findings: list[dict]) -> dict:
        """Return a structured coach report payload."""

    @abstractmethod
    async def answer_question(
        self, report: dict, context: dict, question: str
    ) -> dict:
        """Return a structured follow-up answer."""


class FakeAIProvider(AIProvider):
    """Deterministic provider for tests and no-key local development."""

    model = "fake-coach"

    async def generate_report(self, context: dict, findings: list[dict]) -> dict:
        return build_fallback_report(context, findings)

    async def answer_question(
        self, report: dict, context: dict, question: str
    ) -> dict:
        evidence = []
        for priority in report.get("priorities", [])[:1]:
            evidence.extend(priority.get("evidence", [])[:2])
        return {
            "answer": (
                "Based on this report, start with the highest-priority habit and "
                f"review it after your next block of games. Question: {question}"
            ),
            "used_evidence": evidence,
            "suggested_next_question": "Do you want a simple drill for the top priority?",
        }


class OpenAIProvider(AIProvider):
    """OpenAI provider supporting Responses API and legacy Chat Completions."""

    def __init__(
        self,
        api_key: str,
        model: str,
        api_mode: str = "responses",
        base_url: str = "",
    ):
        if not api_key:
            raise AIProviderError("OpenAI API key is not configured")
        if api_mode not in {"responses", "chat"}:
            raise AIProviderError("OpenAI API mode must be 'responses' or 'chat'")
        self.api_key = api_key
        self.model = model
        self.api_mode = api_mode
        self.base_url = base_url

    async def generate_report(self, context: dict, findings: list[dict]) -> dict:
        return await self._create_structured_response(
            system=(
                "You are a League of Legends data analyst coach. Use only the "
                "provided JSON data. Return concise, evidence-backed Chinese advice. "
                "Do not promise rank gains, insult the player, or discuss cheating."
            ),
            schema_instructions=REPORT_SCHEMA_INSTRUCTIONS,
            user_payload={
                "task": "generate_coach_report",
                "context": context,
                "findings": findings,
            },
        )

    async def answer_question(
        self, report: dict, context: dict, question: str
    ) -> dict:
        return await self._create_structured_response(
            system=(
                "You answer follow-up questions about a League of Legends coach "
                "report. Use only the report and context. If evidence is missing, "
                "say it is insufficient."
            ),
            schema_instructions=CHAT_SCHEMA_INSTRUCTIONS,
            user_payload={
                "task": "answer_follow_up",
                "report": report,
                "context": context,
                "question": question,
            },
        )

    async def _create_structured_response(
        self, system: str, schema_instructions: str, user_payload: dict[str, Any]
    ) -> dict:
        try:
            from openai import AsyncOpenAI

            client_kwargs = {"api_key": self.api_key}
            if self.base_url:
                client_kwargs["base_url"] = self.base_url
            client = AsyncOpenAI(**client_kwargs)
            if self.api_mode == "chat":
                response = await client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system},
                        {
                            "role": "user",
                            "content": (
                                schema_instructions
                                + "\n\nPayload:\n"
                                + json.dumps(user_payload, ensure_ascii=False)
                            ),
                        },
                    ],
                    response_format={"type": "json_object"},
                )
                text = response.choices[0].message.content
                if not text:
                    raise AIProviderError("OpenAI chat response did not include content")
                return _parse_json_object(text)

            response = await client.responses.create(
                model=self.model,
                input=[
                    {"role": "system", "content": system},
                    {
                        "role": "user",
                        "content": (
                            schema_instructions
                            + "\n\nPayload:\n"
                            + json.dumps(user_payload, ensure_ascii=False)
                        ),
                    },
                ],
                text={"format": {"type": "json_object"}},
            )
            text = getattr(response, "output_text", None)
            if not text:
                raise AIProviderError("OpenAI response did not include output_text")
            return _parse_json_object(text)
        except AIProviderError:
            raise
        except Exception as exc:
            raise AIProviderError(str(exc)) from exc


def _parse_json_object(text: str) -> dict:
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned).strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        if start == -1:
            raise
        parsed, _ = json.JSONDecoder().raw_decode(cleaned[start:])

    if not isinstance(parsed, dict):
        raise AIProviderError("AI provider response was not a JSON object")
    return parsed


def get_ai_provider() -> AIProvider:
    if settings.openai_api_key:
        return OpenAIProvider(
            settings.openai_api_key,
            settings.openai_model,
            settings.openai_api_mode,
            settings.openai_base_url,
        )
    return FakeAIProvider()
