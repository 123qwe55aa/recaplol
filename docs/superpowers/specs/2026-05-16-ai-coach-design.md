# AI Coach Design

## Goal

Add an AI coach that helps League of Legends players improve by combining their recent match data, champion mastery, current statistical analysis, and OP.GG champion meta data. The first version is a comprehensive health check: generate a structured coach report from the user's recent 10-20 matches, then allow lightweight follow-up questions about that report.

## Product Scope

The first version uses a "report first, follow-up chat second" flow.

- The Analysis page shows an AI Coach summary card and links to a dedicated coach page.
- The Coach page generates or displays the latest saved report for the player.
- The report highlights 3 priority improvement areas.
- Each priority includes a problem, evidence, impact, action items, and an OP.GG/meta reference when available.
- The user can ask follow-up questions in the current page session.
- Follow-up chat is not persisted in version one.

The coach tone is data analyst style with a mild coaching voice: evidence-based, specific, and constructive.

## Architecture

Add a dedicated backend `coach` module instead of expanding the existing `analysis.py` endpoint.

Backend modules:

- `app/api/endpoints/coach.py`
  - `GET /coach/players/{puuid}/report`: read the latest saved report, or return an empty state.
  - `POST /coach/players/{puuid}/report`: generate or refresh a report.
  - `POST /coach/players/{puuid}/chat`: answer a follow-up question using the latest report and structured context.
- `app/services/coach_context_builder.py`
  - Aggregates player, recent matches, stats, analysis, champion mastery, and OP.GG build data.
  - Emits structured facts rather than natural-language advice.
- `app/services/coach_rule_engine.py`
  - Scores likely improvement areas such as deaths, CS, vision, win rate, role performance, champion pool, common champion performance, and OP.GG build deviation.
  - Produces prioritized evidence for the model.
- `app/services/ai_provider.py`
  - Defines an `AIProvider` interface.
  - First implementation is `OpenAIProvider`.
  - Tests use a fake provider.
- `app/models/coach.py`
  - Persists the latest report per generated context.

Frontend modules:

- `src/pages/Coach.tsx`
- `src/hooks/useCoach.ts`
- `src/services/api.ts` coach functions
- `src/types/index.ts` coach types
- `src/App.tsx` route `/coach/:puuid`
- `src/pages/Analysis.tsx` AI Coach summary/entry card

## AI Provider Strategy

The code should depend on an `AIProvider` abstraction. The initial runtime provider is OpenAI, configured by environment variables. The rest of the coach system should not know which model vendor is used.

Provider responsibilities:

- Generate a coach report from a structured context payload.
- Answer a follow-up question using the latest report plus bounded context.
- Return structured data or raise typed errors.

Tests must not call real AI APIs.

## Report Schema

The model output should be structured JSON, not free-form Markdown.

```json
{
  "summary": "一句话总体判断",
  "confidence": "high | medium | low",
  "data_window": {
    "matches": 20,
    "primary_role": "MID",
    "primary_champions": ["Ahri", "Annie"]
  },
  "priorities": [
    {
      "rank": 1,
      "title": "降低中期无效死亡",
      "problem": "最近 20 场场均死亡偏高",
      "evidence": ["场均死亡 6.4", "输局平均死亡 8.1"],
      "impact": "会降低资源转换率，让优势局更难结束",
      "actions": ["15 分钟后没有视野不单带过河", "第二件装备前减少 1v2 尝试"],
      "opgg_reference": "Ahri 主流中路打法更依赖先手控制和边线安全视野"
    }
  ],
  "follow_up_questions": [
    "我应该先练哪个英雄？",
    "为什么我的胜率低于 KDA 表现？"
  ]
}
```

Follow-up chat response:

```json
{
  "answer": "回答内容",
  "used_evidence": ["引用了报告中的哪几条证据"],
  "suggested_next_question": "下一步可以追问什么"
}
```

Rules for model output:

- Use only the provided data.
- Say when data is insufficient.
- Give at most 3 major priorities.
- Make every recommendation executable.
- Avoid promises like guaranteed rank improvement.
- Avoid abusive language.
- Avoid advice about cheating, scripting, account trading, or ban evasion.

## Persistence And Cache

Save the latest generated report in the backend database. Chat history is only kept in frontend memory for version one.

Suggested persisted fields:

- `id`
- `puuid`
- `report_json`
- `context_json`
- `data_fingerprint`
- `model`
- `status`
- `error_message`
- `generated_at`
- `created_at`
- `updated_at`

The `data_fingerprint` should include:

- `puuid`
- recent match ids
- match count
- primary role
- primary champions
- OP.GG query parameters
- coach prompt/schema version

`POST /coach/players/{puuid}/report` behavior:

- Return cached report when fingerprint has not changed.
- Regenerate when fingerprint changed.
- Regenerate when `force=true`.

## Error Handling

- If AI generation fails and an older report exists, return the old report with `stale: true`.
- If AI generation fails and no report exists, return a clear error.
- If OP.GG data is missing, still generate a report with lower confidence.
- If recent match count is below 5, allow report generation but mark confidence low.
- If no recent matches exist, show a clear empty state and suggest fetching matches first.

## Frontend UX

Analysis page:

- Add an AI Coach card below or near existing summary stats.
- Show whether a latest report exists.
- Provide a button to open `/coach/:puuid`.

Coach page:

- Header with back link, player identity if available, data window, and last generated time.
- Empty state with a "Generate AI Coach Report" button.
- Loading state during generation.
- Report state with summary, confidence, and three priority cards.
- Each priority card shows problem, evidence, impact, actions, and OP.GG reference.
- Follow-up chat below the report.
- Refresh report button with optional force refresh.

## Testing

Backend tests:

- Context builder aggregates player, match, stats, mastery, and OP.GG data into correct facts.
- Rule engine ranks deaths, CS, vision, champion pool, and build deviation issues.
- Report endpoint handles empty state, generation, cache hit, force refresh, and AI failure fallback.
- Chat endpoint answers using fake provider and latest report.
- AI provider interface is tested with fake implementations only.

Frontend tests:

- Analysis page renders AI Coach entry.
- Coach page renders no-report state.
- Coach page renders report priorities.
- Follow-up question renders answer.
- API failure shows retry/error state.

## Non-Goals For Version One

- Persistent chat history.
- Long-term coaching memory across weeks.
- Real-time in-game coaching.
- Voice assistant.
- Full timeline event analysis.
- Guaranteeing rank improvement.
- Support for cheating, scripting, or ban evasion.

## Open Questions For Implementation

- Exact OpenAI model and SDK details must be confirmed from current official OpenAI documentation before implementation.
- The current project does not have a single root git repository; only `lol-backend` appears to be a git repo, so this spec may not be committed from the project root until repository structure is clarified.
