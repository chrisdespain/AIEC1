import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import cache
import agent

load_dotenv()

_STATIC_DIR = Path(__file__).parent / "static"

@asynccontextmanager
async def lifespan(app: FastAPI):
    repo_path = os.getenv("REPO_PATH", "")
    if not repo_path or not Path(repo_path).is_dir():
        raise RuntimeError(f"REPO_PATH is not set or does not exist: {repo_path!r}")
    yield

app = FastAPI(lifespan=lifespan)

class ChatRequest(BaseModel):
    message: str
    conversation_id: str

@app.get("/")
async def index():
    return FileResponse(_STATIC_DIR / "index.html")

@app.get("/api/faq")
async def faq():
    return cache.top(10)

@app.post("/api/chat")
async def chat(req: ChatRequest):
    cached_answer = cache.get(req.message)
    if cached_answer:
        cache.hit(req.message)
        async def cached_stream():
            yield f'data: {json.dumps({"type": "result", "text": cached_answer, "cached": True})}\n\n'
        return StreamingResponse(cached_stream(), media_type="text/event-stream")

    async def live_stream():
        result_text = None
        tool_used = False
        async for chunk in agent.stream_response(req.message, req.conversation_id):
            yield chunk
            if chunk.startswith("data: "):
                try:
                    data = json.loads(chunk[6:].strip())
                    if data.get("type") == "result":
                        result_text = data.get("text", "")
                    elif data.get("type") == "tool":
                        tool_used = True
                except json.JSONDecodeError:
                    pass
        if result_text and tool_used:
            cache.put(req.message, result_text)

    return StreamingResponse(live_stream(), media_type="text/event-stream")

app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")
