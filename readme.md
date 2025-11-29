
# HIKE IT BLE ESPHome Component

Full-featured BLE integration for HIKE IT throttle controllers, may also work for other branded throttle controllers.

## Features

- Auto-connect on boot with automatic reconnection
- Speed model control (9 modes: Off, Eco 4x4, Cruise, Sport, Hike IT, Auto, Launch, Anti-Slip, Valet)
- Step adjustment for each speed mode
- Lock/Unlock with PIN
- Screen on/off toggle button
- Status sensor with connection state
- Automation triggers (on_connected, on_disconnected, on_verified, on_message)

## Requirements

- ESPHome 2025.11.0 or later
- ESP32 with BLE support

## Installation

### 1. Get Your Device MAC Address
Use the Python script first to scan for your device MAC address:
```bash
python tests/hikeit_ble.py
# Choose option 2 to scan for HIKE IT devices
# Note down the MAC address
```

### 2. Configure ESPHome
Use the example YAML below, replacing the MAC address with yours.

Configure secrets for hikeit_mac_address and hikeit_pin

```yaml
esphome:
  name: hikeit
  friendly_name: Hikeit
  
esp32:
  board: lolin_s3
  framework:
    type: esp-idf

# Enable logging
logger:
  level: DEBUG
  logs:
    # Reduce BLE spam
    esp32_ble: INFO
    esp32_ble_tracker: INFO
    # Keep hikeit detailed
    hikeit_ble: DEBUG

# WiFi configuration
wifi:
  ssid: !secret wifi_ssid
  password: !secret wifi_password
  
# Captive portal for initial setup
captive_portal:

# Web server (optional, for debugging)
web_server:

# BLE Client setup
esp32_ble_tracker:
  scan_parameters:
    interval: 1100ms
    window: 1100ms
    active: true

ble_client:
  - mac_address: !secret hikeit_mac_address
    id: hikeit_ble_client
    auto_connect: true

external_components:
   - source: github://andrewbackway/esphome-hikeit_ble@main

# ====================================================================================
# HIKE IT BLE Component Configuration
# ====================================================================================

hikeit_ble:
  id: hikeit_hikeit
  ble_client_id: hikeit_ble_client
  mac_address: !secret hikeit_mac_address
  pin: !secret hikeit_pin
  
  # Automation triggers
  on_connected:
    - logger.log:
        format: "🔌 Hikeit connected!"
        level: INFO
  
  on_disconnected:
    - logger.log:
        format: "⚠️ Hikeit disconnected!"
        level: WARN
  
  on_verified:
    - logger.log:
        format: "✅ Hikeit verified and ready!"
        level: INFO
  
  on_message:
    - lambda: |-
        ESP_LOGV("hikeit", "Raw message: %s", message.c_str());

# ====================================================================================
# Platform-based Entity Configuration
# ====================================================================================

# Speed Model Select
select:
  - platform: hikeit_ble
    hikeit_ble_id: hikeit_hikeit
    name: "Model"
    id: hikeit_speed_model
    icon: "mdi:speedometer"
    on_value:
      - logger.log:
          format: "Model changed to: %s"
          args: [ 'x.c_str()' ]

# Step Adjustment Number
number:
  - platform: hikeit_ble
    hikeit_ble_id: hikeit_hikeit
    name: "Step Adjustment"
    id: hikeit_step
    icon: "mdi:tune-vertical"
    mode: slider
    on_value:
      - logger.log:
          format: "Step adjusted to: %.0f"
          args: [ 'x' ]

# Lock/Unlock Switch
switch:
  - platform: hikeit_ble
    hikeit_ble_id: hikeit_hikeit
    name: "Device Locked"
    id: hikeit_locked
    icon: "mdi:lock"
    on_turn_on:
      - logger.log: "🔒 Hike IT locked"
    on_turn_off:
      - logger.log: "🔓 Hike IT unlocked"
  
  # Optional: Connect switch to control BLE connection
  - platform: template
    id: hikeit_connect
    name: "HIKE IT Connect"
    icon: "mdi:bluetooth"
    optimistic: true
    restore_mode: RESTORE_DEFAULT_OFF

# Screen Command Button
button:
  - platform: hikeit_ble
    hikeit_ble_id: hikeit_hikeit
    name: "Screen Toggle"
    id: hikeit_screen
    icon: "mdi:monitor"
    on_press:
      - logger.log: "📺 Screen toggle command sent"

# Status Sensor
text_sensor:
  - platform: hikeit_ble
    hikeit_ble_id: hikeit_hikeit
    name: "Connection Status"
    id: hikeit_status
    icon: "mdi:connection"
```

## Platform Entities

All entities are now configured as platform sensors, which follows the ESPHome 2025.11+ convention:

### Select (Speed Model)
```yaml
select:
  - platform: hikeit_ble
    hikeit_ble_id: hikeit_hikeit
    name: "Model"
```

Available options: Off, Eco 4x4, Cruise, Sport, Hike IT, Auto, Launch, Anti-Slip, Valet

### Number (Step Adjustment)
```yaml
number:
  - platform: hikeit_ble
    hikeit_ble_id: hikeit_hikeit
    name: "Step Adjustment"
    mode: slider  # or box
```

Range: 0-15

### Switch (Lock/Unlock)
```yaml
switch:
  - platform: hikeit_ble
    hikeit_ble_id: hikeit_hikeit
    name: "Device Locked"
```

Controls device lock state using configured PIN.

### Button (Screen Toggle)
```yaml
button:
  - platform: hikeit_ble
    hikeit_ble_id: hikeit_hikeit
    name: "Screen Toggle"
    command_type: 0  # 0 = screen, 1 = auto transmission (optional)
```

### Text Sensor (Connection Status)
```yaml
text_sensor:
  - platform: hikeit_ble
    hikeit_ble_id: hikeit_hikeit
    name: "Connection Status"
```

Reports: Disconnected, Connecting..., Connected, Verifying..., Verified, Error, Offline


## Troubleshooting

### Connection Issues

1. **Device not connecting:**
   - Verify MAC address is correct
   - Check ESP32 logs: `esphome logs hikeit_bike.yaml`
   - Ensure device is in range (<10m)
   - Try power cycling both ESP32 and HIKE IT device

2. **Verification fails:**
   - Check logs for "Verification FAILED!"
   - Device might need button press for pairing
   - Try disconnecting from phone app first

3. **Reconnection loop:**
   - Device ID not captured - check logs
   - BLE interference - move away from WiFi router

### Command Issues

1. **Commands not working:**
   - Ensure device is verified (check status sensor)
   - Check logs for "No cached state" warnings
   - Wait for Type 02 message before sending commands

2. **Lock/Unlock fails:**
   - Verify PIN in YAML matches device PIN
   - Check logs for "Wrong PIN" status

## Protocol Details

Message format (19 bytes / 38 hex chars):

- Header: AA55 (2 bytes)
- Sequence: 00-FF rolling counter (1 byte)
- Type: Command type (1 byte)
- Content: Command data (10 bytes)
- Device ID: Unique device identifier (4 bytes)
- Checksum: Sum of bytes 2-17 & 0xFF (1 byte)

Command types:

- 0x01: Study mode
- 0x02: Status/Model (most common)
- 0x05: Lock device
- 0x06: Unlock device
- 0x08: Screen command
- 0x09: Verification (subtype 03=connect, 04=disconnect)

## License

MIT License - Free to use and modify

## Credits

Based on HIKE IT Android app protocol

