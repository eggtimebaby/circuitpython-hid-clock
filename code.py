# code.py

import time
import wifi_module
import time_module
import gpio
import rotary
import buttons
import oled
import config
from adafruit_hid.consumer_control_code import ConsumerControlCode

# Constants
SHOW_MIC_STATE_DURATION = config.get_value("SHOW_MIC_STATE_DURATION", 2.0)
SHOW_STATUS_DURATION = 3.0  # How long to show status messages (3 seconds)
WIFI_RETRY_INTERVAL = 300   # Attempt reconnection every 5 minutes if offline
CLOCK_UPDATE_INTERVAL = 0.5 # Update clock display twice per second when visible
WEATHER_FETCH_INTERVAL = 30 * 60  # Fetch weather every 30 minutes (or use config)
SETTINGS_INFO_ROTATE_INTERVAL = 5.0  # Rotate between settings info screens

# Variables for tracking state
mic_on = True
show_mic_state_until = 0
show_status_until = 0
status_message = ""
last_wifi_retry = 0
last_clock_update = 0
last_displayed_time = ""
last_weather_fetch = 0
weather_api_configured = False
settings_mode = False
settings_info_last_change = 0
settings_info_index = 0

# Settings mode info screens - Messages to display in settings mode
SETTINGS_INFO_SCREENS = [
    "SETTINGS MODE\nEdit settings.toml",
    "WiFi Settings:\nSSID & PASSWORD",
    "Weather API Key:\nWEATHER_API_KEY",
    "Optional Settings:\nWEATHER_CITY",
    "Optional Settings:\nWEATHER_UNITS",
    "Long-press Back & Skip\nto exit settings mode"
]

# Function to handle WiFi status messages
def wifi_status_callback(message):
    global show_status_until, status_message
    status_message = message
    show_status_until = time.monotonic() + SHOW_STATUS_DURATION
    oled.display_status(message)

# Register the callback with the wifi module
wifi_module.set_status_callback(wifi_status_callback)

# Function to display settings mode information
def display_settings_info():
    """Display information about the settings mode"""
    global settings_info_index, settings_info_last_change
    
    # Calculate if we need to switch to the next info screen
    now = time.monotonic()
    if now - settings_info_last_change > SETTINGS_INFO_ROTATE_INTERVAL:
        settings_info_last_change = now
        settings_info_index = (settings_info_index + 1) % len(SETTINGS_INFO_SCREENS)
        
    # Display the current settings info screen
    info_text = SETTINGS_INFO_SCREENS[settings_info_index]
    oled.display_status(info_text)

# ===== STARTUP SEQUENCE =====

# Check if we should start in settings mode (by checking config or button combo at boot)
try:
    # Check config first
    settings_mode = config.get_value("SETTINGS_MODE", False)
    
    # Also check if both skip and back buttons are held down during startup
    # This allows user to force settings mode even without config access
    if not settings_mode:
        # Quick check for button press without debouncing
        skip_pressed = not buttons.skip_button.is_pressed()
        back_pressed = not buttons.back_button.is_pressed()
        if skip_pressed and back_pressed:
            print("Button combo detected: entering settings mode")
            settings_mode = True
            # Save to config if possible
            config.set_value("SETTINGS_MODE", True)
except Exception as e:
    print(f"Error checking settings mode: {e}")

# Display startup message
print("Starting up...")
if settings_mode:
    oled.display_status("SETTINGS MODE")
    time.sleep(1)
else:
    oled.display_status("Starting...")

# 1) Connect to Wi-Fi at Startup (unless in settings mode)
wifi_connected = False
if not settings_mode:
    wifi_connected = wifi_module.ensure_wifi_connected()

    if not wifi_connected:
        if wifi_module.is_offline_mode():
            status_message = "Running in offline mode"
        else:
            status_message = "WiFi connection failed"
        
        show_status_until = time.monotonic() + SHOW_STATUS_DURATION
        oled.display_status(status_message)
        time.sleep(2)  # Give user time to read the message

# 2) Initialize NTP time sync if connected and configured
if wifi_connected and config.get_value("NTP_SYNC_ON_STARTUP", True):
    try:
        print("Attempting NTP time sync...")
        oled.display_status("Syncing time...")
        import ntp_module
        sync_success = ntp_module.sync_time(force=True)
        
        if sync_success:
            status_message = "Time synced!"
        else:
            status_message = "Time sync failed"
            
        show_status_until = time.monotonic() + SHOW_STATUS_DURATION
        print(status_message)
        oled.display_status(status_message)
    except Exception as e:
        print(f"NTP error: {e}")
        # Continue without NTP

# 3) Initialize Weather if connected and enabled
if wifi_connected and config.get_value("WEATHER_ENABLED", True):
    try:
        # Import weather module
        import weather_module
        
        # Check if API key is configured
        api_key = weather_module.get_weather_api_key()
        if api_key:
            weather_api_configured = True
            oled.display_status("Fetching weather...")
            
            # Try to get initial weather data
            weather_data = weather_module.fetch_weather()
            if weather_data:
                status_message = f"Weather: {weather_data['weather'][0]['main']}"
                city_name = weather_data['name']
                print(f"Weather for {city_name}: {status_message}")
            else:
                status_message = "Weather fetch failed"
                
            show_status_until = time.monotonic() + SHOW_STATUS_DURATION
            oled.display_status(status_message)
        else:
            print("Weather API key not configured")
            
    except (ImportError, Exception) as e:
        print(f"Weather init error: {e}")
        # Continue without weather

# 4) Display initial clock after startup sequence
time.sleep(1)  # Give a moment to read any status message
oled.display_clock(time_module.format_local_time())

# ===== MAIN LOOP =====
print("Startup complete, entering main loop")
while True:
    now_monotonic = time.monotonic()

    # Check for settings mode exit combo (long press both back and skip buttons)
    if settings_mode:
        # In settings mode, we need to check for the exit combo
        _, action = buttons.check_buttons(mic_on, lambda: None)  # Don't toggle mic in settings mode
        
        # Check if both long presses happened
        if action == "rewind" or action == "fast_forward":
            # Check if both buttons are pressed
            skip_pressed = not buttons.skip_button.is_pressed()
            back_pressed = not buttons.back_button.is_pressed()
            
            if skip_pressed and back_pressed:
                print("Exit settings mode combo detected")
                settings_mode = False
                config.set_value("SETTINGS_MODE", False)
                oled.display_status("Exiting settings mode")
                time.sleep(1)
                oled.display_clock(time_module.format_local_time())
    else:
        # Normal mode - handle regular controls
        
        # Rotary: volume & play/pause control
        rotary.check_rotary(gpio.cc)

        # Buttons: check if mic toggle, skip, or back was pressed
        old_mic_on = mic_on
        mic_on, action = buttons.check_buttons(mic_on, gpio.toggle_mic_hotkey)

        if mic_on != old_mic_on:
            oled.display_mic_state(mic_on)
            show_mic_state_until = now_monotonic + SHOW_MIC_STATE_DURATION
            # Clear any status message that might be showing
            show_status_until = 0

        # Handle button actions
        if action == "skip":
            gpio.cc.send(ConsumerControlCode.SCAN_NEXT_TRACK)
        elif action == "back":
            gpio.cc.send(ConsumerControlCode.SCAN_PREVIOUS_TRACK)
        elif action == "fast_forward":
            gpio.cc.send(ConsumerControlCode.FAST_FORWARD)
        elif action == "rewind":
            gpio.cc.send(ConsumerControlCode.REWIND)

        # Periodic WiFi retry if in offline mode
        if wifi_module.is_offline_mode() and now_monotonic - last_wifi_retry > WIFI_RETRY_INTERVAL:
            last_wifi_retry = now_monotonic
            print("Attempting to reconnect to WiFi from offline mode...")
            wifi_connected = wifi_module.retry_connection()
            
            # If reconnection successful and weather enabled, fetch new data
            if wifi_connected and weather_api_configured:
                try:
                    import weather_module
                    weather_module.fetch_weather()
                except Exception as e:
                    print(f"Weather update error: {e}")

        # Periodic weather update if connected and configured
        if (wifi_module.is_connected() and 
            weather_api_configured and 
            now_monotonic - last_weather_fetch > WEATHER_FETCH_INTERVAL):
            last_weather_fetch = now_monotonic
            try:
                import weather_module
                print("Updating weather data...")
                weather_module.fetch_weather()
            except Exception as e:
                print(f"Weather update error: {e}")

    # Display management based on current mode
    if settings_mode:
        # In settings mode, always show the settings info
        display_settings_info()
    else:
        # Normal display priority: 1) Mic state, 2) Status messages, 3) Rotation
        if now_monotonic < show_mic_state_until:
            # Continue showing mic state
            pass
        elif now_monotonic < show_status_until:
            # Continue showing status message
            pass
        else:
            # Handle display rotation or update time
            rotated = oled.handle_display_rotation()
            
            # If not rotated and in time mode, update the clock if needed
            if not rotated and oled.get_current_mode() == oled.DisplayMode.TIME:
                if now_monotonic - last_clock_update > CLOCK_UPDATE_INTERVAL:
                    last_clock_update = now_monotonic
                    current_time = time_module.format_local_time()
                    
                    # Only update display if time string has changed
                    if current_time != last_displayed_time:
                        last_displayed_time = current_time
                        oled.display_clock(current_time)

    # Small delay to regulate loop speed
    time.sleep(0.05)  # Even more responsive for button presses
