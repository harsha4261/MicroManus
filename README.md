# MicroManus

A deep-research chat agent with live internet access — built as the DrDroid (W23) Product Engineer assignment.

Ask it a question and it runs a **think → search → read → think again** loop (LangGraph ReAct agent) until it has enough to answer, then writes a cited Markdown report you can export as a PDF. Conversations are threaded, cost-tracked per model, and gated behind OAuth + a credits/Stripe paywall.

## Live deployment

| | |
|---|---|
| Backend API | https://micromanus.fastapicloud.dev (FastAPI on fastapicloud) |
| Frontend | _deployed on Vercel — add the production URL here_ |
| API docs (Swagger) | https://micromanus.fastapicloud.dev/docs |

## What it does (assignment requirements)

- **Web UI to chat with an agent that has internet access** — React chat UI; the agent searches the web (Tavily, DuckDuckGo fallback) and reads pages (`fetch_page`) via two LangChain tools.
- **Conversation threads that hold context** — every message replays that thread's history (capped at the last 20 messages) back into the prompt.
- **Agent operates in a loop: think → tool call → observe → think again** — implemented with `langgraph.prebuilt.create_react_agent`; the loop is visible live in the UI as a "field notes" trace (`search` / `read` / `found` lines) while it runs, with token-by-token streaming of the final answer.
- **Start new chats** — sidebar "+ New chat"; chats can also be soft-deleted (hidden from the list, kept for cost history).
- **Create a report (PDF) as an artifact** — reports render as full Markdown (headings, tables, citations, sources) and export to PDF server-side (fpdf2).

## Beyond the brief

Built out past the minimum so the app is actually usable and defensible in front of a reviewer:

- **Auth**: Google + GitHub OAuth, short-lived JWT access tokens (30 min) with rotating refresh tokens (30 days) — no session ever stays valid indefinitely on a leaked token.
- **Billing**: Stripe Checkout for credit purchases, webhook-verified crediting (signature-checked, replay-safe via a unique constraint on `stripe_session_id`), a one-time coupon path, and a "buy credits" prompt the moment a user hits zero.
- **Bring-your-own LLM key**: users paste their own API key for OpenAI, Anthropic, Groq, Gemini, OpenRouter, Mistral, or Cerebras (several free-tier models included). Keys are Fernet-encrypted at rest, never logged. Multiple comma-separated keys rotate per request to spread provider rate limits.
- **Cost & stats page**: per-thread token breakdown (input / output / cache-read / cache-write) and $ cost, priced per the model actually used for that thread — verified against each provider's real per-token pricing, including correct handling of cached-token billing (LangChain reports cached tokens as part of `input_tokens`, so they're not double-charged).
- **Admin panel**: allow-listed emails (`ADMIN_EMAILS`) get a `/admin` page listing every user, credits, spend, and a manual credit adjustment tool.
- **Rate limiting**: 10 messages/minute per user, independent of credit balance, to stop runaway loops or abuse from burning API spend.
- **Resilience in the agent loop**: a malformed tool call from a small/free model doesn't kill the run — the agent falls back to a tool-less "answer from what you've already gathered" pass; the same fallback fires if the step budget runs out. Blocked/403'd sites are reported back to the agent as a fact it can route around, not a fatal error.
- **Evidence discipline**: the system prompt enforces citing only URLs actually fetched during the run and forbids filling gaps with numbers recalled from model memory — an explicit anti-hallucination guard, since research agents built on small models fabricate readily under pressure.
- **i18n**: English / Hindi UI switcher.
- **Backend test suite**: 23 pytest tests covering pricing math, rate limiting, soft delete, PDF export edge cases (long URLs, unicode), and every agent-loop failure path described above.

## Architecture

```
frontend/          React + Vite SPA
  src/pages/        Chat, Settings, Stats, Admin, Paywall, Login
  src/api.js         fetch wrapper: bearer auth, silent token refresh, SSE streaming
  src/i18n.js         en/hi dictionary
  src/alert.js        SweetAlert2 (errors, confirmations)

backend/            FastAPI + SQLAlchemy + LangGraph
  app/main.py         app wiring, CORS, /me
  app/auth.py          OAuth (Google/GitHub), JWT access + refresh tokens
  app/agent.py          the research agent: tools, system prompt, loop, streaming
  app/threads.py         chat CRUD, SSE message streaming, PDF export, rate limiting
  app/billing.py          Stripe checkout + webhook
  app/llm_settings.py      per-user LLM provider/model/key config
  app/pricing.py            model catalog + $/Mtok cost math
  app/stats.py               per-thread cost & token stats
  app/admin.py                 admin user list + credit adjustment
  app/models.py, db.py, crypto.py, config.py, schemas.py
  tests/                       pytest suite (23 tests)
```

**Data flow for a message:** browser → `POST /threads/{id}/messages` → LangGraph agent streams Server-Sent Events (`tool_call`, `tool_result`, `delta`, `answer`, `usage`, `done`) → frontend renders the live trace and the answer as it streams → final answer + token usage persisted to Postgres.

## Tech stack

**Backend**: FastAPI, SQLAlchemy 2, Postgres (Neon), LangGraph + LangChain (OpenAI/Anthropic clients, works with any OpenAI-compatible provider), Authlib (OAuth), PyJWT, Fernet (`cryptography`), Stripe SDK, fpdf2, pytest.

**Frontend**: React 19, React Router, Vite, react-markdown + remark-gfm, SweetAlert2.

## Running locally

**Backend**
```bash
cd backend
uv sync
cp .env.example .env   # fill in DATABASE_URL, JWT_SECRET, FERNET_KEY at minimum
uv run fastapi dev app/main.py
```
Generate a `FERNET_KEY`: `python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`

**Frontend**
```bash
cd frontend
npm install
cp .env.example .env   # VITE_API_URL=http://localhost:8000
npm run dev
```

**Tests**
```bash
cd backend && uv run pytest -q
```

## Environment variables (backend)

| Variable | Required | Purpose |
|---|---|---|
| `DATABASE_URL` (or `NEON_DATABASE_URL`) | yes | Postgres connection string |
| `JWT_SECRET` | yes | signs access/refresh tokens |
| `FERNET_KEY` | yes | encrypts stored per-user LLM API keys |
| `FRONTEND_URL`, `BACKEND_URL` | yes | CORS + OAuth/Stripe redirect targets |
| `GOOGLE_CLIENT_ID/SECRET`, `GITHUB_CLIENT_ID/SECRET` | for OAuth | login providers |
| `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` | for billing | checkout + webhook verification |
| `TAVILY_API_KEY` | optional | primary web search (falls back to DuckDuckGo if unset) |
| `ADMIN_EMAILS` | optional | comma-separated emails granted `/admin` access |
| `COUPON_CODE`, `SIGNUP_CREDITS` | optional | free-credit coupon config |

## Known limitations

- Rate limiter and Tavily/DuckDuckGo results are per-process, not shared across replicas — fine at current scale, would move to Redis if horizontally scaled.
- Refresh tokens are stateless JWTs — can't be revoked individually before expiry (30 days).
- PDF export uses core PDF fonts (Latin-1); non-Latin scripts (e.g. the Hindi UI's own text) wouldn't render correctly if a report needed them — a bundled TTF would fix this.
- Model catalog and pricing (`app/pricing.py`) are hardcoded; provider pricing changes require a manual update.
