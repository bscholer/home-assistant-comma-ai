# Changelog

All notable changes to the comma.ai Home Assistant integration will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Historical route visualization
- Navigation destination setting
- Saved locations management
- Binary sensors (is_driving, is_online)
- Services for advanced operations
- Multi-language translations
- Automatic token expiration warnings

## [1.1.2] - 2026-11-19

### Added
- The car battery sensor exposes the raw panda state as attributes, and the athena `pandaStates` message is logged at debug level, to help diagnose odd voltage readings

### Fixed
- The first poll after Home Assistant started skipped the athena sensors (car battery, car running) on hosts that had booted less than 5 minutes earlier

## [1.1.1] - 2026-11-19

### Added
- Car battery voltage sensor and car running binary sensor, read live from the device via athena (polled every 5 minutes, since it uses the device's own connection). Thanks @georgegebbett (#7)
- Reauth flow: an expired JWT token now prompts to re-authenticate instead of failing setup. Thanks @georgegebbett (#7)

### Fixed
- Accounts without a username (for example Google sign-ins) were titled `comma.ai (None)`; the title now falls back to the email, then the user ID. Thanks @georgegebbett (#7)

### Changed
- Total drive time now displays in days and weekly drive time in hours by default, instead of minutes (for example 51.2 d instead of 73,740 min). Existing entities keep their current display unit; change it in the entity settings

## [1.1.0] - 2026-11-19

### Added
- Software build sensors (branch, commit, remote and vehicle platform), derived from the latest route the device uploaded, so they update after the next drive. The commit sensor carries the full SHA, commit date and dirty flag as attributes. Thanks @Nimijneb (#10)

### Fixed
- Distance sensors were 1.6x too low: comma's stats API reports miles, not kilometers. They now follow the Home Assistant unit system instead of always showing miles. Existing installs keep their current display unit; change it in the entity settings if you want km. Long-term statistics recorded before this fix stay 1.6x too low. Thanks @ds-sebastian (#8, fixes #4)
- hassfest translation errors: the JWT URL moved into a description placeholder (#11)

### Changed
- Removed the deprecated `battery_level` override from the device tracker (unsupported from Home Assistant 2027.7). Thanks @ds-sebastian (#6, fixes #5)

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
