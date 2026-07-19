"""Entrypoint that starts the LangGraph API server in-memory (no license required).

Used by Dockerfile.vercel to serve the agent on Vercel Container Images.
Reads the graph config from langgraph.json and starts the Starlette/Uvicorn
server on 0.0.0.0:$PORT (Vercel injects $PORT; defaults to 2024 locally).
"""

import json
import os

from langgraph_api.cli import run_server


def main() -> None:
    config_path = os.environ.get("LANGGRAPH_CONFIG", "langgraph.json")
    with open(config_path, encoding="utf-8") as f:
        config_data = json.load(f)

    port = int(os.environ.get("PORT", "2024"))

    # When deployed on Vercel, env vars are injected directly — no .env file needed.
    # For local Docker testing, pass --env-file .env to docker run.
    env_path = config_data.get("env", None)
    if env_path and not os.path.exists(env_path):
        env_path = None

    run_server(
        host="0.0.0.0",
        port=port,
        reload=False,
        graphs=config_data.get("graphs", {}),
        env=env_path,
        auth=config_data.get("auth"),
        ui=config_data.get("ui"),
        webhooks=config_data.get("webhooks"),
        ui_config=config_data.get("ui_config"),
        checkpointer=config_data.get("checkpointer"),
        open_browser=False,
        runtime_edition="inmem",
    )


if __name__ == "__main__":
    main()
