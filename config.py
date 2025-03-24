# config.py

import config_manager

# Get configuration from the config manager
# This will load from settings.json if available, or create it with defaults
def get_config():
    """
    Returns the current configuration dictionary.
    """
    return config_manager.get_config()

# Shortcut functions for common operations
def get_value(key, default=None):
    """Get a config value with optional default"""
    return config_manager.get_value(key, default)

def set_value(key, value, save_immediately=True):
    """Update a config value and optionally save to disk"""
    return config_manager.set_value(key, value, save_immediately)

# Provide legacy compatibility through the 'config' attribute
# This allows existing code to use config.config["KEY"] without changes
config = get_config()
