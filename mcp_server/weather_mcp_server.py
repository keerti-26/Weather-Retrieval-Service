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
async def get_current_weather_by_location(city: str) -> dict:
    """
    Get current weather conditions for a city.
    
    Args:
        city: City name, e.g. "Boston, MA"
    
    Returns:
        Dictionary with keys: location, day, temperature, precipitation_prob,
        wind_speed, wind_direction, detailed_forecast.
        Returns error dict with 'error' key if no data found.
    """
    result = weather_broker.get_current_weather(city)
    if result is None:
        return {
            "error": f"No current weather data found for {city}. Please check the city name and try again."
        }
    return result

@mcp.tool
async def get_weather_forecast_by_location(city: str, days: int = 7) -> dict:
    """
    Get weather forecast for a city for the next N days (1-7).
    
    Args:
        city: City name, e.g. "Boston, MA"
        days: Number of days to forecast (1-7), defaults to 7
    
    Returns:
        Dictionary with 'forecasts' key containing list of forecast periods.
        Each period has: location, day, starttime, endtime, temperature,
        precipitation_prob, wind_speed, wind_direction, detailed_forecast.
        Returns error dict with 'error' key if invalid parameters or no data.
    """
    if days < 1 or days > 7:
        return {
            "error": "Invalid days parameter. Must be between 1 and 7."
        }
    
    result = weather_broker.get_forecast(city, days)
    if not result:
        return {
            "error": f"No forecast data found for {city}. Please check the city name and try again."
        }
    
    # Convert datetime objects to ISO format strings for JSON serialization
    serialized_result = []
    for period in result:
        serialized_period = dict(period)  # Make a copy
        if 'starttime' in serialized_period and serialized_period['starttime']:
            serialized_period['starttime'] = serialized_period['starttime'].isoformat()
        if 'endtime' in serialized_period and serialized_period['endtime']:
            serialized_period['endtime'] = serialized_period['endtime'].isoformat()
        serialized_result.append(serialized_period)
    
    return {"forecasts": serialized_result}

@mcp.tool
async def predict_umbrella_needed_by_location(city: str, date: date) -> dict:
    """
    Predict whether an umbrella is needed for a city on a given date.
    
    Uses a threshold-based prediction: recommends an umbrella if the maximum
    precipitation probability for the day exceeds 40%.
    
    Args:
        city: City name, e.g. "Boston, MA"
        date: Date to predict umbrella needed (YYYY-MM-DD format)
    
    Returns:
        Dictionary with keys:
        - recommendation: "yes" or "no"
        - reason: Explanation of the recommendation
        - threshold: The 40% threshold used
        - city: City queried
        - date: Date queried (ISO format)
        Returns error dict with 'error' key if no data or lookup failed.
    """
    result = weather_broker.predict_umbrella_needed(city, date)
    date_str = date.isoformat() if isinstance(date, (date, datetime)) else str(date)
    
    # Return structured response with explanation
    if result == 'Yes':
        return {
            "recommendation": "yes",
            "reason": f"An umbrella is recommended for {city} on {date_str}. Precipitation probability exceeds 40%.",
            "threshold": 40,
            "city": city,
            "date": date_str
        }
    elif result == 'No':
        return {
            "recommendation": "no",
            "reason": f"An umbrella is not needed for {city} on {date_str}. Precipitation probability is 40% or lower.",
            "threshold": 40,
            "city": city,
            "date": date_str
        }
    elif result == 'No data available':
        return {
            "error": f"No forecast data available for {city} on {date_str}. Unable to make prediction."
        }
    else:  # Error case
        return {
            "error": f"Error retrieving forecast data for {city} on {date_str}. Please try again."
        }


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