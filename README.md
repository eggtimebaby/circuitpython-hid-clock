# CircuitPython HID Clock

A CircuitPython-based device that provides time, weather, and HID control functions.

## Features

- Real-time clock synchronized via NTP
- Weather display using OpenWeatherMap API
- HID controls for computer functions
- OLED display showing time and weather information

## Hardware Requirements

- CircuitPython-compatible board with WiFi (e.g., ESP32-S2, ESP32-S3)
- OLED display (SSD1306 compatible)
- Buttons and rotary encoders as needed for controls

## Setup Instructions

1. Clone this repository to your computer
2. Copy the contents to your CircuitPython device
3. Create your configuration files:
   - Copy `settings.toml.example` to `settings.toml` and update with your credentials
   - Copy `settings.json.example` to `settings.json` and update with your preferences
4. Restart your device

## Configuration

### WiFi Setup

Edit `settings.toml` and `settings.json` to include your WiFi credentials:

```toml
# In settings.toml
CIRCUITPY_WIFI_SSID = "your_wifi_ssid_here"
CIRCUITPY_WIFI_PASSWORD = "your_wifi_password_here"
```

```json
// In settings.json
{
  "WIFI_SSID": "your_wifi_ssid_here",
  "WIFI_PASSWORD": "your_wifi_password_here"
}
```

### Weather API

This project uses the OpenWeatherMap API. Get your free API key by signing up at [OpenWeatherMap](https://openweathermap.org/api) and add it to your configuration files.

## License

MIT License
