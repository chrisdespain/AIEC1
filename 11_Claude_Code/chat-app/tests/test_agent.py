import asyncio
import json
import os
import pytest

# Mark as integration — requires live SDK auth and REPO_PATH
pytestmark = pytest.mark.integration

@pytest.mark.asyncio
async def test_stream_response_returns_result():
    from dotenv import load_dotenv
    load_dotenv()

    # Reload agent so it picks up REPO_PATH from .env
    import importlib
    import agent
    importlib.reload(agent)

    events = []
    async for chunk in agent.stream_response("What is this repository?", "smoke-test-1"):
        if chunk.startswith("data: "):
            try:
                events.append(json.loads(chunk[6:].strip()))
            except json.JSONDecodeError:
                pass

    result_events = [e for e in events if e.get("type") == "result"]
    assert len(result_events) == 1
    assert len(result_events[0]["text"]) > 10
