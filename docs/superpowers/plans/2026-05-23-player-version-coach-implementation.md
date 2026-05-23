# Player Version and Coach Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add latest LoL client version information and embedded AI Coach chat to the player page.

**Architecture:** Reuse the existing React Query and coach chat patterns. Add one Data Dragon API service function, one query hook, two focused UI components, and compose them into `PlayerPage`.

**Tech Stack:** React, TypeScript, Vite, Vitest, React Testing Library, TanStack Query, Axios.

---

### Task 1: Version Service and Hook

**Files:**
- Modify: `lol-frontend/src/services/api.ts`
- Create: `lol-frontend/src/hooks/useLolVersion.ts`
- Test: `lol-frontend/src/services/__tests__/api.test.ts`

- [x] Add a failing API service test for fetching the first Data Dragon version.
- [x] Implement `getLatestLolVersion()`.
- [x] Add `useLolVersion()` with a six-hour stale time.

### Task 2: Player Page UI

**Files:**
- Create: `lol-frontend/src/components/LoLVersionCard.tsx`
- Create: `lol-frontend/src/components/PlayerCoachChatPanel.tsx`
- Modify: `lol-frontend/src/pages/Player.tsx`
- Test: `lol-frontend/src/components/__tests__/LoLVersionCard.test.tsx`
- Test: `lol-frontend/src/components/__tests__/PlayerCoachChatPanel.test.tsx`
- Test: `lol-frontend/src/pages/__tests__/Player.test.tsx`

- [x] Add failing component and page tests.
- [x] Implement version card loading, success, failure, and patch notes link states.
- [x] Implement embedded AI Coach chat with local message history and a full coach page link.
- [x] Render both cards on `PlayerPage`.
