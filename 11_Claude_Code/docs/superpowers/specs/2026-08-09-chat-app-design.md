# Codebase Concierge Chat App — Design Spec

**Date:** 2026-08-09
**Target repo:** `vercel/vercel` (TypeScript monorepo)
**Stack:** Python 3.12+, FastAPI, uv, Claude Agent SDK, RAGAS

---

## 1. Architecture & File Structure

```
chat-app/
├── CLAUDE.md
├── pyproject.toml
├── .env                   ← REPO_PATH + auth (gitignored)
├── .gitignore
├── main.py                ← FastAPI routes + static mount
├── agent.py               ← query() wrapper, SSE stream, session map
├── cache.py               ← FAQ cache: frequency counter + answer store
├── tools.py               ← 5 custom tools as in-process MCP server
├── eval/
│   ├── generate_testset.py  ← runs once: builds test_cases.json via RAGAS TestsetGenerator
│   ├── test_cases.json       ← generated Q&A corpus (gitignored until stable)
│   └── run_eval.py           ← imports agent.py directly, scores with RAGAS
├── tests/
│   ├── test_cache.py
│   └── test_agent.py
└── static/
    └── index.html
```

**Authentication:** The `claude-agent-sdk` resolves credentials in order:
`ANTHROPIC_API_KEY` → `ANTHROPIC_AUTH_TOKEN` → stored `claude auth login` profile.
No API key is required if the `claude` CLI is already authenticated.

**Target repo path** is set via `REPO_PATH` in `.env` (absolute path to the local
`vercel/vercel` clone). The server fails fast at startup if `REPO_PATH` is unset or
the directory does not exist.

---

## 2. Components & Data Flow

### `main.py`
FastAPI entry point. Mounts `static/` at `/` and defines:
- `GET /` → serves `static/index.html`
- `POST /api/chat` → receives `{"message": "...", "conversation_id": "..."}`,
  checks cache first, then delegates to `agent.py`, returns
  `StreamingResponse(media_type="text/event-stream")`

Cache check happens before the agent runs: if the normalized query is a cache hit,
the cached answer is streamed immediately as a single `result` SSE event — the agent
never runs.

### `agent.py`
Owns all SDK interaction:
- `_sessions: dict[str, str]` — maps `conversation_id` → SDK `session_id` (in-memory)
- `async def stream_response(message: str, conversation_id: str) -> AsyncGenerator`
  - Captures `session_id` from the first `SystemMessage` (`subtype="init"`)
  - Resumes via `ClaudeAgentOptions(resume=session_id)` on subsequent turns
  - Yields SSE-formatted chunks:
    - `data: {"type":"tool","name":"Read","input":"..."}\n\n` — tool-call progress
    - `data: {"type":"text","delta":"..."}\n\n` — streaming assistant text
    - `data: {"type":"result","text":"..."}\n\n` — final answer
    - `data: {"type":"error","text":"..."}\n\n` — any exception

`ClaudeAgentOptions` configuration:
```python
ClaudeAgentOptions(
    system_prompt="You are a concierge for the vercel/vercel repository. Answer concisely. Cite file paths.",
    allowed_tools=["Read", "Glob", "Grep",
                   "mcp__concierge__list_packages",
                   "mcp__concierge__git_log",
                   "mcp__concierge__find_exports",
                   "mcp__concierge__recent_features",
                   "mcp__concierge__search_features"],
    cwd=REPO_PATH,
    max_turns=25,
    mcp_servers={"concierge": server},
    resume=session_id,  # omitted on first turn
)
```

Server restart clears `_sessions`. The frontend's `conversation_id` persists in the
browser; the next message starts a fresh SDK session transparently.

### `cache.py`
In-memory FAQ cache:
- `normalize(query: str) -> str` — lowercase, strip punctuation, collapse whitespace
- `get(query: str) -> str | None` — cache lookup by normalized key
- `put(query: str, answer: str)` — store answer, increment frequency counter
- `top(n: int = 10) -> list[dict]` — return top-N queries by frequency for the FAQ panel
- No TTL for simplicity; cache lives for the server process lifetime

Token minimization: a cache hit skips the agent entirely — no SDK call, no token spend.

### `tools.py`
Five tools registered as a single in-process MCP server (`create_sdk_mcp_server`):

| Tool | Description | Implementation |
|------|-------------|----------------|
| `list_packages` | Enumerate packages in the monorepo | Read `packages/` directory entries |
| `git_log` | Recent commits | `git log --oneline -20` in `REPO_PATH` |
| `find_exports` | Exported symbols from a package | Grep for `^export` in package `src/` |
| `recent_features` | Summarize recent additions | `git log` + read recent commit diffs |
| `search_features` | Find a feature by keyword | `git log --all --grep=<keyword>` + grep `packages/*/README.md` headers |

All tools are read-only. No shell writes, no file mutations.

### `static/index.html`
Single-file frontend — plain HTML, CSS, and vanilla JS. No framework.
`highlight.js` loaded via CDN for code block syntax highlighting.

Layout:
- **Left sidebar:**
  - Conversation list (one entry per `conversation_id`, "New Chat" button generates UUID)
  - FAQ panel below conversation list — top-10 cached queries, clickable to pre-fill input
- **Right panel:**
  - Message history
  - Streaming assistant bubbles (incremental text, blinking cursor during stream)
  - Tool-call status chips above each answer ("reading `packages/cli/src/index.ts`…")
  - Collapsible "Sources" footer per response — files read, extracted from tool SSE events
  - Input box + send button

SSE reading: `fetch("/api/chat", {method:"POST", body: JSON.stringify({...})})` then
`response.body.getReader()` — `EventSource` is not used (GET-only; we need POST).

---

## 3. Error Handling

| Scenario | Behavior |
|----------|----------|
| `REPO_PATH` unset or missing | Server refuses to start; prints clear message |
| Agent exception | Caught in `stream_response()`; yields `{"type":"error"}` SSE event; frontend renders error bubble |
| `max_turns` exceeded | SDK returns `ResultMessage` with partial result; treated as normal completion |
| Cache read/write error | Log and fail open — agent runs, response served normally |
| Server restart | `_sessions` cleared; next message starts new SDK session; UI sidebar unaffected |

All errors surface as SSE events. No unhandled 500s reach the browser.

---

## 4. Token Minimization

1. **Cache hits** — exact-match normalized queries skip the agent entirely (largest saving)
2. **`max_turns=25`** — hard cap prevents runaway loops
3. **Lean system prompt** — 3–4 lines, no padding
4. **Targeted custom tools** — `search_features` and `find_exports` use precise grep patterns rather than broad file reads, reducing context the agent must process

---

## 5. Eval Harness (RAGAS)

### `eval/generate_testset.py`
Runs once. Loads these files from `vercel/vercel` as RAGAS `Document` objects:
`README.md`, `packages/*/README.md`, `packages/*/package.json` (description fields),
and the top-level `CHANGELOG.md` if present. Calls `TestsetGenerator` to produce
15–20 Q&A pairs covering the monorepo. Writes output to `test_cases.json`.

### `eval/run_eval.py`
Imports `stream_response()` from `agent.py` directly (no HTTP server needed).
For each test case:
1. Calls `stream_response(question, conversation_id=uuid4())` and collects all SSE events
2. Reconstructs `answer` from `result` event
3. Reconstructs `contexts` from `tool` events (file paths the agent read)
4. Scores with RAGAS metrics: `answer_relevancy`, `faithfulness`, `context_precision`

Prints a summary table and writes a JSON report.

---

## 6. Testing

| Layer | Command | What it covers |
|-------|---------|---------------|
| Cache unit tests | `uv run pytest tests/test_cache.py` | Hit/miss, normalization, frequency ordering, top-N |
| Agent smoke test | `uv run pytest tests/test_agent.py` | `stream_response()` returns a non-empty `result` |
| RAGAS eval | `uv run eval/run_eval.py` | Answer quality: relevancy, faithfulness, context precision |

Generate test cases first: `uv run eval/generate_testset.py`

---

## 7. Run Commands (for CLAUDE.md)

```bash
# Install
uv sync

# Run server
uv run uvicorn main:app --reload --port 8000

# Test endpoint
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"what does this repo do?","conversation_id":"test-1"}'

# Unit tests
uv run pytest tests/

# Generate eval test set (run once)
uv run eval/generate_testset.py

# Run RAGAS eval
uv run eval/run_eval.py
```

---

## 8. Constraints & Decisions

- **Read-only agent:** `allowed_tools` contains only `Read`, `Glob`, `Grep`, and the five
  custom tools. No `Write`, `Edit`, or `Bash`. The agent structurally cannot modify the
  filesystem regardless of user input.
- **In-memory state:** Both `_sessions` and `cache` live in process memory. A server
  restart clears them. Acceptable for a homework/demo app; a production version would
  use Redis or a database.
- **No frontend framework:** Plain HTML/CSS/JS + `highlight.js` CDN only. Keeps the
  frontend self-contained in a single file.
- **`vercel/vercel` as target:** All custom tools are written for this monorepo's
  structure (`packages/` layout, git history). Pointing `REPO_PATH` at a different repo
  will work for the built-in tools (`Read`, `Glob`, `Grep`) but the custom tools may
  return empty results.
