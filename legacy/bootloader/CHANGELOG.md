# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## 1.12.1 [February 2023]

### Fixed
- Correctly distrust v2-signed firmwares.


## 1.12.0 [internal only - January 2023]

### Added
- T1 bootloader: verify firmware signatures based on SignMessage, add signature debugging  [#2568]

### Fixed
- Better way to debug T1 combinations of debug/production combinations of bootloader and firmware  [#2423]


## 1.11.0 [May 2022]

### Added
- Bootloader will report version of installed firmware.  [#2231]

### Fixed
- Compress firmware verification coordinates to be able link bootloader into preallocated space.  [#1884]

### Security
- Erase storage when downgrading below fix_version.
- Avoid accidental build with broken stack protector  [#1642]


## 1.10.0 [May 2021]

### Added
- "Stay in bootloader" flag.  [#1461]
- Soft-reset (reboots itself after firmware installation).

### Changed
- Use Trezor instead of TREZOR.

## 1.8.0 [February 2019]

### Changed
- Make the update process more similar to Model T process.
- Require only left button to start the bootloader.

## 1.6.1 [December 2018]

### Fixed
- Fix USB issue on some Windows 10 installations.

## 1.6.0 [September 2018]

### Changed
- Switch from HID to WebUSB.

## 1.5.1 [August 2018]

### Fixed
- Improve MPU configuration.

## 1.5.0 [Jun 2018]

### Fixed
- Make unofficial firmwares work again.

## 1.4.0 [March 2018]

### Added
- More flash-write tests.
- Support WipeDevice message.

### Fixed
- Don't restore storage from unofficial firmware.
- Activate MPU and don't switch VTOR table for unofficial firmware.

## 1.3.3 [August 2017]

### Added
- Add self-test.

### Fixed
- Erase metadata backup after usage.
- Erase SRAM on application start.

## 1.3.2 [July 2017]

### Added
- Add self-test.

### Changed
- Don't show recovery seed warning if firmware is flashed for the first time.
- Don't show fingerprint if firmware is flashed for the first time.

### Fixed
- Compute firmware hash before checking signatures.
- Fix usage of RNG before setup.
- Fix stack protector fault.

## 1.3.1 [February 2017]

### Fixed
- Fix button testing so it does not break USB communication.

## 1.3.0 [October 2016]

### Added
- Add test for buttons.

### Changed
- Clean USB descriptor.
- Return firmware_present in Features response.
- Don't halt on broken firmware, stay in bootloader.

## 1.2.8 [September 2016]

### Fixed
- Don't halt on broken firmware.

## 1.2.7 [May 2016]

### Changed
- Optimize speed of firmware update.

## 1.2.6 [February 2016]

### Changed
- Show hash of unofficial firmware.
- Clean USB descriptor.

### Fixed
- Use stack protector.

## 1.2.5 [October 2014]

### Added
- Initial import of code.

[#1461]: https://github.com/trezor/trezor-firmware/pull/1461
[#1642]: https://github.com/trezor/trezor-firmware/pull/1642
[#1884]: https://github.com/trezor/trezor-firmware/pull/1884
[#2231]: https://github.com/trezor/trezor-firmware/pull/2231
[#2423]: https://github.com/trezor/trezor-firmware/pull/2423
[#2568]: https://github.com/trezor/trezor-firmware/pull/2568
