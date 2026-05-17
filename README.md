# RecapLoL

RecapLoL is a League of Legends recap and coaching app. It pulls Riot Games data, stores player and match records, summarizes recent performance, and generates an AI coach report with concrete improvement priorities.

The project is split into a FastAPI backend and a React frontend, with Docker Compose support for local full-stack development.

## Features

- Search and display player profile data by Riot ID / PUUID
- Fetch and store recent League of Legends match data from the Riot Games API
- Show match history, ranked information, champion mastery, and aggregate stats
- Analyze player performance across KDA, win rate, CS, vision, gold, roles, and champions
- Scrape OP.GG champion build data for build and matchup reference
- Generate an AI Coach report with up to three prioritized training areas
- Ask follow-up questions about the latest coach report

## Tech Stack

Backend:

- Python 3.11
- FastAPI
- SQLAlchemy async
- PostgreSQL
- Redis
- Pydantic v2
- OpenAI Python SDK
- pytest

Frontend:

- React 18
- TypeScript
- Vite
- Tailwind CSS
- React Query
- Zustand
- Recharts
- Vitest

Infrastructure:

- Docker Compose
- Nginx frontend container with `/api` reverse proxy

## Project Structure

```text
.
├── docker-compose.yml
├── docs/
│   └── superpowers/
├── lol-backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── repositories/
│   │   ├── schemas/
│   │   └── services/
│   ├── tests/
│   ├── main.py
│   └── pyproject.toml
└── lol-frontend/
    ├── src/
    │   ├── components/
    │   ├── hooks/
    │   ├── pages/
    │   ├── services/
    │   ├── stores/
    │   └── types/
    └── package.json
```

## Requirements

- Docker and Docker Compose
- Node.js 20+ if running the frontend outside Docker
- Python 3.11+ if running the backend outside Docker
- Riot Games developer API key
- OpenAI API key for AI Coach generation

## Environment Setup

Create the backend environment file:

```bash
cp lol-backend/.env.example lol-backend/.env
```

Then edit `lol-backend/.env`:

```env
RIOT_API_KEY=your_riot_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini
OPENAI_API_MODE=responses
```

For Docker Compose, the root `docker-compose.yml` overrides database and Redis URLs to use the container services, so the default local values in `.env.example` do not need to be changed for Docker.

## Quick Start With Docker

From the repository root:

```bash
docker compose up -d --build
```

Open the app:

```text
http://127.0.0.1:3006
```

Backend health check:

```text
http://127.0.0.1:8001/health
```

Stop the stack:

```bash
docker compose down
```

Remove containers and local database volumes:

```bash
docker compose down -v
```

## Local Development

### Backend

From `lol-backend`:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python main.py
```

The backend runs on:

```text
http://127.0.0.1:8000
```

The app creates database tables automatically on startup.

### Frontend

From `lol-frontend`:

```bash
npm install
npm run dev
```

The frontend runs on:

```text
http://127.0.0.1:3000
```

During Vite development, `/api` is proxied to `http://localhost:8000`.

## Deploy To Render (Free)

This repo now includes a Render Blueprint file at `render.yaml` for one-click setup:

- `recaplol-backend` (Docker web service, Free)
- `recaplol-frontend` (Static site)

### Deploy steps

1. Push this repository to GitHub.
2. In Render, choose New -> Blueprint and select this repo.
3. In the backend service, set required env vars:
   - `DATABASE_URL`
   - `REDIS_URL`
   - `RIOT_API_KEY`
   - `OPENAI_API_KEY` (optional if AI features are disabled)
4. After frontend gets a URL, set:
   - Backend `CORS_ORIGINS=https://<your-frontend-domain>`
5. Set frontend env var:
   - `VITE_API_BASE_URL=https://<your-backend-domain>`
6. Redeploy both services.

### Notes for Free plan

- Free backend web services spin down after ~15 minutes idle.
- First request after idle has cold-start latency.
- Do not put secrets in frontend env vars (`VITE_*` is public in browser bundles).

## Frontend On GitHub Pages + Backend On Render

This setup works well for this project:

- Frontend: GitHub Pages
- Backend: Render Web Service

### GitHub Pages setup

1. In GitHub repo settings, enable Pages and set source to "GitHub Actions".
2. Add repository secret:
   - `VITE_API_BASE_URL=https://<your-render-backend-domain>`
3. Push to `main` to trigger `.github/workflows/deploy-pages.yml`.

The workflow builds `lol-frontend`, publishes `dist`, and writes `404.html` for SPA route refresh support.

### Render CORS setup for Pages

Set backend env var:

```env
CORS_ORIGINS=https://123qwe55aa.github.io
```

If your Pages site uses a custom domain, use that domain instead.

## Useful Commands

Run backend tests:

```bash
cd lol-backend
python -m pytest -q
```

Run frontend tests:

```bash
cd lol-frontend
npm test -- --run
```

Build frontend:

```bash
cd lol-frontend
npm run build
```

Run full Docker stack:

```bash
docker compose up -d --build
```

Check running services:

```bash
docker compose ps
```

View logs:

```bash
docker compose logs -f
```

## Main API Areas

The backend exposes these route groups:

- `/players` - player profile, ranked data, and champion mastery
- `/matches` - match lists, match details, and match fetching
- `/stats` - career, champion, and role statistics
- `/analysis` - trend and progress analysis
- `/opgg` - champion build and matchup data from OP.GG
- `/coach` - AI Coach report generation and follow-up chat
- `/health` - service health check

FastAPI also provides interactive API docs when the backend is running:

```text
http://127.0.0.1:8000/docs
```

When using the Docker stack, use:

```text
http://127.0.0.1:8001/docs
```

## AI Coach Flow

The AI Coach feature follows a report-first workflow:

1. Build a structured context from player data, recent matches, stats, champion mastery, and OP.GG build data.
2. Run deterministic rule scoring to identify likely improvement areas.
3. Generate a structured AI report with summary, confidence, data window, priorities, action items, and follow-up questions.
4. Cache the latest report by data fingerprint.
5. Answer page-session follow-up questions using the latest report and bounded context.

If no OpenAI key is configured, AI generation will not work, but the rest of the app and tests can still run.

## Riot API Notes

You need a Riot Games API key from the Riot Developer Portal. Development keys expire regularly, so refresh the key if requests start returning authorization errors.

Player-facing lookup should use Riot ID and PUUID-oriented flows. Avoid relying on deprecated Summoner Name flows for new features.

## Compliance Notes

This project is intended for player recap, learning, and self-improvement. It should not be used to:

- provide unfair in-game advantage
- expose hidden player information
- calculate unofficial MMR or ELO
- automate gameplay decisions
- support cheating, scripting, account trading, or ban evasion

Keep API keys private. Do not commit `.env` files or production secrets.

## Status

Current local verification:

- Backend tests: passing
- Frontend tests: passing
- Frontend production build: passing
- Docker Compose stack: verified locally
