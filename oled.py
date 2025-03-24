# oled.py

import time
import board
import busio
import displayio
import terminalio
from adafruit_display_text import label
import adafruit_displayio_ssd1306
import config

# Release any displays in case something was initialized before
displayio.release_displays()

# I2C + SSD1306 Setup
i2c = busio.I2C(board.GP1, board.GP0)  # SCL=GP1, SDA=GP0
display_bus = displayio.I2CDisplay(i2c, device_address=0x3C)

WIDTH = 128
HEIGHT = 64

display = adafruit_displayio_ssd1306.SSD1306(
    display_bus, width=WIDTH, height=HEIGHT
)

# ===== Display Groups and Labels =====

# Main display group
splash = displayio.Group()
display.root_group = splash

# Time display - large centered text
main_label = label.Label(
    font=terminalio.FONT,
    text="INIT",
    color=0xFFFFFF,
    scale=2,
    anchor_point=(0.5, 0.5),
    anchored_position=(WIDTH // 2, HEIGHT // 2)
)

# Status message display - smaller text
status_label = label.Label(
    font=terminalio.FONT,
    text="",
    color=0xFFFFFF,
    scale=1,
    anchor_point=(0.5, 0.5),
    anchored_position=(WIDTH // 2, HEIGHT // 2)
)

# Weather display - two lines of text
weather_group = displayio.Group()

weather_city_label = label.Label(
    font=terminalio.FONT,
    text="",
    color=0xFFFFFF,
    scale=1,
    anchor_point=(0.5, 0.0),  # Top center
    anchored_position=(WIDTH // 2, 10)
)
weather_group.append(weather_city_label)

weather_temp_label = label.Label(
    font=terminalio.FONT,
    text="",
    color=0xFFFFFF,
    scale=1,
    anchor_point=(0.5, 0.0),  # Below city
    anchored_position=(WIDTH // 2, 35)
)
weather_group.append(weather_temp_label)

# Start with only main label in the display group
splash.append(main_label)

# ===== Display mode tracking =====

# Display modes
class DisplayMode:
    TIME = "time"
    STATUS = "status"
    MIC = "mic"
    WEATHER = "weather"

# Current display mode
_current_mode = DisplayMode.TIME

# Display rotation
_next_rotation = 0
_current_rotation_index = 0
_rotation_items = [DisplayMode.TIME, DisplayMode.WEATHER]


def _clear_display():
    """Remove all labels from the display"""
    if main_label in splash:
        splash.remove(main_label)
    if status_label in splash:
        splash.remove(status_label)
    if weather_group in splash:
        splash.remove(weather_group)


def display_mic_state(is_on: bool):
    """
    Shows 'MIC ON' or 'MIC OFF' in large text.
    """
    global _current_mode
    
    _clear_display()
    splash.append(main_label)
    
    if is_on:
        main_label.text = "MIC ON"
    else:
        main_label.text = "MIC OFF"
    
    _current_mode = DisplayMode.MIC


def display_clock(time_str: str):
    """
    Displays the passed-in time string (e.g. '12:01:05 AM').
    """
    global _current_mode
    
    if _current_mode != DisplayMode.TIME:
        _clear_display()
        splash.append(main_label)
        _current_mode = DisplayMode.TIME
        
    main_label.text = time_str


def display_status(message: str):
    """
    Display a status message in smaller text.
    Used for system status updates like WiFi connection, NTP sync, etc.
    """
    global _current_mode
    
    _clear_display()
    splash.append(status_label)
    
    status_label.text = message
    _current_mode = DisplayMode.STATUS


def display_weather(city, temp_condition):
    """
    Display weather information with city on top line
    and temperature + condition on bottom line.
    
    Args:
        city: City name string
        temp_condition: Temperature and condition string
    """
    global _current_mode
    
    _clear_display()
    splash.append(weather_group)
    
    weather_city_label.text = city
    weather_temp_label.text = temp_condition
    
    _current_mode = DisplayMode.WEATHER


def get_current_mode():
    """Returns the current display mode"""
    return _current_mode


def handle_display_rotation():
    """
    Check if it's time to rotate the display and do so if needed.
    Call this regularly from the main loop.
    
    Returns:
        bool: True if display was rotated, False otherwise
    """
    global _next_rotation, _current_rotation_index
    
    # Check if rotation is enabled
    if not config.get_value("DISPLAY_ROTATION_ENABLED", True):
        return False
    
    # Check if it's time to rotate
    now = time.monotonic()
    if now < _next_rotation:
        return False
    
    # Get the rotation interval from config
    interval = config.get_value("DISPLAY_ROTATION_INTERVAL", 10)
    _next_rotation = now + interval
    
    # If we're showing a temporary display (status or mic), don't rotate
    if _current_mode in [DisplayMode.STATUS, DisplayMode.MIC]:
        return False
    
    # Build the rotation item list (always includes TIME, conditionally includes others)
    _rotation_items = [DisplayMode.TIME]
    
    # Add weather if enabled and we have an API key
    if (config.get_value("WEATHER_ENABLED", True) and 
        config.get_value("WEATHER_API_KEY", "")):
        _rotation_items.append(DisplayMode.WEATHER)
    
    # If there's only one item, no need to rotate
    if len(_rotation_items) <= 1:
        return False
    
    # Move to the next item in rotation
    _current_rotation_index = (_current_rotation_index + 1) % len(_rotation_items)
    next_mode = _rotation_items[_current_rotation_index]
    
    # Handle the rotation based on next mode
    if next_mode == DisplayMode.WEATHER:
        try:
            import weather_module
            city_line, temp_line = weather_module.format_weather_for_display()
            if city_line and temp_line:
                display_weather(city_line, temp_line)
                return True
        except (ImportError, Exception) as e:
            print(f"Weather display error: {e}")
            # Fall back to time if we can't display weather
            display_clock(time_module.format_local_time())
    elif next_mode == DisplayMode.TIME:
        import time_module
        display_clock(time_module.format_local_time())
        return True
    
    return False
