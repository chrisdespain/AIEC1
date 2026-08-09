import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

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

_STATIC_DIR = Path(__file__).parent / "static"

@app.get("/")
async def index():
    return FileResponse(_STATIC_DIR / "index.html")

@app.post("/api/chat")
async def chat(req: ChatRequest):
    return {"reply": req.message}

app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")
