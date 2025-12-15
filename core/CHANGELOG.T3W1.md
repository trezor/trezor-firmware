# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [2.9.6] (4th December 2025)

### Fixed
- Fixed Stellar Amount and Bitcoin lock time font.  [#6109]
- Make sure to increment THP `seq_bit`.  [#6138]
- Don't stall THP handling during PIN unlock.  [#6145]

## [2.9.5] (28th November 2025)

### Fixed
- Fixed tamper RSOD not showing.  [#6165]

## [2.9.4] (19th November 2025)

### Added
- Show an explicit warning when `ButtonRequest` ACK is delayed.  [#5884]
- Show warning on Ripple destination tag missing.  [#5931]
- Use LED effect for BLE pairing.  [#6076]

### Changed
- Deprecate ETH Holesky testnet and use Hoodi testnet instead.  [#5942]

### Fixed
- Erase BLE bonds too after entering wipe code.  [#5939]
- Restart BLE advertising after re-enabling BLE.  [#5952]
- Fix false "NO USB CONNECTION" warning on the home screen.  [#5980]
- Fix homescreen LED blinking.  [#5990]
- Improve speed of translations upload over bluetooth.  [#5995]
- Adjust random part of BLE device name during pairing.  [#6019]
- Synchronize LED and background in tutorial.  [#6022]
- Restart bluetooth on reboot from device menu.  [#6023]
- Removed warning screen for some non-ERC20 contract calls.  [#6032]
- Removed "More info" menu item from screens that don't have more info.  [#6053]
- Fixed touch issue causing stuck hold-to-confirm buttons.  [#6075]
- Reduce +/- buttons' size to allow more text to fit.  [#6096]
- Add missing `get_serial_number` handler.  [#6100]

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
[#5884]: https://github.com/trezor/trezor-firmware/pull/5884
[#5897]: https://github.com/trezor/trezor-firmware/pull/5897
[#5911]: https://github.com/trezor/trezor-firmware/pull/5911
[#5922]: https://github.com/trezor/trezor-firmware/pull/5922
[#5928]: https://github.com/trezor/trezor-firmware/pull/5928
[#5931]: https://github.com/trezor/trezor-firmware/pull/5931
[#5939]: https://github.com/trezor/trezor-firmware/pull/5939
[#5942]: https://github.com/trezor/trezor-firmware/pull/5942
[#5952]: https://github.com/trezor/trezor-firmware/pull/5952
[#5980]: https://github.com/trezor/trezor-firmware/pull/5980
[#5990]: https://github.com/trezor/trezor-firmware/pull/5990
[#5995]: https://github.com/trezor/trezor-firmware/pull/5995
[#6019]: https://github.com/trezor/trezor-firmware/pull/6019
[#6022]: https://github.com/trezor/trezor-firmware/pull/6022
[#6023]: https://github.com/trezor/trezor-firmware/pull/6023
[#6032]: https://github.com/trezor/trezor-firmware/pull/6032
[#6053]: https://github.com/trezor/trezor-firmware/pull/6053
[#6075]: https://github.com/trezor/trezor-firmware/pull/6075
[#6076]: https://github.com/trezor/trezor-firmware/pull/6076
[#6096]: https://github.com/trezor/trezor-firmware/pull/6096
[#6100]: https://github.com/trezor/trezor-firmware/pull/6100
[#6109]: https://github.com/trezor/trezor-firmware/pull/6109
[#6138]: https://github.com/trezor/trezor-firmware/pull/6138
[#6145]: https://github.com/trezor/trezor-firmware/pull/6145
[#6165]: https://github.com/trezor/trezor-firmware/pull/6165
