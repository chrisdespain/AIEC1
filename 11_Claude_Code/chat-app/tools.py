import os
import subprocess
from pathlib import Path
from claude_agent_sdk import tool, create_sdk_mcp_server

REPO_PATH = os.getenv("REPO_PATH", "")

@tool("list_packages", "List all packages in the vercel monorepo", {})
async def list_packages(args):
    packages_dir = Path(REPO_PATH) / "packages"
    if not packages_dir.is_dir():
        return {"content": [{"type": "text", "text": "packages/ directory not found"}]}
    names = sorted(p.name for p in packages_dir.iterdir() if p.is_dir())
    return {"content": [{"type": "text", "text": "\n".join(names)}]}

@tool("git_log", "Show recent git commits", {"count": int})
async def git_log(args):
    count = int(args.get("count", 20))
    result = subprocess.run(
        ["git", "log", "--oneline", f"-{count}"],
        cwd=REPO_PATH, capture_output=True, text=True,
    )
    return {"content": [{"type": "text", "text": result.stdout or result.stderr}]}

@tool("find_exports", "Find exported symbols from a package", {"package_name": str})
async def find_exports(args):
    pkg_src = Path(REPO_PATH) / "packages" / args["package_name"] / "src"
    if not pkg_src.is_dir():
        return {"content": [{"type": "text", "text": f"src/ not found for: {args['package_name']}"}]}
    result = subprocess.run(
        ["grep", "-r", "--include=*.ts", "^export", str(pkg_src)],
        capture_output=True, text=True,
    )
    lines = result.stdout.strip().split("\n")[:50]
    return {"content": [{"type": "text", "text": "\n".join(lines)}]}

@tool("recent_features", "Summarize recent additions from git history", {"days": int})
async def recent_features(args):
    days = int(args.get("days", 14))
    result = subprocess.run(
        ["git", "log", "--oneline", f"--since={days} days ago", "--no-merges"],
        cwd=REPO_PATH, capture_output=True, text=True,
    )
    return {"content": [{"type": "text", "text": result.stdout or "No recent commits found"}]}

@tool("search_features", "Search for a feature by keyword in git history and READMEs", {"keyword": str})
async def search_features(args):
    kw = args["keyword"]
    git_r = subprocess.run(
        ["git", "log", "--all", "--oneline", f"--grep={kw}"],
        cwd=REPO_PATH, capture_output=True, text=True,
    )
    grep_r = subprocess.run(
        ["grep", "-r", "--include=README.md", "-l", kw,
         str(Path(REPO_PATH) / "packages")],
        capture_output=True, text=True,
    )
    output = (
        f"Commits mentioning '{kw}':\n{git_r.stdout}\n\n"
        f"READMEs mentioning '{kw}':\n{grep_r.stdout}"
    )
    return {"content": [{"type": "text", "text": output.strip()}]}

server = create_sdk_mcp_server(
    name="concierge",
    version="1.0.0",
    tools=[list_packages, git_log, find_exports, recent_features, search_features],
)
