import asyncio
import os
from dotenv import load_dotenv
from claude_agent_sdk import query, ClaudeAgentOptions

load_dotenv()
REPO_PATH = os.getenv("REPO_PATH", "")

async def main():
    async for message in query(
        prompt="What does this project do? Answer in two sentences.",
        options=ClaudeAgentOptions(
            allowed_tools=["Read", "Glob", "Grep"],
            cwd=REPO_PATH,
            max_turns=5,
        ),
    ):
        print(type(message).__name__, end=" ")
        if hasattr(message, "result"):
            print("\n\nResult:", message.result)
        else:
            print()

asyncio.run(main())
