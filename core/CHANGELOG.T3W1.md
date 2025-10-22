# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [2.9.3] (21st October 2025)

### Added
- Support using both Tropic and Optiga to protect PIN.  [#5845]
- Added support for Bluetooth toggling in the Device menu.  [#5911]
- Support device unlocking during THP handshake.  [#5922]
- Allow exporting device serial number.  [#5928]

### Changed
- Moved app name from the connection button to the Host Info screen.  [#5870]

### Fixed
- Cache THP host info also during credential-based pairing.  [#5867]
- Fix incorrect chunkified address rendering.  [#5882]
- Exit pairing screen when already paired host connects.  [#5897]

[#5845]: https://github.com/trezor/trezor-firmware/pull/5845
[#5867]: https://github.com/trezor/trezor-firmware/pull/5867
[#5870]: https://github.com/trezor/trezor-firmware/pull/5870
[#5882]: https://github.com/trezor/trezor-firmware/pull/5882
[#5897]: https://github.com/trezor/trezor-firmware/pull/5897
[#5911]: https://github.com/trezor/trezor-firmware/pull/5911
[#5922]: https://github.com/trezor/trezor-firmware/pull/5922
[#5928]: https://github.com/trezor/trezor-firmware/pull/5928
