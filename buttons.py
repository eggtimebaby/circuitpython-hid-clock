# buttons.py

import time
import board
import digitalio
import config

# --- Button configuration ---
# Button debounce time in seconds
DEBOUNCE_TIME = 0.02
# Time threshold for long press detection in seconds
LONG_PRESS_TIME = 0.8
# Time window for double-click detection in seconds
DOUBLE_CLICK_TIME = 0.4

# --- Button states ---
class ButtonState:
    IDLE = 0       # Button is not pressed
    PRESSED = 1    # Button is currently pressed
    RELEASED = 2   # Button was just released
    DEBOUNCING = 3 # Button is changing state, wait for debounce

# --- Button class ---
class Button:
    def __init__(self, pin, pull=digitalio.Pull.UP, active_low=True):
        self.pin = digitalio.DigitalInOut(pin)
        self.pin.direction = digitalio.Direction.INPUT
        self.pin.pull = pull
        self.active_low = active_low
        
        # State management
        self.state = ButtonState.IDLE
        self.last_state_change = time.monotonic()
        self.press_start_time = 0
        self.last_release_time = 0
        self.previous_press_count = 0  # For double-click detection
        
    def is_pressed(self):
        """Returns True if button is currently physically pressed."""
        return (not self.pin.value) if self.active_low else self.pin.value
        
    def update(self):
        """
        Update button state machine.
        Call this frequently from your main loop.
        
        Returns a tuple of events:
        (pressed, released, long_press, double_click)
        """
        now = time.monotonic()
        pressed = False
        released = False
        long_press = False
        double_click = False
        
        # Get current physical state
        is_pressed_now = self.is_pressed()
        
        # State machine
        if self.state == ButtonState.IDLE:
            if is_pressed_now:
                # Button was just pressed
                self.state = ButtonState.DEBOUNCING
                self.last_state_change = now
            
        elif self.state == ButtonState.DEBOUNCING:
            if now - self.last_state_change >= DEBOUNCE_TIME:
                # Debounce period over, check if still pressed
                if is_pressed_now:
                    # Yes, now we're in pressed state
                    self.state = ButtonState.PRESSED
                    self.press_start_time = now
                    pressed = True
                else:
                    # No, must have been noise, go back to idle
                    self.state = ButtonState.IDLE
                
        elif self.state == ButtonState.PRESSED:
            if not is_pressed_now:
                # Button was released
                self.state = ButtonState.RELEASED
                self.last_state_change = now
                
                # Calculate press duration to detect long press
                press_duration = now - self.press_start_time
                if press_duration >= LONG_PRESS_TIME:
                    long_press = True
                
                # Check if this is a double click
                if now - self.last_release_time < DOUBLE_CLICK_TIME:
                    double_click = True
                    self.previous_press_count = 0  # Reset after detecting double click
                else:
                    self.previous_press_count = 1  # Single click
                
                released = True
                
        elif self.state == ButtonState.RELEASED:
            # Update state after release
            self.last_release_time = now
            self.state = ButtonState.IDLE
            
        return pressed, released, long_press, double_click

# Initialize buttons
mic_button = Button(board.GP2)
skip_button = Button(board.GP22)
back_button = Button(board.GP21)

# Track button actions
action_table = {
    # Format: button: {event_type: action}
    mic_button: {
        "pressed": None,              # No action on press
        "released": "toggle_mic",     # Toggle mic on release (normal press)
        "long_press": None,           # No long press action yet
        "double_click": None          # No double click action yet
    },
    skip_button: {
        "pressed": None,
        "released": "skip",
        "long_press": "fast_forward", # Hold to fast forward (if supported)
        "double_click": None
    },
    back_button: {
        "pressed": None,
        "released": "back",
        "long_press": "rewind",       # Hold to rewind (if supported)
        "double_click": None
    }
}

def check_buttons(mic_on, toggle_mic_hotkey):
    """
    Checks all buttons using the state machine approach.
    Returns:
      (new_mic_on, action)
    
    Where 'action' can be:
      - None (nothing happened)
      - "skip", "back" (media controls)
      - "fast_forward", "rewind" (long press media controls)
    """
    action = None
    
    # Check each button
    for button, actions in action_table.items():
        pressed, released, long_press, double_click = button.update()
        
        # Determine action based on events
        button_action = None
        if long_press and actions["long_press"]:
            button_action = actions["long_press"]
        elif double_click and actions["double_click"]:
            button_action = actions["double_click"]
        elif released and actions["released"]:
            button_action = actions["released"]
        elif pressed and actions["pressed"]:
            button_action = actions["pressed"]
            
        # Handle special case for mic toggle
        if button_action == "toggle_mic":
            mic_on = not mic_on
            toggle_mic_hotkey()
            # No further action needed for mic toggle
        elif button_action:
            # For other actions, return the action name
            action = button_action
            
    return mic_on, action
