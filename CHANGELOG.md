# Changelog

All notable changes to this project will be documented in this file.

## [0.6.0] - 2025-10-22

Major thanks to user HJ@discord for putting up with testing and dustball62 for confirming

### Added

- Support for v6 firmware XM models using a different login path (XW already was successful)
- Calculated cpuload on v6 if values available (to prevent reporting close to 100%)
- Fix frequency on v6 firmware (if value is cast as a string ending in MHz)
- Added tx/rx rates for v6 as capacity (throughput is available in v6 web interface, but probably through counters, so not yet available)
- Fixed ieeemode (v8) vs opmode (v6) mapped back to IeeeMode enum
- Derived antenna_gain (v8) from antenna (v6 string)
- Improved internal workings and firmware detection

## [0.5.6] - 2025-10-11

### Added

- Model name (devmodel) to SKU (product code) mapper for model_id and model_name matching in Home Assistant

## [0.5.5] - 2025-10-05

### Changed

- Change login from json_data to form_data for v6 login

## [0.5.4] - 2025-10-01

### Added

- Alternate/pre-decessing login url for v6

## [0.5.3] - 2025-09-26

### Changed

- Improved unauthorized and forbidden handling

## [0.5.1] - 2025-08-31

### Changed

- Created a base class based on AirOS8 for both v6 and v8 to consume increasing mypy options for consumption

## [0.5.0] - Not released

Initial support for firmware 6

### Added

- Add logging redacted data on interface [issue](https://github.com/home-assistant/core/issues/151348)
- W.r.t. reported NanoBeam 8.7.18; Mark mtu optional on interfaces
- W.r.t. reported NanoStation 6.3.16-22; Provide preliminary status reporting

## [0.4.4] - 2025-08-29

### Changed

- Made signal in Disconnected optional as reported on LiteBeam 8.7.15

## [0.4.3] - 2025-08-22

### Changed

- Made antenna_gain and nol_* optional as reported on  Prism and LiteBeam 8.7.8 support

## [0.4.2] - 2025-08-17

### Changed

- Aligned quality targets either improved or tagged

## [0.4.1] - 2025-08-17

### Changed

- Further refactoring of the code (HA compatibility)

## [0.4.0] - 2025-08-16

### Added

- Refactoring of the code (DRY-ing up)
- Documentation on available class functions
- Added the additional firmware update related functions

## [0.3.0] - 2025-08-15

### Added

- Implementation of `[AP|Sta]-[MODE]` to Enums.
- Added update check (non-forced) endpoint
- Added warnings fetch endpoint

## [0.2.11] - 2025-08-14

### Changed

- Addition of more fixtures (thanks @Zrzyck)

## [0.2.10] - 2025-08-13

### Changed

- Maintenance chores
- Added pylint and pytest (and applicable changes)

## [0.2.9] - 2025-08-12

### Changed

- Bug Fixes
  - More consistent error handling across login, status, stakick, and provmode; login now returns False when an auth token is missing. Improved discovery transport setup and resilience.
- Refactor
  - Tightened type hints and clarified method signatures for predictable return types and safer usage.
- Tests
  - Substantially expanded coverage, especially for discovery edge cases and error paths.
- Chores
  - Enabled type checking in CI and gated coverage on it; added pre-commit hook and supporting environment script; updated test dependencies.

## [0.2.8] - 2025-08-12

### Changed

- Improved exception handling
- GPS data optional (reported on NanoStation via HA Core Issue 150491)

## [0.2.7] - 2025-08-08

### Added

- Added support for 8.7.11 NanoStation not having 'age' in the 'remote'(s)
- Added debugging script for pinpointing issues in the dataclass

## [0.2.6] - 2025-08-06

### Added

- Added redaction of data in exceptions when requesting `status()`
- Additional settings in dataclass (HA Core Issue 150118)
- Added 'likely' mocked fixture for above issue
- Added additional devices (see [Contributing](CONTRIBUTE.md) for more information)

### Changed

- Changed name and kwargs for discovery function

## [0.2.5] - 2025-08-05

### Added

- Added booleans determining station/accesspoint and PTP/PTMP in derived subclass

## [0.2.4] - 2025-08-03

### Added

- Added support handling a LiteBeam 5AC, including new wireless and IEEE mode options and allowing for unset height.

## [0.2.3] - 2025-08-02

### Changed

- Fixed callback function to async.
- Added changelog.

## [0.2.2] - 2025-08-02

### Changed

- Added a method to control provisioning mode for AirOS devices.
- Introduced a high-level asynchronous device discovery function for AirOS devices.
- Standardized class, exception, and log naming from "Airos" to "AirOS" across the codebase.
- Renamed enum members in WirelessMode for improved clarity.
- Updated tests and fixtures to use new naming conventions and to cover new discovery functionality.

## [0.2.1] - 2025-08-02

### Added

- Added a new field to device status data showing the MAC address and interface name of the primary enabled interface.

### Changed

- Updated wireless fixture data to reflect the correct access point MAC address.

## [0.2.0] - 2025-07-28

### Added

- Added UDP-based discovery for Ubiquiti airOS devices, enabling automatic detection and information retrieval from devices on the network.
- Introduced detailed error handling and new exception types for discovery-related issues.
- Improved code consistency by standardizing logger variable naming.
- Added a script to generate mock discovery packet fixtures for testing.
- Introduced comprehensive tests for the new device discovery functionality.

## [0.1.8] - 2025-07-28

### Added

- Improved device connection status reporting with clearer distinction between connected and disconnected devices.
- Enhanced status information for UNMS connectivity.
- Clarified descriptions for connected and disconnected device states.

## [0.1.7] - 2025-07-27

### Changed

- Improved login error handling by providing a clear error message when authentication is denied.

## [0.1.6] - 2025-07-26

### Changed

- Renamed the AirOS data class to clarify its association with AirOS v8 devices.
- Updated documentation to specify support for AirOS v8 devices.
- Adjusted import statements to reflect the class renaming.

## [0.1.5] - 2025-07-23

### Changed

- Improved handling of unknown or invalid enum values in device data by logging and removing them during data processing, reducing the chance of errors.
- Streamlined warning logging for device status, ensuring warnings are logged immediately rather than being cached.
- Simplified internal data handling and validation logic for device configuration fields.

## [0.1.4] - 2025-07-22

### Changed

- Improved warning handling to ensure each unique warning is only logged once per session.
- Added support for a new wireless mode labeled "AUTO".
- Enhanced warning messages to prompt users to report unknown remote wireless modes.

## [0.1.3] - 2025-07-22

### Changed

- Updated device status retrieval to always return structured data instead of raw JSON.

### Removed

- Dropped JSON output
- Removed a redundant test related to JSON status output.

## [0.1.2] - 2025-07-22

### Added

- Introduced a comprehensive and strongly typed data model for AirOS device data, enabling structured parsing and validation.
- The device status method now supports returning either a structured object or raw JSON, with improved warning handling for unknown values.
- Updated the README to include an example that prints the wireless mode from the device status.
- Added new test to verify device status retrieval returns structured data objects alongside existing JSON-based tests.

### Changed

- Updated dependencies to include mashumaro and removed asyncio.
- Bumped project version to 0.1.2.
- Changed output/returns from JSON to mashumaro (tnx @joostlek)

## [0.1.1] - 2025-07-21

### Added

- Error/exception handling and raising

## [0.1.0] - 2025-07-20

### Changed

- Improve station reconnect

## [0.0.9] - 2025-07-19

### Added

- Add tests
- Add station reconnect (`stakick`)

## [0.0.8] - 2025-07-16

### Changed

- Reworked exceptions

## [0.0.7] - 2025-07-16

### Changed

- Adjust function returns

## [0.0.6] - 2025-07-16

### Added

- Revert setting verify_ssl, leaving it up to the ingestor to set session

## [0.0.5] - 2025-07-15

### Add

- Add basic testing
- Add renovate for chores

## [0.0.4] - 2025-07-13

### Added

- Improve session handling and ssl, bump version
- Add `pre-commit`, prep `uv`
- Add more actions and pypi publishing
- Switch pypi publishing to Trusted Publishing
- Ensure environment and permissions improving publishing
- Actions and pypi

## [0.0.1] - 2025-07-13

### Added

- Initial commits
