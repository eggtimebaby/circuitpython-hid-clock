# boot.py - Run before code.py to initialize configuration in read-only filesystem

import os
import storage
import supervisor
import sys
import gc

# Notify that boot.py is running
print("Boot.py: Initializing with read-only filesystem")

# Import config_manager for direct access to the module
sys.path.append("/")
import config_manager

# First, tell config_manager that filesystem is read-only to avoid unnecessary
# attempts to create or modify files
config_manager._filesystem_readonly = True

# Load TOML settings into memory
# CircuitPython can read settings.toml even in read-only mode
try:
    from adafruit_toml import toml_load
    
    # Check if settings.toml exists and has content
    try:
        settings = toml_load("/settings.toml")
        print("Boot.py: Loaded settings from settings.toml")
        
        # Start with default config
        config = config_manager.DEFAULT_CONFIG.copy()
        
        # Map known TOML settings to config_manager format
        # Weather settings
        if "WEATHER_API_KEY" in settings:
            config["WEATHER_API_KEY"] = settings["WEATHER_API_KEY"]
        if "WEATHER_CITY" in settings:
            config["WEATHER_CITY"] = settings["WEATHER_CITY"]
        if "WEATHER_UNITS" in settings:
            config["WEATHER_UNITS"] = settings["WEATHER_UNITS"]
            
        # WiFi settings - map from CircuitPython's naming convention
        if "CIRCUITPY_WIFI_SSID" in settings:
            config["WIFI_SSID"] = settings["CIRCUITPY_WIFI_SSID"]
        if "CIRCUITPY_WIFI_PASSWORD" in settings:
            config["WIFI_PASSWORD"] = settings["CIRCUITPY_WIFI_PASSWORD"]
            
        # Time settings - check for custom timezone
        if "TIMEZONE" in settings:
            config["TIMEZONE"] = settings["TIMEZONE"]
        if "DST" in settings:
            config["DST"] = settings["DST"]
            
        # Device settings
        if "SETTINGS_MODE" in settings:
            config["SETTINGS_MODE"] = settings["SETTINGS_MODE"]

        # Store settings in config_manager's memory and set it as already loaded
        # so it doesn't try to reload from nonexistent settings.json
        config_manager._config = config
        print("Boot.py: Preloaded configuration in memory")
    except OSError as e:
        print(f"Boot.py: Could not read settings.toml: {e}")
except ImportError:
    print("Boot.py: Trying fallback method for TOML")
    try:
        # Manual parsing of settings.toml (simplified)
        with open("/settings.toml", "r") as f:
            settings_text = f.read()
            settings = {}
            
            # Very basic TOML parsing for key = "value" pairs
            for line in settings_text.splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    try:
                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip()
                        # Remove quotes if present
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        settings[key] = value
                    except ValueError:
                        pass  # Skip lines that don't fit key=value format
            
            # Convert TOML settings to the format expected by config_manager
            config = config_manager.DEFAULT_CONFIG.copy()
            
            # Map settings similar to above
            if "WEATHER_API_KEY" in settings:
                config["WEATHER_API_KEY"] = settings["WEATHER_API_KEY"]
            if "WEATHER_CITY" in settings:
                config["WEATHER_CITY"] = settings["WEATHER_CITY"]
            if "WEATHER_UNITS" in settings:
                config["WEATHER_UNITS"] = settings["WEATHER_UNITS"]
                
            # WiFi settings
            if "CIRCUITPY_WIFI_SSID" in settings:
                config["WIFI_SSID"] = settings["CIRCUITPY_WIFI_SSID"]
            if "CIRCUITPY_WIFI_PASSWORD" in settings:
                config["WIFI_PASSWORD"] = settings["CIRCUITPY_WIFI_PASSWORD"]
                
            # Time settings - check for custom timezone
            if "TIMEZONE" in settings:
                config["TIMEZONE"] = settings["TIMEZONE"]
            if "DST" in settings:
                config["DST"] = settings["DST"]
                
            # Device settings
            if "SETTINGS_MODE" in settings:
                config["SETTINGS_MODE"] = settings["SETTINGS_MODE"]
                
            # Store settings in config_manager's memory
            config_manager._config = config
            print("Boot.py: Preloaded configuration using basic parsing")
    except Exception as e:
        print(f"Boot.py: Error loading settings: {e}")
        print("Boot.py: Using default config")

# Essential: save available RAM for later operations
gc.collect()
