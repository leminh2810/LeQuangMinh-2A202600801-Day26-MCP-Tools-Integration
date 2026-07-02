from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from google.adk import Agent
from google.adk.tools.mcp_tool.mcp_toolset import (
    McpToolset,
    StreamableHTTPConnectionParams,
)

load_dotenv()
load_dotenv(Path(__file__).resolve().parents[3] / ".env")

if not os.getenv("GOOGLE_API_KEY") and os.getenv("GEMINI_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8085/mcp")

AGENT_INSTRUCTION = """
You are a helpful weather assistant.
Use the MCP weather tools whenever the user asks about current weather,
forecast, or server health. Ask for a city only when the user did not provide one.
Keep answers concise and include units from the tool result.
"""

FALLBACK_INSTRUCTION = """
You are a weather assistant, but the MCP weather server is not connected.
Explain briefly that the local MCP server must be started before live weather tools
can be used.
"""

logger.info("Initializing weather agent with MCP server: %s", MCP_SERVER_URL)

try:
    connection_params = StreamableHTTPConnectionParams(
        url=MCP_SERVER_URL,
        timeout=30.0,
    )
    weather_tools = McpToolset(connection_params=connection_params)

    root_agent = Agent(
        name="weather_agent",
        model="gemini-2.5-flash",
        instruction=AGENT_INSTRUCTION,
        tools=[weather_tools],
    )
    logger.info("Weather agent initialized with remote MCP tools.")
except Exception:
    logger.exception("Failed to initialize MCP tools from %s", MCP_SERVER_URL)
    root_agent = Agent(
        name="weather_agent",
        model="gemini-2.5-flash",
        instruction=FALLBACK_INSTRUCTION,
    )
