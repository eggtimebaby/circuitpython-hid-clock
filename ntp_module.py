# ntp_module.py

import time
import socketpool
import wifi_module
import adafruit_ntp
import config

# Cache for the NTP object
_ntp = None

# Last sync timestamp (monotonic time)
_last_sync_time = 0

# Default sync interval (how often to resync with NTP server)
_sync_interval_seconds = 24 * 60 * 60  # Once per day by default

# Flag to track if the RTC has been set at least once
_rtc_synced = False


def get_ntp_client():
    """
    Get or create an NTP client instance.
    Requires an active Wi-Fi connection.
    
    Returns the NTP client object or None if Wi-Fi isn't available.
    """
    global _ntp
    
    # If we already have an NTP client, reuse it
    if _ntp is not None:
        return _ntp
    
    # Check if we're connected to Wi-Fi
    if not wifi_module.is_connected():
        print("Wi-Fi not connected, can't create NTP client")
        return None
    
    try:
        # Get the socket pool that wifi_module already created
        pool = wifi_module.get_socket_pool()
        if pool is None:
            print("No socket pool available")
            return None
        
        # Create the NTP client
        ntp_servers = config.config.get("NTP_SERVERS", ["pool.ntp.org", "time.google.com"])
        print(f"Creating NTP client with servers: {ntp_servers}")
        _ntp = adafruit_ntp.NTP(pool, server=ntp_servers[0])
        
        # Set fallback servers if first one fails
        if len(ntp_servers) > 1:
            _ntp.server = ntp_servers
            
        return _ntp
    except Exception as e:
        print(f"Error creating NTP client: {e}")
        return None


def sync_time(force=False):
    """
    Synchronize the system time with an NTP server.
    
    Args:
        force: If True, sync even if the minimum interval hasn't elapsed
        
    Returns:
        bool: True if sync was successful, False otherwise
    """
    global _last_sync_time, _rtc_synced
    
    # Check if we need to sync based on interval
    now = time.monotonic()
    interval = config.config.get("NTP_SYNC_INTERVAL", _sync_interval_seconds)
    
    if not force and _rtc_synced and (now - _last_sync_time) < interval:
        # Too soon since last sync
        return True
    
    try:
        # Ensure Wi-Fi is connected
        if not wifi_module.is_connected():
            print("Wi-Fi not connected, attempting to connect")
            wifi_module.ensure_wifi_connected()
            if not wifi_module.is_connected():
                print("Failed to connect to Wi-Fi")
                return False
        
        # Get NTP client
        ntp = get_ntp_client()
        if ntp is None:
            print("Failed to get NTP client")
            return False
        
        # Update the last sync time
        _last_sync_time = now
        
        # Get the current UTC time from NTP
        try:
            # This is where the actual NTP query happens
            ntp_datetime = ntp.datetime
            print(f"NTP time received: {ntp_datetime}")
            
            # Update flag that we've successfully synced at least once
            _rtc_synced = True
            
            return True
        except Exception as e:
            print(f"Error getting time from NTP server: {e}")
            return False
            
    except Exception as e:
        print(f"Time sync failed: {e}")
        return False


def is_rtc_synced():
    """
    Returns whether the RTC has been synced at least once since boot.
    """
    return _rtc_synced


def get_current_datetime():
    """
    Returns the current datetime as a time.struct_time in the local timezone.
    
    This uses the NTP-synchronized time if available, with timezone
    adjustments from the config.
    """
    # Try to sync if needed
    if not _rtc_synced:
        sync_time()
    
    # Get current time
    utc_now = time.localtime()
    
    # Apply timezone offset
    from time_module import get_utc_offset_seconds
    offset_seconds = get_utc_offset_seconds()
    local_secs = time.mktime(utc_now) + offset_seconds
    
    return time.localtime(local_secs)
