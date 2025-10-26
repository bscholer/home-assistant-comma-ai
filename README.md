# comma.ai Home Assistant Integration

This custom integration allows you to monitor your comma.ai devices (EON, comma three, etc.) in Home Assistant.

## Features

- **Device Tracking**: Track the GPS location of your comma.ai device on the map
- **Sensor Entities**: Monitor various device statistics:
  - Device type
  - openpilot version
  - Prime status
  - Last ping time
  - Last GPS update time
  - GPS speed
  - GPS bearing
  - GPS accuracy

## Installation

1. Copy the `comma` directory to your `custom_components` directory
2. Restart Home Assistant
3. Go to Settings → Devices & Services → Add Integration
4. Search for "comma.ai"
5. Enter your JWT token (get it from [jwt.comma.ai](https://jwt.comma.ai))

## Configuration

The integration is configured through the UI. You only need to provide your JWT token from comma.ai.

### Initial Setup
1. Get your JWT token from [jwt.comma.ai](https://jwt.comma.ai)
2. Add the integration in Settings → Devices & Services
3. Enter your JWT token

### Updating Your JWT Token

JWT tokens expire after 90 days. To update your token:

1. Go to Settings → Devices & Services
2. Find the comma.ai integration
3. Click the ⋮ menu → "Reconfigure"
4. Enter your new JWT token from [jwt.comma.ai](https://jwt.comma.ai)
5. Click Submit

The integration will reload with the new token while preserving all your data and configuration.

## Usage

Once configured, the integration will:
- Create a device for each comma.ai device in your account
- Add sensor entities for various device statistics
- Add a device tracker entity for GPS location tracking
- Update data every 60 seconds

## Entities Created

For each comma.ai device, the following entities will be created:

### Sensors
- `sensor.<device_name>_device_type` - The type of device (e.g., "neo", "three")
- `sensor.<device_name>_openpilot_version` - The installed openpilot version
- `sensor.<device_name>_prime_status` - Whether the device has comma prime
- `sensor.<device_name>_last_ping` - Last time the device communicated with comma servers
- `sensor.<device_name>_last_gps_update` - Last GPS update timestamp
- `sensor.<device_name>_gps_speed` - Current GPS speed
- `sensor.<device_name>_gps_bearing` - Current GPS bearing
- `sensor.<device_name>_gps_accuracy` - GPS accuracy in meters

### Device Tracker
- `device_tracker.<device_name>_location` - GPS location for map tracking

## API Information

This integration uses the comma.ai public API documented at [api.comma.ai](https://api.comma.ai/).

## Troubleshooting

If you encounter issues:
1. Check that your JWT token is valid at [jwt.comma.ai](https://jwt.comma.ai)
2. Check the Home Assistant logs for error messages
3. Ensure your device is online and connected to comma servers

## Support

For issues with this integration, please check the Home Assistant logs for detailed error messages.


