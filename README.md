# comma.ai Home Assistant Integration

This custom integration allows you to monitor your comma.ai devices (EON, comma three, etc.) in Home Assistant.

<img width="339" height="160" alt="image" src="https://github.com/user-attachments/assets/5504fcac-6d2d-402d-98b0-fa7031f440bf" />

## Features

- **Device Tracking**: Track the GPS location of your comma.ai device on the map
- **Sensor Entities**: Monitor various device statistics and usage data (see below for full list)
- **Live Cameras**: View the road (outside) and driver (inside) cameras live, the same stream as comma connect's camera button

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
4. If you only want devices owned by you to show up, enable "Ignore devices you don't own".
   - This is primarily helpful for people who have had users share their devices with them for debugging purposes. These shared devices will be filtered out.

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
- `sensor.<device_name>_dongle_id` - The Dongle ID of the device
- `sensor.<device_name>_device_type` - The type of device (e.g., "neo", "three")
- `sensor.<device_name>_openpilot_version` - The installed openpilot version
- `sensor.<device_name>_is_owner` - Whether you are the owner of the device ("Yes" or "No")
- `sensor.<device_name>_is_paired` - Whether the device is paired ("Yes" or "No")
- `sensor.<device_name>_prime_status` - Whether the device has comma prime ("Yes" or "No")

#### Device Status
- `sensor.<device_name>_last_ping` - Last time the device communicated with comma servers (timestamp)
- `sensor.<device_name>_last_location_time` - Last location update timestamp

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

### Cameras
- `camera.<device_name>_road_camera` - Live view from the wide road camera (outside the car)
- `camera.<device_name>_driver_camera` - Live view from the driver camera (inside the car)

The cameras use the same WebRTC live stream as the camera button in [comma connect](https://connect.comma.ai): Home Assistant sends a `startStream` request to the device through comma's athena relay, then receives the video peer-to-peer (or through comma's TURN relay). Frames are served to Home Assistant as snapshots and as an MJPEG stream, so they work in picture cards, the more-info dialog and `camera.snapshot`.

Things to know:
- **The car must be off.** openpilot only live streams while offroad, and the device must be online (awake and connected to Wi-Fi or cellular).
- **Streams start on demand.** A stream starts when an image is requested (e.g. a dashboard card is visible) and stops 30 seconds after the last request. A card that stays open keeps the stream, and the device's cameras, running. The first image can take 10-20 seconds while the device starts its cameras.
- **One viewer at a time.** The device accepts a single stream client. Home Assistant will take over an open comma connect live view; if you then open the live view in comma connect, Home Assistant backs off for 2 minutes.
- **One camera at a time.** The device sends a single video track. Viewing both cameras at once alternates between them every 10 seconds; the other camera shows its last frame meanwhile.
- The camera's `last_error` attribute shows why the last stream attempt failed (e.g. device offline, or "turn car ignition off to use livestreaming").
- Streaming needs [aiortc](https://github.com/aiortc/aiortc), which Home Assistant installs automatically. Its latest release does not support the PyAV version that Home Assistant ships, so the integration installs it from a pinned aiortc commit; this requires Home Assistant 2025.12 or newer.

## API Information

This integration uses the comma.ai public API documented at [api.comma.ai](https://api.comma.ai/). Live streaming uses the (undocumented) athena `startStream` method that comma connect uses, so a comma or openpilot update could break it.

## Troubleshooting

If you encounter issues:
1. Check that your JWT token is valid at [jwt.comma.ai](https://jwt.comma.ai)
2. Check the Home Assistant logs for error messages
3. Ensure your device is online and connected to comma servers
4. For cameras: make sure the car is off and the live view works in comma connect

## Support

For issues with this integration, please check the Home Assistant logs for detailed error messages.

Feel free to open an Issue or Pull Request!


