
# HIKE IT BLE ESPHome Component

Full-featured BLE integration for HIKE IT throttle controllers.

## Features

- ✅ Auto-connect on boot with automatic reconnection
- ✅ Speed model control (10 modes: Economy, Normal, Cruise, Sport, ke IT, Auto, Launch, Anti-Slip, Valet, SL)
- ✅ Step adjustment for each speed mode
- ✅ Lock/Unlock with PIN
- ✅ Screen on/off toggle button
- ✅ Auto mode toggle button
- ✅ Status sensor with connection state
- ✅ Full protocol implementation with message parsing
- ✅ Automation triggers (on_connected, on_disconnected, on_verified, _message)

## Installation

### 2. Get Your Device MAC Address
Use the Python script first to scan for your device MAC address:
```bash
python test\hikeit_ble.py
# Choose option 2 to scan for HIKE IT devices
# Note down the MAC address
```

### 3. Configure ESPHome
Use the example YAML below, replacing the MAC address with yours.


## Home Assistant Integration

Once flashed, the device will appear in Home Assistant with the llowing entities:

- **Select: Speed Model** - Choose from 10 speed modes
- **Number: Step Adjustment** - Fine-tune step value (0-15)
- **Switch: Device Locked** - Lock/unlock with PIN (4 digits)
- **Button: Screen** - Trigger screen on / off
- **Button: Auto Mode** - Toggle automatic mode
- **Text Sensor: Device Status** - Shows connection state

## Usage Examples

### Change Speed Mode
```yaml
automation:
  - alias: "Set Sport Mode"
    trigger:
      - platform: state
        entity_id: binary_sensor.go_fast
        to: "on"
    action:
      - service: select.select_option
        target:
          entity_id: select.speed_model
        data:
          option: "Sport"
```


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

## Advanced Configuration

### Custom Automations with Triggers

```yaml
hikeit_ble:
  id: my_hikeit
  mac_address: "AA:BB:CC:DD:EE:FF"
  pin: "123"
  
  on_connected:
    - logger.log: "Device connected!"
    - homeassistant.event:
        event: esphome.hikeit_connected
  
  on_disconnected:
    - logger.log: "Device disconnected!"
    - homeassistant.event:
        event: esphome.hikeit_disconnected
  
  on_verified:
    - logger.log: "Device verified!"
    - switch.turn_on: status_led
  
  on_message:
    - lambda: |-
        ESP_LOGD("hikeit", "Message: %s", message.c_str());
```

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

