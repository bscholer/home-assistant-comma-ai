# comma.ai Home Assistant Integration

This custom integration allows you to monitor your comma.ai devices (EON, comma three, etc.) in Home Assistant.

## Features

- **Device Tracking**: Track the GPS location of your comma.ai device on the map
- **Sensor Entities**: Monitor various device statistics and usage data (see below for full list)

## Installation

1. Open HACS store
    - If you don't have HACS installed, follow [these instructions](https://www.hacs.xyz/docs/use/)
2. In the top right, click the three dots, and click "Custom Repositories"
3. Add `https://github.com/bscholer/home-assistant-comma-ai`, then close the modal
4. Search for `comma.ai` in the HACS store. Open `comma.ai`, and click "Download"
5. Restart Home Assistant
6. Go to Settings → Devices & Services → Add Integration
7. Search for "comma.ai"
8. Enter your JWT token (get it from [jwt.comma.ai](https://jwt.comma.ai))

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

#### Device Information
- `sensor.<device_name>_device_type` - The type of device (e.g., "neo", "three")
- `sensor.<device_name>_openpilot_version` - The installed openpilot version
- `sensor.<device_name>_prime_status` - Whether the device has comma prime ("Yes" or "No")

#### Device Status
- `sensor.<device_name>_last_ping` - Last time the device communicated with comma servers (timestamp)
- `sensor.<device_name>_last_gps_update` - Last GPS update timestamp

#### GPS Data
- `sensor.<device_name>_gps_speed` - Current GPS speed (m/s, auto-converts to mph/kph)
- `sensor.<device_name>_gps_bearing` - Current GPS bearing (degrees)
- `sensor.<device_name>_gps_accuracy` - GPS accuracy in meters

#### All-Time Statistics
- `sensor.<device_name>_total_distance` - Total distance driven with openpilot (km, auto-converts to miles)
- `sensor.<device_name>_total_minutes` - Total minutes driven with openpilot
- `sensor.<device_name>_total_routes` - Total number of routes driven with openpilot

#### Weekly Statistics
- `sensor.<device_name>_week_distance` - Distance driven this week (km, auto-converts to miles)
- `sensor.<device_name>_week_minutes` - Minutes driven this week
- `sensor.<device_name>_week_routes` - Number of routes driven this week

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


