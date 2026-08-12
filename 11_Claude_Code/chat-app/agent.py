import json
import os
from typing import AsyncGenerator
from claude_agent_sdk import (
    query, ClaudeAgentOptions,
    SystemMessage, AssistantMessage, UserMessage, ResultMessage,
    TextBlock, ToolUseBlock, ToolResultBlock,
)
from dotenv import load_dotenv

load_dotenv()

REPO_PATH = os.getenv("REPO_PATH", "")
_sessions: dict[str, str] = {}

SYSTEM_PROMPT = (
    "You are a concierge for the vercel/vercel monorepo. "
    "The repository is mounted at your working directory — always use your tools "
    "(Read, Glob, Grep) to look up accurate information before answering. "
    "Never ask which repository the user is referring to — it is always vercel/vercel. "
    "Answer concisely. Always cite file paths when referencing code."
)

def _get_server():
    from tools import server
    return server

async def stream_response(
    message: str, conversation_id: str
) -> AsyncGenerator[str, None]:
    session_id = _sessions.get(conversation_id)

    # Dynamic MCP server injection via mcp_servers is blocked when an enterprise
    # MCP config is present (the SDK raises an error at subprocess launch).
    # Respect that restriction: skip mcp_servers in enterprise environments so
    # the agent can still run using built-in tools (Read, Glob, Grep).
    # Set AGENT_DYNAMIC_MCP=1 to re-enable when the enterprise restriction is lifted.
    # Enterprise accounts block dynamic MCP server injection.
    # Set AGENT_DYNAMIC_MCP=1 in .env to enable custom tools once the restriction is lifted.
    use_dynamic_mcp = os.getenv("AGENT_DYNAMIC_MCP", "0") == "1"

    _MCP_TOOLS = [
        "mcp__concierge__list_packages",
        "mcp__concierge__git_log",
        "mcp__concierge__find_exports",
        "mcp__concierge__recent_features",
        "mcp__concierge__search_features",
    ]

    opts = ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        allowed_tools=["Read", "Glob", "Grep"] + (_MCP_TOOLS if use_dynamic_mcp else []),
        cwd=REPO_PATH,
        max_turns=25,
        **({"mcp_servers": {"concierge": _get_server()}} if use_dynamic_mcp else {}),
        **({"resume": session_id} if session_id else {}),
    )

    try:
        _tool_id_to_name: dict[str, str] = {}
        async for msg in query(prompt=message, options=opts):
            if isinstance(msg, SystemMessage) and msg.subtype == "init":
                _sessions[conversation_id] = msg.data["session_id"]

            elif isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        yield f'data: {json.dumps({"type": "text", "delta": block.text})}\n\n'
                    elif isinstance(block, ToolUseBlock):
                        _tool_id_to_name[block.id] = block.name
                        raw = str(block.input)
                        inp = raw[:200] + ("…" if len(raw) > 200 else "")
                        yield f'data: {json.dumps({"type": "tool", "name": block.name, "input": inp})}\n\n'
                    # ThinkingBlock and other block types are silently skipped

            elif isinstance(msg, UserMessage):
                if isinstance(msg.content, list):
                    for block in msg.content:
                        if isinstance(block, ToolResultBlock) and not block.is_error:
                            tool_name = _tool_id_to_name.get(block.tool_use_id, "")
                            # Only emit content for text-returning tools (not Glob path lists)
                            if tool_name in ("Read", "Grep") and isinstance(block.content, str):
                                snippet = block.content[:2000] + ("…" if len(block.content) > 2000 else "")
                                yield f'data: {json.dumps({"type": "tool_result", "tool": tool_name, "content": snippet})}\n\n'

            elif isinstance(msg, ResultMessage):
                yield f'data: {json.dumps({"type": "result", "text": msg.result})}\n\n'

    except Exception as exc:
        yield f'data: {json.dumps({"type": "error", "text": str(exc)})}\n\n'
