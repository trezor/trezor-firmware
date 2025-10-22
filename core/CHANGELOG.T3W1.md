# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [2.9.3] (21st October 2025)

### Added
- Add dependency check between the PIN and the wipe code.  [#4446]
- Generation of SLIP-21 node for a new way of storing labels (using Evolu).  [#5220]
- Use Tropic in AuthenticateDevice.  [#5760]
- Support using both Tropic and Optiga to protect PIN.  [#5845]
- Added support for Bluetooth toggling in the Device menu.  [#5911]
- Support device unlocking during THP handshake.  [#5922]
- Allow exporting device serial number.  [#5928]
- Show warning on Ripple destination tag missing.  [#5931]

### Changed
- Moved app name from the connection button to the Host Info screen.  [#5870]
- Deprecate ETH Holesky testnet and use Hoodi testnet instead.  [#5942]

### Fixed
- Don't allocate tracebacks in optimized builds.  [#5526]
- Allow backup check only when the backup exists.  [#5763]
- Cache THP host info also during credential-based pairing.  [#5867]
- Fix incorrect chunkified address rendering.  [#5882]
- Exit pairing screen when already paired host connects.  [#5897]
- Erase BLE bonds too after entering wipe code.  [#5939]
- Fix false "NO USB CONNECTION" warning on the home screen.  [#5980]
- Fix homescreen LED blinking.  [#5990]
- Improve speed of translations upload over bluetooth.  [#5995]
- Adjust random part of BLE device name during pairing.  [#6019]
- Synchronize LED and background in tutorial.  [#6022]

[#4446]: https://github.com/trezor/trezor-firmware/pull/4446
[#5220]: https://github.com/trezor/trezor-firmware/pull/5220
[#5526]: https://github.com/trezor/trezor-firmware/pull/5526
[#5760]: https://github.com/trezor/trezor-firmware/pull/5760
[#5763]: https://github.com/trezor/trezor-firmware/pull/5763
[#5845]: https://github.com/trezor/trezor-firmware/pull/5845
[#5867]: https://github.com/trezor/trezor-firmware/pull/5867
[#5870]: https://github.com/trezor/trezor-firmware/pull/5870
[#5882]: https://github.com/trezor/trezor-firmware/pull/5882
[#5897]: https://github.com/trezor/trezor-firmware/pull/5897
[#5911]: https://github.com/trezor/trezor-firmware/pull/5911
[#5922]: https://github.com/trezor/trezor-firmware/pull/5922
[#5928]: https://github.com/trezor/trezor-firmware/pull/5928
[#5931]: https://github.com/trezor/trezor-firmware/pull/5931
[#5939]: https://github.com/trezor/trezor-firmware/pull/5939
[#5942]: https://github.com/trezor/trezor-firmware/pull/5942
[#5980]: https://github.com/trezor/trezor-firmware/pull/5980
[#5990]: https://github.com/trezor/trezor-firmware/pull/5990
[#5995]: https://github.com/trezor/trezor-firmware/pull/5995
[#6019]: https://github.com/trezor/trezor-firmware/pull/6019
[#6022]: https://github.com/trezor/trezor-firmware/pull/6022
