#!/usr/bin/env python3
"""Verify the local Weather Agent lab setup."""

from __future__ import annotations

import asyncio
import os
import sys
import warnings
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None
else:
    load_dotenv()
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")

if not os.getenv("GOOGLE_API_KEY") and os.getenv("GEMINI_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8085/mcp")


def check_environment() -> bool:
    """Check whether the ADK client has a Google API key configured."""
    print("Checking environment configuration...")

    if load_dotenv is None:
        print("FAIL python-dotenv is not installed")
        return False

    load_dotenv()
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")

    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_google_api_key_here":
        print("FAIL GOOGLE_API_KEY is not configured")
        print("     Set GOOGLE_API_KEY in mcp-client/.env or GEMINI_API_KEY in the repo .env")
        return False

    source = "GOOGLE_API_KEY" if os.getenv("GOOGLE_API_KEY") else "GEMINI_API_KEY"
    print(f"OK   {source} configured ({len(api_key)} characters)")
    return True


def check_dependencies() -> bool:
    """Check whether required Python packages are importable."""
    print("\nChecking dependencies...")

    required_packages = [
        ("google.adk", "Google ADK"),
        ("mcp", "MCP"),
        ("httpx", "httpx"),
        ("dotenv", "python-dotenv"),
    ]

    all_installed = True
    for package, name in required_packages:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", FutureWarning)
                __import__(package)
            print(f"OK   {name}")
        except ImportError:
            print(f"FAIL {name} is not installed")
            all_installed = False

    if not all_installed:
        print("\nInstall dependencies with: uv sync")

    return all_installed


def check_agent_structure() -> bool:
    """Check whether ADK can discover the weather_agent package."""
    print("\nChecking agent structure...")

    required_files = [
        Path("weather_agent/agent.py"),
        Path("weather_agent/__init__.py"),
    ]

    all_exist = True
    for path in required_files:
        if path.exists():
            print(f"OK   {path}")
        else:
            print(f"FAIL {path} not found")
            all_exist = False

    return all_exist


def check_mcp_server() -> bool:
    """Connect to the MCP server and verify the expected tools are available."""
    print("\nChecking MCP server connectivity...")
    print(f"Server URL: {MCP_SERVER_URL}")

    async def test_connection() -> tuple[bool, str]:
        from mcp import ClientSession
        from mcp.client.streamable_http import streamable_http_client

        try:
            async with streamable_http_client(MCP_SERVER_URL) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    names = {tool.name for tool in tools.tools}
                    expected = {
                        "get_current_weather",
                        "get_forecast",
                        "health_check",
                    }
                    missing = expected - names
                    if missing:
                        return False, f"missing tools: {', '.join(sorted(missing))}"

                    health = await session.call_tool("health_check", {})
                    text = health.content[0].text if health.content else ""
                    return True, text
        except Exception as exc:
            return False, str(exc)

    ok, detail = asyncio.run(test_connection())
    if ok:
        print("OK   MCP server reachable")
        print(f"     health_check: {detail}")
        return True

    print(f"FAIL Cannot connect to MCP server: {detail}")
    print("     Start it first from ../mcp-server with: uv run python weather.py")
    return False


def check_agent_import() -> bool:
    """Import the ADK root_agent."""
    print("\nChecking agent import...")

    try:
        from weather_agent import root_agent

        print(f"OK   Agent imported: {root_agent.name}")
        print(f"     Model: {root_agent.model}")
        return True
    except Exception as exc:
        print(f"FAIL Failed to import agent: {exc}")
        return False


def main() -> int:
    print("=" * 60)
    print("Weather Agent Setup Verification")
    print("=" * 60)

    checks = [
        check_environment(),
        check_dependencies(),
        check_agent_structure(),
        check_mcp_server(),
        check_agent_import(),
    ]

    print("\n" + "=" * 60)
    if all(checks):
        print("All checks passed.")
        print("Run the client UI with: uv run adk web")
        print("Then open: http://localhost:8000")
        return 0

    print("Some checks failed. Fix the items above and run this script again.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
