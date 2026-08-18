import os
import weather_broker
from fastmcp import FastMCP
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from contextvars import ContextVar
from datetime import datetime, date

# Context variable to store request headers
_request_context: ContextVar[dict] = ContextVar('request_context', default={})

mcp = FastMCP("Weather Data MCP Server")

class RequestContextMiddleware(BaseHTTPMiddleware):
    """Middleware to capture HTTP headers containing end-user identity."""
    async def dispatch(self, request: Request, call_next):
        # Capture headers that Databricks injects with user identity
        headers = {
            'x-forwarded-user': request.headers.get('x-forwarded-user'),
            'x-forwarded-email': request.headers.get('x-forwarded-email'),
        }
        _request_context.set(headers)
        response = await call_next(request)
        return response

@mcp.tool
async def get_current_weather_by_location(city: str) -> str:
    """
    Get current weather conditions for a city.
    
    Args:
        city: City name, e.g. "Boston, MA"
    
    Returns:
        Current weather data including temperature, precipitation probability,
        wind speed/direction, and detailed forecast. Returns error message if
        no data found or city invalid.
    """
    result = weather_broker.get_current_weather(city)
    if result is None:
        return f"No current weather data found for {city}. Please check the city name and try again."
    return str(result)

@mcp.tool
async def get_weather_forecast_by_location(city: str, days: int = 7) -> str:
    """
    Get weather forecast for a city for the next N days (1-7).
    
    Args:
        city: City name, e.g. "Boston, MA"
        days: Number of days to forecast (1-7), defaults to 7
    
    Returns:
        List of forecast periods with temperature, precipitation probability,
        wind conditions, and detailed descriptions. Returns error message if
        no data found or parameters invalid.
    """
    if days < 1 or days > 7:
        return "Invalid days parameter. Must be between 1 and 7."
    
    result = weather_broker.get_forecast(city, days)
    if not result:
        return f"No forecast data found for {city}. Please check the city name and try again."
    return str(result)

@mcp.tool
async def predict_umbrella_needed_by_location(city: str, date: date) -> str:
    """
    Predict whether an umbrella is needed for a city on a given date.
    
    Uses a threshold-based prediction: recommends an umbrella if the maximum
    precipitation probability for the day exceeds 40%.
    
    Args:
        city: City name, e.g. "Boston, MA"
        date: Date to predict umbrella needed (YYYY-MM-DD format)
    
    Returns:
        'Yes' if umbrella recommended (>40% precipitation probability),
        'No' if not needed (≤40% precipitation),
        'No data available' if no forecast exists,
        'Error' if lookup failed.
    """
    result = weather_broker.predict_umbrella_needed(city, date)
    
    # Enhance response with explanation
    if result == 'Yes':
        return f"Yes - An umbrella is recommended for {city} on {date}. Precipitation probability exceeds 40%."
    elif result == 'No':
        return f"No - An umbrella is not needed for {city} on {date}. Precipitation probability is 40% or lower."
    elif result == 'No data available':
        return f"No forecast data available for {city} on {date}. Unable to make prediction."
    else:  # Error case
        return f"Error retrieving forecast data for {city} on {date}. Please try again."


if __name__ == "__main__":
    # Add middleware to capture request headers for end-user identity
    # This must be done before mcp.run() is called
    if hasattr(mcp, 'app') and mcp.app is not None:
        mcp.app.add_middleware(RequestContextMiddleware)
    
    # Databricks Apps route external HTTP traffic to this port via app.yaml;
    # streamable-http is the transport Databricks' MCP client/gateway expects
    # (see the "Host your own MCP" doc linked in the module docstring above).
    port = int(os.getenv("DATABRICKS_APP_PORT", os.getenv("PORT", 8000)))
    mcp.run(transport="http", host="0.0.0.0", port=port)