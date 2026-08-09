# Codebase Concierge

## Run Commands

```bash
# Install dependencies
uv sync

# Start server (requires REPO_PATH in .env)
uv run uvicorn main:app --reload --port 8000

# Test endpoint
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"what does this repo do?","conversation_id":"test-1"}'

# Run unit tests
uv run pytest tests/ -v

# Generate RAGAS test cases (run once, needs OPENAI_API_KEY)
uv run eval/generate_testset.py

# Run RAGAS eval
uv run eval/run_eval.py
```

## Architecture

The chat logic lives entirely in `agent.py:stream_response()`. This is the seam where
the Claude Agent SDK connects to FastAPI. `main.py`'s `/api/chat` handler delegates to
this function — do not embed agent logic in `main.py`.

`cache.py` is checked before calling `stream_response()`. A cache hit skips the agent
entirely — no SDK call, no token spend.

## Conventions

- No frontend framework — plain HTML/CSS/JS only (`static/index.html`)
- Agent is read-only: `allowed_tools` never includes Write, Edit, or Bash
- Custom tools live in `tools.py`; add new tools there and register them in `server`
- `.env` is gitignored — never commit it
