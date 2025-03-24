# weather_module.py

import time
import wifi_module
import json
import config
import adafruit_requests

# Cache for weather data
_weather_data = None
_last_weather_fetch = 0

# OpenWeather API settings
API_BASE_URL = "http://api.openweathermap.org/data/2.5/weather"
DEFAULT_CITY = "London"
DEFAULT_UNITS = "metric"  # Options: metric, imperial, standard

# Weather data fetch interval (default: 30 minutes)
WEATHER_FETCH_INTERVAL = 30 * 60


def get_weather_api_key():
    """
    Get the OpenWeather API key from environment variables (settings.toml) or config.
    Environment variable takes precedence over config settings.
    """
    import os
    
    # First check for environment variable from settings.toml
    env_key = os.getenv("WEATHER_API_KEY", "")
    if env_key:
        print("Using weather API key from environment variables")
        return env_key
        
    # Fall back to config if no environment variable
    config_key = config.get_value("WEATHER_API_KEY", "")
    if config_key:
        print("Using weather API key from config")
        
    return config_key


def get_city():
    """Get the configured city name"""
    return config.get_value("WEATHER_CITY", DEFAULT_CITY)


def get_units():
    """Get the configured units (metric or imperial)"""
    return config.get_value("WEATHER_UNITS", DEFAULT_UNITS)


def fetch_weather():
    """
    Fetch current weather data from OpenWeather API.
    
    Returns:
        dict: Weather data dictionary or None if failed
    """
    global _weather_data, _last_weather_fetch
    
    # Check if Wi-Fi is connected
    if not wifi_module.is_connected():
        print("Cannot fetch weather: Wi-Fi not connected")
        return None
    
    # Get API key
    api_key = get_weather_api_key()
    if not api_key:
        print("No weather API key configured")
        return None
    
    try:
        # Get socket and set up requests
        pool = wifi_module.get_socket_pool()
        if not pool:
            return None
            
        requests = adafruit_requests.Session(pool)
        
        # Build API URL
        city = get_city()
        units = get_units()
        url = f"{API_BASE_URL}?q={city}&units={units}&appid={api_key}"
        
        print(f"Fetching weather for {city}...")
        response = requests.get(url)
        
        if response.status_code == 200:
            # Parse JSON response
            data = response.json()
            _weather_data = data
            _last_weather_fetch = time.monotonic()
            print("Weather data updated successfully")
            return data
        else:
            print(f"Weather API error: {response.status_code}")
            print(response.text)
            return None
            
    except Exception as e:
        print(f"Error fetching weather: {e}")
        return None


def get_weather_data(force_refresh=False):
    """
    Get weather data, fetching from API if needed or if forced.
    
    Args:
        force_refresh: If True, forces a new API call regardless of cache age
        
    Returns:
        dict: Weather data dictionary or None if unavailable
    """
    global _weather_data, _last_weather_fetch
    
    now = time.monotonic()
    interval = config.get_value("WEATHER_FETCH_INTERVAL", WEATHER_FETCH_INTERVAL)
    
    # Check if we need to fetch new data
    if (force_refresh or 
        _weather_data is None or 
        (now - _last_weather_fetch) >= interval):
        return fetch_weather()
    
    # Return cached data
    return _weather_data


def format_weather_for_display():
    """
    Format weather data for display on the OLED.
    
    Returns:
        tuple: (line1, line2) formatted for display or (None, None) if no data
    """
    weather = get_weather_data()
    if not weather:
        return (None, None)
    
    try:
        # Extract data
        temp = weather["main"]["temp"]
        condition = weather["weather"][0]["main"]
        city = weather["name"]
        
        # Format temperature based on units
        units = get_units()
        if units == "metric":
            temp_str = f"{temp:.1f}°C"
        else:
            temp_str = f"{temp:.1f}°F"
        
        # Format lines
        line1 = f"{city}"
        line2 = f"{temp_str} {condition}"
        
        return (line1, line2)
    except (KeyError, IndexError) as e:
        print(f"Error formatting weather: {e}")
        return (None, None)


def set_city(city_name):
    """
    Update the city for weather fetching.
    
    Args:
        city_name: Name of the city to fetch weather for
        
    Returns:
        bool: True if successful, False otherwise
    """
    return config.set_value("WEATHER_CITY", city_name)


def set_api_key(api_key):
    """
    Set the OpenWeather API key.
    
    Args:
        api_key: OpenWeather API key
        
    Returns:
        bool: True if successful, False otherwise
    """
    return config.set_value("WEATHER_API_KEY", api_key)


def set_units(units):
    """
    Set the units for temperature (metric or imperial).
    
    Args:
        units: 'metric' for Celsius or 'imperial' for Fahrenheit
        
    Returns:
        bool: True if successful, False otherwise
    """
    if units not in ["metric", "imperial", "standard"]:
        return False
    return config.set_value("WEATHER_UNITS", units)
