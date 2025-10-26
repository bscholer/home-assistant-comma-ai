# Changelog

All notable changes to the comma.ai Home Assistant integration will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-10-26

### Added
- Initial release
- Device tracker for GPS location tracking
- Device information sensors (type, openpilot version, Prime status)
- GPS data sensors (speed, bearing, accuracy)
- Last ping and GPS update timestamp sensors
- All-time driving statistics (distance, time, routes)
- Weekly driving statistics (distance, time, routes)
- Config flow for easy setup via UI
- **JWT token reconfiguration** - Easy token renewal through UI when tokens expire (90 day expiry)
- JWT token authentication
- HACS compatibility
- Automatic unit conversion (km to miles, m/s to mph)
- Device grouping in Home Assistant UI
- 60-second update interval
- Graceful handling of offline devices
- Timezone-aware timestamp sensors
- Energy dashboard compatibility for distance tracking

### Technical
- Uses comma.ai public API v1 and v1.1
- Async implementation with proper coordinators
- Type hints throughout codebase
- Proper error handling
- Translation support (English)
- Home Assistant 2024.1.0+ compatibility
- Reconfigure flow for token updates

## [Unreleased]

### Planned
- Historical route visualization
- Navigation destination setting
- Saved locations management
- Binary sensors (is_driving, is_online)
- Services for advanced operations
- Multi-language translations
- Automatic token expiration warnings

