# time_module.py

import time
import config

# Track when we last tried to sync time
_last_sync_attempt = 0

def get_utc_offset_seconds():
    """
    Returns the UTC offset in seconds based on TIMEZONE and DST settings.
    """
    timezone = config.config["TIMEZONE"]
    dst = config.config["DST"]

    if timezone == "UK":
        base_offset = 0
        if dst:
            base_offset += 1  # BST = +1 hour
    elif timezone == "US_EAST":
        base_offset = -5  # EST = -5 hours
        if dst:
            base_offset += 1  # EDT = -4 hours
    else:
        base_offset = 0

    return base_offset * 3600  # Convert hours to seconds


def get_local_time():
    """
    Returns a local time struct_time, using NTP if available.
    
    If NTP is not available or sync fails, falls back to the internal clock.
    """
    global _last_sync_attempt
    
    # Check if we should attempt an NTP sync
    now = time.monotonic()
    retry_interval = config.config.get("NTP_SYNC_RETRY_INTERVAL", 300)
    
    # Periodically try to sync with NTP
    if now - _last_sync_attempt > retry_interval:
        _last_sync_attempt = now
        try:
            # Import only when needed to avoid import loops
            import ntp_module
            if ntp_module.sync_time():
                # Successfully synced, use NTP time
                return ntp_module.get_current_datetime()
        except (ImportError, Exception) as e:
            print(f"NTP sync attempt error: {e}")
            # Fall back to internal time
    
    # If we reach here, either NTP sync didn't happen or failed
    # Calculate local time using internal clock and config offset
    offset_seconds = get_utc_offset_seconds()
    utc_now = time.localtime()
    local_secs = time.mktime(utc_now) + offset_seconds
    return time.localtime(local_secs)


def format_local_time():
    """
    Formats the current local time in a 12-hour format with AM/PM.
    Uses NTP-synchronized time when available.
    """
    local_t = get_local_time()
    
    hour_24 = local_t.tm_hour
    minute = local_t.tm_min
    second = local_t.tm_sec

    am_pm = "AM" if hour_24 < 12 else "PM"
    hour_12 = hour_24 % 12
    if hour_12 == 0:
        hour_12 = 12

    return f"{hour_12}:{minute:02d}:{second:02d} {am_pm}"
