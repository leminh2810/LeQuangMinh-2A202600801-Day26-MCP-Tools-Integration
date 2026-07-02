from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

PORT = int(os.getenv("PORT", "8085"))
WEATHERAPI_BASE = "https://api.weatherapi.com/v1"
USER_AGENT = "weather-mcp-lab/1.0"
API_KEY = os.getenv("WEATHERAPI_KEY")

mcp = FastMCP("weather", host="0.0.0.0", port=PORT)


async def make_weather_request(
    endpoint: str,
    params: dict[str, str],
) -> dict[str, Any] | None:
    """Call WeatherAPI and return parsed JSON, or None on any recoverable error."""
    if not API_KEY:
        print("ERROR: WEATHERAPI_KEY is not set. Create a free key at https://weatherapi.com.")
        return None

    url = f"{WEATHERAPI_BASE}/{endpoint}"
    request_params = params | {"key": API_KEY}
    headers = {"User-Agent": USER_AGENT}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                url,
                headers=headers,
                params=request_params,
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            print(f"WeatherAPI HTTP error {exc.response.status_code}: {exc.response.text}")
        except httpx.RequestError as exc:
            print(f"WeatherAPI request error: {exc}")
        except ValueError as exc:
            print(f"WeatherAPI returned invalid JSON: {exc}")

    return None


@mcp.tool()
async def get_current_weather(city: str) -> str:
    """Get current weather conditions for a city.

    Args:
        city: City name, for example Hanoi, Haiphong, Danang, Brisbane, or Sydney.
    """
    data = await make_weather_request(
        "current.json",
        {
            "q": city,
            "aqi": "no",
        },
    )

    if data is None:
        if not API_KEY:
            return "WeatherAPI key is not configured. Set WEATHERAPI_KEY with your key from weatherapi.com."
        return f"Unable to fetch current weather data for {city}. Check the city name and API key."

    location = data["location"]
    current = data["current"]

    return f"""Current Weather for {location['name']}, {location['region']}, {location['country']}:

Temperature: {current['temp_c']} C ({current['temp_f']} F)
Feels like: {current['feelslike_c']} C ({current['feelslike_f']} F)
Condition: {current['condition']['text']}
Humidity: {current['humidity']}%
Wind: {current['wind_kph']} km/h ({current['wind_mph']} mph) {current['wind_dir']}
Pressure: {current['pressure_mb']} mb
UV Index: {current['uv']}
Visibility: {current['vis_km']} km

Last updated: {current['last_updated']}"""


@mcp.tool()
async def get_forecast(city: str, days: int = 3) -> str:
    """Get a weather forecast for a city.

    Args:
        city: City name, for example Hanoi, Haiphong, Danang, Brisbane, or Sydney.
        days: Number of forecast days. The free WeatherAPI tier supports 1 to 3 days.
    """
    safe_days = max(1, min(int(days), 3))
    data = await make_weather_request(
        "forecast.json",
        {
            "q": city,
            "days": str(safe_days),
            "aqi": "no",
            "alerts": "no",
        },
    )

    if data is None:
        if not API_KEY:
            return "WeatherAPI key is not configured. Set WEATHERAPI_KEY with your key from weatherapi.com."
        return f"Unable to fetch forecast data for {city}. Check the city name and API key."

    location = data["location"]
    forecast_days = data["forecast"]["forecastday"]
    forecasts = [
        f"Weather Forecast for {location['name']}, {location['region']}, {location['country']}:"
    ]

    for forecast_day in forecast_days:
        day = forecast_day["day"]
        forecasts.append(
            f"""{forecast_day['date']}:
High: {day['maxtemp_c']} C ({day['maxtemp_f']} F)
Low: {day['mintemp_c']} C ({day['mintemp_f']} F)
Condition: {day['condition']['text']}
Chance of Rain: {day['daily_chance_of_rain']}%
Max Wind: {day['maxwind_kph']} km/h
UV Index: {day['uv']}"""
        )

    return "\n---\n".join(forecasts)


@mcp.tool()
async def health_check() -> str:
    """Verify that the Weather MCP server is running."""
    api_key_status = "configured" if API_KEY else "missing"
    return f"Weather MCP Server is running. WEATHERAPI_KEY status: {api_key_status}."


if __name__ == "__main__":
    if "--stdio" in sys.argv:
        print("Starting Weather MCP server in stdio mode", file=sys.stderr)
        mcp.run()
    else:
        print(f"Starting Weather MCP server on http://0.0.0.0:{PORT}/mcp")
        print("Tools: get_current_weather, get_forecast, health_check")
        mcp.run(transport="streamable-http")
