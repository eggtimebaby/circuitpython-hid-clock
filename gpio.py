# gpio.py

import usb_hid
from adafruit_hid.consumer_control import ConsumerControl
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode

import config

# Create HID objects
cc = ConsumerControl(usb_hid.devices)
kbd = Keyboard(usb_hid.devices)

# Build a keycode map for your mic shortcut
KEY_MAP = {
    "LEFT_CONTROL": Keycode.LEFT_CONTROL,
    "LEFT_SHIFT": Keycode.LEFT_SHIFT,
    "WINDOWS": Keycode.WINDOWS,
    "M": Keycode.M,
    "A": Keycode.A,
    # Add others if needed...
}

def parse_shortcut(shortcut_list):
    """
    Convert list of string key names into actual Keycode objects.
    """
    return [KEY_MAP[item] for item in shortcut_list if item in KEY_MAP]

# Convert the user’s config string array (e.g. ["LEFT_CONTROL","LEFT_SHIFT","M"])
# into actual Keycodes.
MIC_SHORTCUT_CODES = parse_shortcut(config.config["MIC_SHORTCUT"])


def toggle_mic_hotkey():
    """
    Presses & releases the configured mic shortcut (e.g. Ctrl+Shift+M).
    """
    kbd.press(*MIC_SHORTCUT_CODES)
    kbd.release_all()
