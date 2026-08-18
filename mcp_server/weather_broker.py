import lakebase
from typing import List, Optional
import logging
from datetime import date

logger = logging.getLogger(__name__)

def get_current_weather(city: str) -> Optional[dict]:
    """
    Get the current weather for a city from NWS.
    
    Args:
        city: City name, e.g. "Boston, MA".
    
    Returns:
        A dict with location, day, temperature, precipitation_prob, wind_speed, wind_direction, and detailed_forecast.
        Returns None if no current forecast found.
    """
    try:
        with lakebase.get_connection() as conn:
            cursor = conn.cursor() 
            cursor.execute("""
            SELECT location, day, temperature, precipitation_prob, wind_speed, wind_direction, detailed_forecast
            FROM weather_forecast
            WHERE location = %s AND CURRENT_TIMESTAMP BETWEEN starttime AND endtime
            ORDER BY starttime DESC
            LIMIT 1
            """,
            (city,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    except Exception as e:
        logger.error(f"Error getting current weather for {city}: {e}")
        return None

def get_forecast(city:str, days:int=1) -> List[dict]:
    """
    Get the forecast of the city for n number of days from NWS
    Args:
        city: City name, e.g. "Boston, MA".
        days: 1 to 7 days
    
    Returns:
        A list of dicts with location, day, starttime, endtime, temperature, precipitation_prob, wind_speed, wind_direction, and detailed_forecast.
        Returns empty list if no forecast found.
    """
    try:
        # Validate days parameter to prevent SQL injection
        if not isinstance(days, int) or days < 1 or days > 7:
            logger.error(f"Invalid days parameter: {days}. Must be integer 1-7.")
            return []
        
        with lakebase.get_connection() as conn:
            cursor = conn.cursor() 
            # Safe to use f-string here since days is validated as integer
            cursor.execute(f"""
            SELECT location, day, starttime, endtime, temperature, precipitation_prob, wind_speed, wind_direction, detailed_forecast
            FROM weather_forecast
            WHERE location = %s AND starttime BETWEEN CURRENT_TIMESTAMP AND CURRENT_TIMESTAMP + INTERVAL '{days}' DAY
            ORDER BY starttime ASC
            """,
            (city,)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Error getting forecast for {city}: {e}")
        return []

def predict_umbrella_needed(city: str, date: date) -> str:
    """
    Check the precipitation probability for the day and return whether an umbrella is needed for the day if it is greater than 40
    Args:
        city: City name, e.g. "Boston, MA".
        date: date object, e.g. datetime.date(2026, 8, 19)
    
    Returns:
        'Yes' if umbrella needed (>40% precipitation), 'No' if not needed, 'No data available' if no forecast, or 'Error' on exception
    """
    try:
        with lakebase.get_connection() as conn:
            cursor = conn.cursor() 
            cursor.execute("""
            SELECT MAX(precipitation_prob) as max_precip
            FROM weather_forecast
            WHERE location = %s AND DATE(starttime) = %s
            """,
            (city, date)
            )
            row = cursor.fetchone()
            if row and row['max_precip'] is not None:
                return 'Yes' if row['max_precip'] > 40 else 'No'
            return 'No data available'
    except Exception as e:
        logger.error(f"Error predicting umbrella for {city} on {date}: {e}")
        return 'Error'


        