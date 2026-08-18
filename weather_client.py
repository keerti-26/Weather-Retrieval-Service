"""NWS (National Weather Service) API client for fetching weather alerts."""
import json
import logging
from typing import List, Dict, Optional

import requests
from geopy.geocoders import Nominatim

# NWS API base URL
NWS_API_BASE_URL = "https://api.weather.gov"

logger = logging.getLogger(__name__)


class NWSClient:
    """Client for interacting with the National Weather Service API."""
    
    def __init__(self, base_url: str = "https://api.weather.gov"):
        """
        Initialize NWS API client.
        
        Args:
            base_url: Base URL for NWS API (default: https://api.weather.gov)
        """
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': '(Weather Retrieval Service, contact@example.com)'
        })
        self.geolocator = Nominatim(user_agent="weather_retrieval_service")
    
    def get_city_coordinates(self, city: str) -> Optional[tuple]:
        """
        Get latitude and longitude for a city.
        
        Args:
            city: City name (e.g., "Boston, MA" or "San Francisco, CA")
        
        Returns:
            Tuple of (latitude, longitude) or None if location not found
        """
        try:
            location = self.geolocator.geocode(city)
            if location:
                return (round(location.latitude, 4), round(location.longitude, 4))
            logger.warning(f"Location not found for city: {city}")
            return None
        except Exception as e:
            logger.error(f"Error geocoding city {city}: {e}")
            return None
    
    def get_grid_details(self, city:str) -> Optional[Dict]:
        """
        Fetch current weather conditions for a given city.
        
        Args:
            city: City name (e.g., "Boston, MA" or "San Francisco, CA")
        
        Returns:
            Dictionary of weather conditions or None if not found
        """
        try:
            coords = self.get_city_coordinates(city)
            if coords:
                logger.info(f"  Coordinates: {coords[0]}, {coords[1]}")
                lat, long = coords[0], coords[1]
                response = self.session.get(
                    f"{self.base_url}/points/{lat},{long}"
                )
                response.raise_for_status()
                grid_reponse = response.json().get("properties")
                return grid_reponse
        except Exception as e:
            logger.error(f"Not able to get the grid details for {city}: {e}")
            raise

    def get_cities_forecast(self, cities:List[str]) -> List[Dict]:
        """
        Fetch current weather conditions for a given city.
        
        Args:
            city: City name (e.g., "Boston, MA" or "San Francisco, CA")
        
        Returns:
            Dictionary of weather conditions or None if not found
        """
        all_normalized_forecasts = []
        
        for city in cities:
            try:
                forecast = self.get_forecast(city)
                normalized = self.normalize_forecast_for_db(city, forecast)
                all_normalized_forecasts.extend(normalized)
                logger.info(f"  Collected {len(normalized)} alerts from {city}")
                
            except Exception as e:
                logger.error(f"Failed to process city {city}: {e}")
                # Continue processing other cities even if one fails
                continue
        logger.info(f"Collected {len(all_normalized_forecasts)} alerts from {len(cities)} cities")
        return all_normalized_forecasts


    def get_forecast(self, city:str) -> List[Dict]:
        """
        Fetch current weather conditions for a given city.
        
        Args:
            city: City name (e.g., "Boston, MA" or "San Francisco, CA")
        
        Returns:
            Dictionary of weather conditions or None if not found
        """
        try:
            grid_response = self.get_grid_details(city)
            if grid_response:
                grid_id, grid_x, grid_y = grid_response.get("gridId"), grid_response.get("gridX"), grid_response.get("gridY")
                response = self.session.get(
                    f"{self.base_url}/gridpoints/{grid_id}/{grid_x},{grid_y}/forecast"
                )
                response.raise_for_status()
                forecast_response = response.json().get("properties").get("periods")
        except Exception as e:
            logger.error(f"Not able to get the forecast for {city}: {e}")
            raise
        return forecast_response

    def normalize_forecast_for_db(self, city: str, forecasts: List[Dict]) -> List[Dict]:
        """
        Normalize alert data into database schema format.
        
        Args:
            city: City name the alerts are associated with
            alerts: Raw alert data from NWS API
        
        Returns:
            List of dictionaries ready for database insertion
        """
        if not forecasts:
            return []
        
        normalized = []
        for forecast in forecasts:
            try:
                normalized.append({
                    "id": city+"_"+str(forecast.get("startTime"))+"_"+str(forecast.get("endTime")),
                    "location": city,
                    "number_counter": forecast.get("number"),
                    "day": forecast.get("name"),
                    "starttime": forecast.get("startTime"),
                    "endtime": forecast.get("endTime"),
                    "temperature": forecast.get("temperature"),
                    "precipitation_prob": forecast.get("probabilityOfPrecipitation")["value"],
                    "wind_speed": forecast.get("windSpeed"),
                    "wind_direction": forecast.get("windDirection"),
                    "detailed_forecast": forecast.get("detailedForecast")
                })
            except Exception as e:
                logger.warning(f"Error normalizing forecast for {city}: {e}")
                continue
        
        logger.info(f"Normalized {len(normalized)} forecast for {city}")
        return normalized
    
    def fetch_active_alerts(self, state_code: str) -> List[Dict]:
        """
        Fetch active weather alerts for a given state.
        
        Args:
            state_code: Two-letter state code (e.g., "MA", "CA", "TX")
        
        Returns:
            List of alert dictionaries with properties
        
        Raises:
            requests.HTTPError: If API request fails
        """
        try:
            response = self.session.get(
                f"{self.base_url}/alerts/active",
                params={"area": state_code},
                timeout=30
            )
            response.raise_for_status()
            
            features = response.json().get("features", [])
            alerts = [feature.get("properties", {}) for feature in features]
            
            logger.info(f"Fetched {len(alerts)} active alerts for state {state_code}")
            return alerts
            
        except requests.Timeout:
            logger.error(f"Request timeout while fetching alerts for {state_code}")
            raise
        except requests.HTTPError as e:
            logger.error(f"HTTP error fetching alerts for {state_code}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching alerts for {state_code}: {e}")
            raise
    
    def normalize_alerts_for_db(self, city: str, alerts: List[Dict]) -> List[Dict]:
        """
        Normalize alert data into database schema format.
        
        Args:
            city: City name the alerts are associated with
            alerts: Raw alert data from NWS API
        
        Returns:
            List of dictionaries ready for database insertion
        """
        if not alerts:
            return []
        
        normalized = []
        for alert in alerts:
            try:
                # Extract and validate required fields
                alert_id = alert.get("id")
                if not alert_id:
                    logger.warning(f"Skipping alert without ID for {city}")
                    continue
                
                normalized.append({
                    "id": str(alert_id),
                    "location": city,
                    "source_type": "alert",
                    "headline": alert.get("headline"),
                    "description": alert.get("description"),
                    "instruction": alert.get("instruction"),
                    "issued_at": alert.get("sent"),
                    "payload": json.dumps(alert)
                })
            except Exception as e:
                logger.warning(f"Error normalizing alert for {city}: {e}")
                continue
        
        logger.info(f"Normalized {len(normalized)} alerts for {city}")
        return normalized

    def fetch_alerts_for_cities(self, cities: List[str]) -> List[Dict]:
        """
        Fetch and normalize alerts for multiple cities.
        
        Args:
            cities: List of city names with state codes (e.g., ["Boston, MA", "Austin, TX"])
        
        Returns:
            List of normalized alert dictionaries ready for database insertion
        """
        all_normalized_alerts = []
        
        for city in cities:
            try:
                # Extract state code from city string (last 2 characters after comma)
                # Expected format: "City Name, ST"
                if ',' not in city:
                    logger.warning(f"City format incorrect (missing comma): {city}")
                    continue
                
                state_code = city.split(',')[-1].strip()[-2:]
                
                # Validate state code is 2 letters
                if len(state_code) != 2 or not state_code.isalpha():
                    logger.warning(f"Invalid state code extracted from {city}: {state_code}")
                    continue
                
                logger.info(f"Fetching alerts for {city} (state: {state_code})")
                
                # Get coordinates for logging/verification
                coords = self.get_city_coordinates(city)
                if coords:
                    logger.info(f"  Coordinates: {coords[0]}, {coords[1]}")
                
                # Fetch active alerts
                alerts = self.fetch_active_alerts(state_code)
                
                # Normalize for database
                normalized = self.normalize_alerts_for_db(city, alerts)
                all_normalized_alerts.extend(normalized)
                
                logger.info(f"  Collected {len(normalized)} alerts from {city}")
                
            except Exception as e:
                logger.error(f"Failed to process city {city}: {e}")
                # Continue processing other cities even if one fails
                continue
        
        logger.info(f"Total alerts collected: {len(all_normalized_alerts)}")
        return all_normalized_alerts
    
    def close(self):
        """Close the HTTP session."""
        self.session.close()
