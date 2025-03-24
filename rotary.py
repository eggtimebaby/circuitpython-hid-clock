# rotary.py

import time
import board
import digitalio
from adafruit_hid.consumer_control_code import ConsumerControlCode

# Rotary pins: CLK, DT, Switch
clk = digitalio.DigitalInOut(board.GP16)
clk.direction = digitalio.Direction.INPUT
clk.pull = digitalio.Pull.UP

dt = digitalio.DigitalInOut(board.GP17)
dt.direction = digitalio.Direction.INPUT
dt.pull = digitalio.Pull.UP

encoder_sw = digitalio.DigitalInOut(board.GP18)
encoder_sw.direction = digitalio.Direction.INPUT
encoder_sw.pull = digitalio.Pull.UP

# Track the last known state of CLK
last_clk = clk.value


def check_rotary(consumer_control):
    """
    Checks the rotary encoder for rotation or button press events.
    If rotated clockwise, send VOLUME_INCREMENT.
    If rotated counter-clockwise, send VOLUME_DECREMENT.
    If switch pressed, send PLAY_PAUSE.
    """
    global last_clk

    current_clk = clk.value
    if current_clk != last_clk:
        # Determine rotation direction
        if dt.value != current_clk:
            # Clockwise
            consumer_control.send(ConsumerControlCode.VOLUME_INCREMENT)
        else:
            # Counter-clockwise
            consumer_control.send(ConsumerControlCode.VOLUME_DECREMENT)

        last_clk = current_clk

    # Encoder switch -> Play/Pause
    if not encoder_sw.value:  # active low
        consumer_control.send(ConsumerControlCode.PLAY_PAUSE)
        time.sleep(0.3)
