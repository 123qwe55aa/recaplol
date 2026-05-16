# AI Coach Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a first-version AI Coach that generates a cached structured improvement report from recent player data and supports page-session follow-up questions.

**Architecture:** Backend adds a focused coach module: schemas, model, repository, context builder, rule engine, AI provider abstraction, and endpoints. Frontend adds typed coach API calls, a dedicated `/coach/:puuid` page, and an Analysis page entry card. The first runtime AI provider is OpenAI via Responses API structured output, while tests use fake providers.

**Tech Stack:** FastAPI, SQLAlchemy async, Pydantic v2, pytest, React 18, TypeScript, React Query, Vite/Vitest, OpenAI Python SDK.

---

## File Structure

Backend:

- Create `lol-backend/app/models/coach.py`: SQLAlchemy model for cached reports.
- Modify `lol-backend/app/models/__init__.py`: export `CoachReport`.
- Create `lol-backend/app/schemas/coach.py`: request/response/report schemas.
- Modify `lol-backend/app/schemas/__init__.py`: export coach schemas.
- Create `lol-backend/app/repositories/coach.py`: latest-report lookup and upsert.
- Create `lol-backend/app/services/coach_rule_engine.py`: deterministic improvement-area scoring.
- Create `lol-backend/app/services/coach_context_builder.py`: aggregate player/recent match facts.
- Create `lol-backend/app/services/ai_provider.py`: provider interface, fake-friendly defaults, OpenAI implementation.
- Create `lol-backend/app/api/endpoints/coach.py`: report and chat endpoints.
- Modify `lol-backend/app/api/v1/router.py`: include coach router.
- Modify `lol-backend/app/core/config.py`: add OpenAI/coach settings.
- Modify `lol-backend/pyproject.toml`: add OpenAI SDK dependency.
- Add tests in `lol-backend/tests/test_coach_rule_engine.py`, `lol-backend/tests/test_coach_context_builder.py`, `lol-backend/tests/test_coach_api_endpoints.py`, `lol-backend/tests/test_ai_provider.py`.

Frontend:

- Modify `lol-frontend/src/types/index.ts`: add coach types.
- Modify `lol-frontend/src/services/api.ts`: add coach API calls.
- Create `lol-frontend/src/hooks/useCoach.ts`: React Query hooks/mutations.
- Create `lol-frontend/src/pages/Coach.tsx`: report and follow-up UI.
- Modify `lol-frontend/src/pages/Analysis.tsx`: add AI Coach entry card.
- Modify `lol-frontend/src/App.tsx`: add `/coach/:puuid` route.
- Add tests in `lol-frontend/src/pages/__tests__/Coach.test.tsx`.

---

### Task 1: Backend Coach Persistence And Schemas

**Files:**
- Create: `lol-backend/app/models/coach.py`
- Modify: `lol-backend/app/models/__init__.py`
- Create: `lol-backend/app/schemas/coach.py`
- Modify: `lol-backend/app/schemas/__init__.py`
- Create: `lol-backend/app/repositories/coach.py`
- Test: `lol-backend/tests/test_models.py`
- Test: `lol-backend/tests/test_schemas.py`

- [ ] **Step 1: Write failing model and schema tests**

Add tests that construct `CoachReport`, validate `CoachReportPayload`, `CoachReportResponse`, and `CoachChatResponse`, and verify Python-side defaults.

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
cd /Users/toby/Documents/Projects/lol/lol-backend
python -m pytest tests/test_models.py tests/test_schemas.py -q
```

Expected: fail because `app.models.coach` and `app.schemas.coach` do not exist.

- [ ] **Step 3: Implement persistence model**

Create `app/models/coach.py` with:

- `CoachReport`
- table name `coach_reports`
- fields: `id`, `puuid`, `report_json`, `context_json`, `data_fingerprint`, `model`, `status`, `error_message`, `stale`, `generated_at`, `created_at`, `updated_at`
- indexes on `puuid`, `data_fingerprint`, and `generated_at`

- [ ] **Step 4: Implement coach schemas**

Create `app/schemas/coach.py` with:

- `CoachDataWindow`
- `CoachPriority`
- `CoachReportPayload`
- `CoachReportResponse`
- `CoachGenerateRequest`
- `CoachChatRequest`
- `CoachChatResponse`

- [ ] **Step 5: Implement repository**

Create `app/repositories/coach.py` with:

- `get_latest_by_puuid(puuid: str)`
- `get_by_fingerprint(puuid: str, fingerprint: str)`
- `upsert_report(...)`

- [ ] **Step 6: Export model and schemas**

Update model and schema `__init__.py` exports.

- [ ] **Step 7: Run tests to verify GREEN**

Run:

```bash
cd /Users/toby/Documents/Projects/lol/lol-backend
python -m pytest tests/test_models.py tests/test_schemas.py -q
```

Expected: pass.

---

### Task 2: Backend Rule Engine And Context Builder

**Files:**
- Create: `lol-backend/app/services/coach_rule_engine.py`
- Create: `lol-backend/app/services/coach_context_builder.py`
- Test: `lol-backend/tests/test_coach_rule_engine.py`
- Test: `lol-backend/tests/test_coach_context_builder.py`

- [ ] **Step 1: Write failing rule engine tests**

Create tests for these cases:

- high deaths ranks above other issues
- low CS per minute produces a CS priority
- low vision score produces a vision priority
- narrow champion pool produces champion pool guidance
- fewer than 5 matches lowers confidence

- [ ] **Step 2: Write failing context builder tests**

Use fake repositories or simple in-memory objects to verify the builder emits:

- player identity
- recent match ids
- match count
- primary role
- primary champions
- averages for kills/deaths/assists/CS/vision/gold
- win rate
- deterministic fingerprint

- [ ] **Step 3: Run tests to verify RED**

Run:

```bash
cd /Users/toby/Documents/Projects/lol/lol-backend
python -m pytest tests/test_coach_rule_engine.py tests/test_coach_context_builder.py -q
```

Expected: fail because services do not exist.

- [ ] **Step 4: Implement rule engine**

Create deterministic functions:

- `score_context(context: dict) -> dict`
- `build_fallback_report(context: dict, findings: list[dict]) -> dict`

Return at most 3 priorities. Keep text concise and data-backed.

- [ ] **Step 5: Implement context builder**

Create `CoachContextBuilder` that accepts an `AsyncSession` and builds context using existing repositories:

- `PlayerRepository`
- `MatchRepository`
- `MatchParticipantRepository`
- `ChampionMasteryRepository`

The builder must attach real win/loss from `Match.blue_team_win` and `participant.team_id`, matching existing `stats.py` logic.

- [ ] **Step 6: Run tests to verify GREEN**

Run:

```bash
cd /Users/toby/Documents/Projects/lol/lol-backend
python -m pytest tests/test_coach_rule_engine.py tests/test_coach_context_builder.py -q
```

Expected: pass.

---

### Task 3: Backend AI Provider And Coach Endpoints

**Files:**
- Create: `lol-backend/app/services/ai_provider.py`
- Create: `lol-backend/app/api/endpoints/coach.py`
- Modify: `lol-backend/app/api/v1/router.py`
- Modify: `lol-backend/app/core/config.py`
- Modify: `lol-backend/pyproject.toml`
- Test: `lol-backend/tests/test_ai_provider.py`
- Test: `lol-backend/tests/test_coach_api_endpoints.py`

- [ ] **Step 1: Write failing provider tests**

Tests should verify:

- fake provider returns a valid report payload
- provider errors are typed
- OpenAI provider is not called when no API key is configured

- [ ] **Step 2: Write failing endpoint tests**

Create tests for:

- `GET /coach/players/{puuid}/report` returns `has_report=false` when no report exists
- `POST /coach/players/{puuid}/report` generates a report through fake provider
- cache hit returns the saved report when fingerprint matches and `force=false`
- `force=true` regenerates
- AI failure returns stale latest report when available
- `POST /coach/players/{puuid}/chat` answers using fake provider and latest report

- [ ] **Step 3: Run tests to verify RED**

Run:

```bash
cd /Users/toby/Documents/Projects/lol/lol-backend
python -m pytest tests/test_ai_provider.py tests/test_coach_api_endpoints.py -q
```

Expected: fail because provider and endpoints do not exist.

- [ ] **Step 4: Implement AI provider abstraction**

Create:

- `AIProviderError`
- `AIProvider`
- `FakeAIProvider`
- `OpenAIProvider`
- `get_ai_provider()`

OpenAI implementation should use the official OpenAI Python SDK Responses API with structured output. Use current docs as source of truth. Keep all OpenAI imports isolated in this file.

- [ ] **Step 5: Add settings**

Add to `app/core/config.py`:

- `openai_api_key: str = ""`
- `openai_model: str = "gpt-4o-mini"`
- `coach_default_match_limit: int = 20`
- `coach_prompt_version: str = "coach-v1"`

- [ ] **Step 6: Add dependency**

Add `openai>=1.0.0` to backend dependencies.

- [ ] **Step 7: Implement coach endpoints**

Use dependency functions that tests can patch:

- `get_context_builder(db)`
- `get_coach_report_repository(db)`
- `get_ai_provider_dependency()`

Endpoint behavior must match the design doc.

- [ ] **Step 8: Include router**

Update `app/api/v1/router.py` to include `coach.router`.

- [ ] **Step 9: Run tests to verify GREEN**

Run:

```bash
cd /Users/toby/Documents/Projects/lol/lol-backend
python -m pytest tests/test_ai_provider.py tests/test_coach_api_endpoints.py -q
```

Expected: pass.

---

### Task 4: Frontend Coach API, Hooks, And Page

**Files:**
- Modify: `lol-frontend/src/types/index.ts`
- Modify: `lol-frontend/src/services/api.ts`
- Create: `lol-frontend/src/hooks/useCoach.ts`
- Create: `lol-frontend/src/pages/Coach.tsx`
- Modify: `lol-frontend/src/App.tsx`
- Test: `lol-frontend/src/pages/__tests__/Coach.test.tsx`

- [ ] **Step 1: Write failing frontend tests**

Create tests that mock coach hooks/API and verify:

- no-report state renders generate button
- generated report renders summary and three priorities
- chat answer appears after submit
- error state renders retry button

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
cd /Users/toby/Documents/Projects/lol/lol-frontend
npm test -- --run src/pages/__tests__/Coach.test.tsx
```

Expected: fail because `Coach.tsx` and hook/types do not exist.

- [ ] **Step 3: Add coach types**

Add TypeScript interfaces matching backend schemas:

- `CoachDataWindow`
- `CoachPriority`
- `CoachReportPayload`
- `CoachReportResponse`
- `CoachChatResponse`

- [ ] **Step 4: Add API functions**

Add to `src/services/api.ts`:

- `getCoachReport(puuid: string)`
- `generateCoachReport(puuid: string, force?: boolean)`
- `sendCoachQuestion(puuid: string, question: string)`

- [ ] **Step 5: Add React Query hooks**

Create `useCoachReport`, `useGenerateCoachReport`, and `useCoachChat`.

- [ ] **Step 6: Implement Coach page**

Build `/coach/:puuid` page with:

- no-report state
- loading state
- report state
- stale badge
- priority cards
- follow-up chat

- [ ] **Step 7: Add route**

Update `App.tsx` with `<Route path="/coach/:puuid" element={<CoachPage />} />`.

- [ ] **Step 8: Run tests to verify GREEN**

Run:

```bash
cd /Users/toby/Documents/Projects/lol/lol-frontend
npm test -- --run src/pages/__tests__/Coach.test.tsx
```

Expected: pass.

---

### Task 5: Frontend Analysis Entry And Full Integration

**Files:**
- Modify: `lol-frontend/src/pages/Analysis.tsx`
- Test: add or update frontend tests as needed

- [ ] **Step 1: Write failing Analysis page test**

Add a test that renders the Analysis page and verifies an AI Coach entry link points to `/coach/{puuid}`.

- [ ] **Step 2: Run test to verify RED**

Run:

```bash
cd /Users/toby/Documents/Projects/lol/lol-frontend
npm test -- --run
```

Expected: fail because Analysis page does not expose the coach entry yet.

- [ ] **Step 3: Implement Analysis entry card**

Add a compact card below existing stats with:

- title `AI 教练`
- short copy `基于最近比赛生成 3 个优先提升建议`
- link/button to `/coach/${puuid}`

- [ ] **Step 4: Run frontend verification**

Run:

```bash
cd /Users/toby/Documents/Projects/lol/lol-frontend
npm test -- --run
npm run build
```

Expected: tests and build pass.

- [ ] **Step 5: Run backend verification**

Run:

```bash
cd /Users/toby/Documents/Projects/lol/lol-backend
python -m pytest -q
```

Expected: backend tests pass.

---

## Plan Self-Review

Spec coverage:

- Report-first and follow-up chat: Tasks 3 and 4.
- Backend coach module: Tasks 1, 2, and 3.
- Provider abstraction/OpenAI first: Task 3.
- Structured JSON report schema: Tasks 1 and 3.
- Cache/fingerprint/stale fallback: Tasks 1, 2, and 3.
- Frontend Coach page and Analysis entry: Tasks 4 and 5.
- Testing and no real AI calls in tests: Tasks 1-5.

No placeholders are intentionally left in this plan. OpenAI exact implementation must use official docs at implementation time, because the API surface can change.
