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
Use 1-3 priorities. Evidence must quote supplied stats, same-role enemy comparison, or match context. If context.lane_opponent_comparison.sample_size is greater than 0, include at least one evidence item that compares the player against the enemy in the same position. Do not use report_summary, findings, or positive_highlights.
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

MATCH_RECAP_SCHEMA_INSTRUCTIONS = """
Return exactly one JSON object with this shape:
{
  "summary": "string",
  "turning_points": [
    {
      "title": "string",
      "timestamp": 0,
      "explanation": "string"
    }
  ],
  "strengths": ["string"],
  "mistakes": ["string"],
  "next_game_focus": "string",
  "follow_up_questions": ["string"]
}
Use only supplied match_context and timeline_recap. Make this recap specific to this single game.
Use match_context.role_profile as the evaluation contract. Do not make CS a primary criticism for UTILITY or JUNGLE. For UTILITY, prioritize vision control, assist participation, objective setup, deaths, and positioning. For lane carries, CS can be a primary point only when role_profile.cs_is_primary is true.
Do not include markdown or extra keys. Do not invent hidden information or skill-shot details.
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

    @abstractmethod
    async def generate_match_recap(
        self, match_context: dict, timeline_recap: dict
    ) -> dict:
        """Return an AI interpretation for one match recap."""


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

    async def generate_match_recap(
        self, match_context: dict, timeline_recap: dict
    ) -> dict:
        participant = match_context.get("participant") or {}
        champion = participant.get("champion_name") or "这名英雄"
        insights = list(timeline_recap.get("insights") or [])
        stats = timeline_recap.get("timeline_stats") or {}
        primary = insights[0] if insights else {}
        role_profile = match_context.get("role_profile") or {}
        cs_is_primary = bool(role_profile.get("cs_is_primary"))
        primary_title = primary.get("title") or "节奏稳定性"
        primary_recommendation = (
            primary.get("recommendation")
            or "下一局先盯一个可执行习惯，打完后只复盘这个习惯是否做到。"
        )
        evidence = list(primary.get("evidence") or [])
        turning_points = []
        for window in timeline_recap.get("resource_windows", [])[:2]:
            if window.get("player_died_before"):
                turning_points.append({
                    "title": f"{window.get('resource') or '资源'}前阵亡",
                    "timestamp": window.get("timestamp") or 0,
                    "explanation": (
                        f"{window.get('minute')} 分钟资源事件前你已经阵亡，"
                        "这会让队伍以少打多或直接放弃争夺。"
                    ),
                })
        if not turning_points and primary:
            turning_points.append({
                "title": primary_title,
                "timestamp": 0,
                "explanation": "这条规则信号是本局最值得先复盘的断点。",
            })

        strengths = []
        cs10 = stats.get("cs_per_min_at_10")
        if cs_is_primary and isinstance(cs10, (int, float)) and cs10 >= 6:
            strengths.append(f"{champion} 10 分钟补刀约 {cs10}/分钟，对线基本盘还可以。")
        if not strengths:
            strengths.append("这局已经有可定位的时间线证据，复盘重点比较清楚。")

        mistakes = evidence or [primary_title]
        return {
            "summary": f"这局 {champion} 最值得复盘的是：{primary_title}。",
            "turning_points": turning_points[:3],
            "strengths": strengths[:2],
            "mistakes": mistakes[:3],
            "next_game_focus": primary_recommendation,
            "follow_up_questions": [
                "这局第一个关键转折点该怎么处理？",
                "下一局我应该只练哪一个动作？",
            ],
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

    async def generate_match_recap(
        self, match_context: dict, timeline_recap: dict
    ) -> dict:
        return await self._create_structured_response(
            system=(
                "You are a League of Legends VOD review coach. Explain one match "
                "from structured timeline evidence. Write in concise Chinese. "
                "Be specific, practical, and avoid generic advice. Use only the "
                "provided facts; if a cause is uncertain, phrase it as an inference. "
                "Respect role_profile. Do not make CS a primary criticism for UTILITY "
                "or JUNGLE."
            ),
            schema_instructions=MATCH_RECAP_SCHEMA_INSTRUCTIONS,
            user_payload={
                "task": "generate_single_match_recap",
                "match_context": match_context,
                "timeline_recap": timeline_recap,
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
