# config_manager.py

import json
import os
import time

# Default configuration values
DEFAULT_CONFIG = {
    # Time settings
    "TIMEZONE": "America/New_York",  # Default to America/New_York instead of UK
    "DST": True,  # Default to True as most regions use DST
    "NTP_SERVERS": ["pool.ntp.org", "time.google.com"],
    "NTP_SYNC_INTERVAL": 86400,
    "NTP_SYNC_ON_STARTUP": True,
    "NTP_SYNC_RETRY_INTERVAL": 300,
    
    # UI settings
    "SHOW_MIC_STATE_DURATION": 2.0,
    "DISPLAY_ROTATION_INTERVAL": 10,  # Seconds between rotating display content
    "DISPLAY_ROTATION_ENABLED": True,  # Whether to rotate between time and other info
    
    # HID settings
    "MIC_SHORTCUT": ["LEFT_CONTROL", "LEFT_SHIFT", "M"],
    
    # Weather settings
    "WEATHER_API_KEY": "",  # Empty by default, retrieve from settings.toml/env
    "WEATHER_CITY": "New York",  # Changed default city to match timezone
    "WEATHER_UNITS": "imperial",  # Changed to imperial for US users
    "WEATHER_FETCH_INTERVAL": 1800,  # Seconds between weather updates (30 mins)
    "WEATHER_ENABLED": True,  # Whether to show weather in the display rotation
    
    # WiFi settings
    "WIFI_SSID": "",  # Will be populated from settings.toml
    "WIFI_PASSWORD": "",
    
    # Settings mode
    "SETTINGS_MODE": False  # When True, display setup instructions instead of using APIs
}

# Path to the settings file
CONFIG_FILE = "/settings.json"

# In-memory cached configuration
_config = None
_config_last_modified = 0
_config_last_check = 0
_config_check_interval = 10  # Seconds between checking for file changes
_filesystem_readonly = False


def get_config():
    """
    Returns the current configuration, loading it from file if necessary.
    If the file doesn't exist, creates it with default values first.
    
    Returns:
        dict: The current configuration dictionary
    """
    global _config, _config_last_modified, _config_last_check, _filesystem_readonly
    
    now = time.monotonic()
    
    # If we haven't loaded config yet or it's time to check for updates
    if _config is None or (now - _config_last_check) > _config_check_interval:
        _config_last_check = now
        
        # If we already know the filesystem is read-only, skip file operations
        if _filesystem_readonly:
            # If config is None, use defaults but don't try to save
            if _config is None:
                _config = DEFAULT_CONFIG.copy()
            return _config
            
        # Check if config file exists and if it's been modified
        try:
            stat = os.stat(CONFIG_FILE)
            file_modified = stat[8]  # 8 is st_mtime in CircuitPython os.stat
            
            # If file was modified since we last loaded it, or we never loaded it
            if _config is None or file_modified > _config_last_modified:
                load_config()
                _config_last_modified = file_modified
        except OSError:
            # File doesn't exist, create it with defaults
            print(f"Config file {CONFIG_FILE} not found, creating with defaults")
            save_config(DEFAULT_CONFIG)
            _config = DEFAULT_CONFIG.copy()
    
    return _config


def load_config():
    """
    Load configuration from the settings file.
    If the file doesn't exist or has invalid JSON, load the defaults.
    """
    global _config
    
    try:
        with open(CONFIG_FILE, "r") as f:
            file_content = f.read()
            if file_content.strip():  # Make sure file isn't empty
                loaded_config = json.loads(file_content)
                
                # Start with defaults, then update with loaded values
                # This ensures any new config options get default values
                merged_config = DEFAULT_CONFIG.copy()
                merged_config.update(loaded_config)
                _config = merged_config
                
                print(f"Loaded configuration from {CONFIG_FILE}")
                return
    except (OSError, ValueError) as e:
        print(f"Error loading config: {e}")
    
    # If we get here, either the file doesn't exist, is empty, or has invalid JSON
    _config = DEFAULT_CONFIG.copy()
    print("Using default configuration")


def save_config(config=None):
    """
    Save the configuration to the settings file.
    
    Args:
        config: The configuration to save. If None, saves the current in-memory config.
    
    Returns:
        bool: True if the save was successful or if using in-memory only config,
              False if save failed for a reason other than read-only filesystem
    """
    global _config, _config_last_modified, _filesystem_readonly
    
    # If we already know filesystem is read-only, don't try to save
    if _filesystem_readonly:
        print("Filesystem is read-only, using in-memory config only")
        # Still update the in-memory config
        if config is not None:
            _config = config
        return True
    
    # If no config provided, use the current one
    if config is None:
        config = _config
        
    # If still None, use defaults
    if config is None:
        config = DEFAULT_CONFIG.copy()
        _config = config
    
    try:
        # Convert to JSON and save
        json_str = json.dumps(config)
        with open(CONFIG_FILE, "w") as f:
            f.write(json_str)
        
        # Update the last modified time
        try:
            stat = os.stat(CONFIG_FILE)
            _config_last_modified = stat[8]  # 8 is st_mtime
        except OSError:
            pass
            
        print(f"Saved configuration to {CONFIG_FILE}")
        return True
    except OSError as e:
        # Check for read-only filesystem (error code 30 in CircuitPython)
        if getattr(e, 'args', [None])[0] == 30:  # Read-only filesystem
            _filesystem_readonly = True
            print("Filesystem is read-only, using in-memory config only")
            # Still update the in-memory config
            _config = config
            return True
        else:
            print(f"Error saving config: {e}")
            return False
    except ValueError as e:
        print(f"Error saving config: {e}")
        return False


def get_value(key, default=None):
    """
    Get a specific configuration value.
    
    Args:
        key: The configuration key to retrieve
        default: The default value to return if the key doesn't exist
    
    Returns:
        The value for the given key, or the default if not found
    """
    config = get_config()
    return config.get(key, default)


def set_value(key, value, save_immediately=True):
    """
    Set a specific configuration value.
    
    Args:
        key: The configuration key to set
        value: The value to set
        save_immediately: If True, saves to disk immediately. 
                         If False, only updates in-memory config.
    
    Returns:
        bool: True if successful, False if save failed (always True if save_immediately=False)
    """
    global _config
    
    # Ensure config is loaded
    config = get_config()
    
    # Update the value
    config[key] = value
    
    # Save if requested
    if save_immediately:
        return save_config()
    
    return True
