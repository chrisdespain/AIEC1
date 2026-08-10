# Codebase Concierge

A chat web app that lets you ask questions about the [vercel/vercel](https://github.com/vercel/vercel) monorepo in natural language, powered by the Claude Agent SDK.

## Features

- **Streaming responses** — SSE via `fetch()` + `ReadableStream`; tool calls appear as chips while the agent works
- **Multi-conversation sidebar** — each conversation maps to its own SDK session with full memory
- **FAQ cache** — exact-match queries bypass the agent entirely (zero token spend); a sidebar panel shows the most-asked questions
- **5 custom read-only tools** — `list_packages`, `git_log`, `find_exports`, `recent_features`, `search_features`
- **Session resumption** — follow-up questions use the same SDK session (no context re-injection)
- **RAGAS eval harness** — auto-generates test cases from repo READMEs and scores `answer_relevancy`, `faithfulness`, `context_precision`

## Setup

### Prerequisites

- [uv](https://docs.astral.sh/uv/) installed
- Claude Code authenticated (`claude auth login`)
- The vercel/vercel repo cloned locally
- OpenAI API key (for the RAGAS eval only)

### Install

```bash
uv sync
```

### Configure

Create `.env` (gitignored):

```
REPO_PATH=/path/to/vercel/vercel
OPENAI_API_KEY=sk-...
```

Set `REPO_PATH` to wherever you cloned `git@github.com:vercel/vercel.git`.

### Run

```bash
uv run uvicorn main:app --reload --port 8000
```

Open `http://localhost:8000`.

## Project Structure

```
chat-app/
├── main.py                   # FastAPI app: GET /, GET /api/faq, POST /api/chat
├── agent.py                  # stream_response() — wraps claude-agent-sdk query()
├── cache.py                  # Normalize → store → frequency → top-N
├── tools.py                  # 5 read-only MCP tools + create_sdk_mcp_server()
├── static/index.html         # Full frontend (no framework)
├── tests/
│   ├── test_cache.py         # Unit tests (7)
│   └── test_agent.py         # Integration smoke test (requires live SDK auth)
└── eval/
    ├── generate_testset.py   # RAGAS TestsetGenerator → test_cases.json
    └── run_eval.py           # Score agent responses with RAGAS metrics
```

## Tests

```bash
# Unit tests (fast, no auth required)
uv run pytest tests/test_cache.py -v

# Integration smoke test (requires live SDK auth + REPO_PATH)
uv run pytest tests/test_agent.py -v -m integration
```

## Eval

```bash
# Generate test cases once (needs OPENAI_API_KEY, takes ~2 min)
uv run eval/generate_testset.py

# Score agent responses (runs agent on each test case, takes 5–15 min)
uv run eval/run_eval.py
```

## Notes

- The agent is **read-only**: `allowed_tools` never includes Write, Edit, or Bash
- Custom MCP tools require `AGENT_DYNAMIC_MCP=1` in `.env` (enterprise accounts restrict dynamic MCP injection)
- `.env` is gitignored — never commit it
