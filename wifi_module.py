# wifi_module.py

import time
import wifi
import socketpool
import ssl
import os
import supervisor

# Cached references
_pool = None
_ssl_context = None
_connected = False
_offline_mode = False
_last_connection_attempt = 0
_connection_attempts = 0

# Maximum number of connection attempts before going to offline mode
MAX_RETRY_ATTEMPTS = 5
# Base delay between retries in seconds (will increase with backoff)
BASE_RETRY_DELAY = 3
# Maximum delay between retries in seconds
MAX_RETRY_DELAY = 60
# Callbacks
_status_callback = None


def set_status_callback(callback_func):
    """
    Set a callback function to be called when status changes.
    The callback should accept a string message parameter.
    """
    global _status_callback
    _status_callback = callback_func


def _notify_status(message):
    """Internal function to notify status via callback if set"""
    if _status_callback:
        _status_callback(message)
    print(message)  # Always print to console as well


def ensure_wifi_connected(force_retry=False):
    """
    If the radio is disabled, enable it. If not connected, connect once
    using environment variables from settings.toml. Cache the socket pool
    and SSL context so we only do it once per session.

    Args:
        force_retry: If True, retry connection even if in offline mode
    
    Returns:
        bool: True if connected, False if in offline mode or connection failed
    """
    global _pool, _ssl_context, _connected, _offline_mode
    global _last_connection_attempt, _connection_attempts

    # If we're in offline mode and not forcing a retry, just return False
    if _offline_mode and not force_retry:
        return False

    # If radio is off, turn it on:
    if not wifi.radio.enabled:
        wifi.radio.enabled = True
        _connected = False  # We know we aren't connected now

    # If we have an IP address, assume we're still connected
    if _connected and wifi.radio.ipv4_address:
        return True  # Already good to go

    # Check if we should respect backoff timing
    now = time.monotonic()
    
    # Calculate backoff delay - exponential backoff with maximum
    if _connection_attempts > 0 and not force_retry:
        # Calculate delay: BASE_RETRY_DELAY * 2^(attempts-1) up to MAX_RETRY_DELAY
        backoff_delay = min(BASE_RETRY_DELAY * (2 ** (_connection_attempts - 1)), 
                            MAX_RETRY_DELAY)
        
        if now - _last_connection_attempt < backoff_delay:
            # Too soon to retry
            return False
    
    # Update our attempt tracking
    _last_connection_attempt = now
    _connection_attempts += 1
    
    # Get connection credentials
    ssid = os.getenv("CIRCUITPY_WIFI_SSID", "DefaultSSID")
    password = os.getenv("CIRCUITPY_WIFI_PASSWORD", "DefaultPass")
    _notify_status(f"Connecting to SSID: {ssid} (attempt {_connection_attempts})...")

    try:
        wifi.radio.connect(ssid, password)
        _notify_status("Connected to Wi-Fi!")
        _connected = True
        _offline_mode = False
        _connection_attempts = 0  # Reset attempt counter on success
        
        # Initialize pool and SSL context
        _pool = socketpool.SocketPool(wifi.radio)
        _ssl_context = ssl.create_default_context()
        
        return True
        
    except Exception as e:
        _notify_status(f"Wi-Fi connection failed: {e}")
        
        # Check if we've exceeded max attempts
        if _connection_attempts >= MAX_RETRY_ATTEMPTS:
            _notify_status("Maximum connection attempts reached. Switching to offline mode.")
            _offline_mode = True
            # We'll stay in offline mode until force_retry=True is passed
        
        return False


def retry_connection():
    """
    Force a retry of the WiFi connection even if in offline mode.
    """
    global _offline_mode
    _offline_mode = False  # Reset offline mode
    return ensure_wifi_connected(force_retry=True)


def disconnect():
    """
    Gracefully disconnect from Wi-Fi but leave the radio powered on.
    This means you can reconnect later without re-enabling the radio.
    """
    global _connected
    if wifi.radio.enabled and _connected:
        wifi.radio.disconnect()
    _connected = False


def disable_radio():
    """
    Powers down the Wi-Fi radio. You must re-enable before connecting again.
    Any existing connection is dropped.
    """
    global _connected
    if wifi.radio.enabled:
        wifi.radio.disconnect()  # If connected, ensure a clean disconnection
        wifi.radio.enabled = False
    _connected = False


def enable_radio():
    """
    Re-enable the Wi-Fi radio, but does NOT automatically connect.
    Use ensure_wifi_connected() if you also want to connect.
    """
    global _connected
    if not wifi.radio.enabled:
        wifi.radio.enabled = True
    # Now we are "enabled" but not necessarily connected
    # We'll remain _connected=False until we call connect again.


def get_socket_pool():
    """
    Use this whenever you need a socket pool. It will ensure
    the radio is on and connected first, if necessary.
    
    Returns:
        socketpool.SocketPool or None: The socket pool if connected, None otherwise
    """
    if ensure_wifi_connected():
        return _pool
    return None


def get_ssl_context():
    """
    Returns the cached SSL context. Ensures the radio is on
    and connected if necessary.
    
    Returns:
        ssl.SSLContext or None: The SSL context if connected, None otherwise
    """
    if ensure_wifi_connected():
        return _ssl_context
    return None


def is_connected():
    """
    Returns True if the radio is on and we have a known valid connection,
    otherwise False.
    """
    return _connected and wifi.radio.enabled and wifi.radio.ipv4_address


def is_offline_mode():
    """
    Returns True if we're in offline mode (gave up trying to connect).
    """
    return _offline_mode


def reset_connection_state():
    """
    Reset connection state and attempt counts.
    Useful after configuration changes.
    """
    global _connected, _offline_mode, _connection_attempts
    _connected = False
    _offline_mode = False
    _connection_attempts = 0
