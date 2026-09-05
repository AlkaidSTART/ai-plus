# AGENTS.md

Working agreement for AI coding agents. Models are strong enough now — no process
scaffolding needed. Only non-negotiable principles and the minimum set of project
facts live here.

## Project Facts

- InsightX: AI market-insight and decision system for cross-border e-commerce.
  Frontend and backend are separated and communicate only over HTTP (REST + SSE).
- `frontend/`: Vue 3 + Vite + TypeScript, dependencies managed with bun.
- `backend/`: FastAPI + LangGraph, Python >= 3.12, dependencies managed with uv.
- Common commands:
  - Frontend: `bun install` / `bun run dev` / `bun run build` (includes vue-tsc type check)
  - Backend: `uv sync` / `uv run uvicorn main:app --reload --port 8000` (`/docs` serves OpenAPI)
- Authoritative docs live in `docs/`: `PRD.md` (requirements & milestones),
  `api.md` (REST + SSE API contract), `04-技术方案.md` (architecture & tech choices).
- README and docs describe the target design; the code may lag behind. Treat the
  actual code as the source of truth. If docs and code disagree, point it out and
  confirm first — never invent an implementation to match the docs.

## Four Principles

### 1. Minimal closed loop

Ship the smallest change that works end to end; one task, one thing. If the task
is not explicitly a refactor, do not refactor — casual cleanup, casual abstraction,
and casual "optimization" all count as scope creep. The change boundary is the task:
no new abstractions, dependencies, or directories for the sake of elegance.

### 2. Plan first, then execute

For any non-trivial task, present a plan before touching code: what will be done,
which files change, how it gets verified. Keep the plan short — a clear list, not
an essay. If execution must deviate from the plan, say why.

### 3. No fabrication

Every claim needs a source: something read in the code, found in the docs, or
produced by a command. When unsure about a library or API behavior, look it up in
official docs or source code — never guess from memory. Saying "I'm not sure" is
always better than inventing functions, interfaces, configs, or doc quotes. If it
is not in the repo, say so.

### 4. Don't add features or requirements lightly

Do only what was asked. Unsolicited "enhancements" are off by default; at most
mention them as a suggestion when wrapping up. When a requirement is ambiguous,
take the minimal interpretation, state it, and proceed — do not widen scope. New
dependencies, config options, and APIs default to "no" unless the task explicitly
requires them.