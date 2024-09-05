
## 0.2.9 [18th September 2024]

### Added
- Added commands to read bootloader and boardloader versions.  [#3752]
- Added TOUCH_CUSTOM and TOUCH_IDLE commands.  [#4064]

### Changed
- [T3B1] Changed welcome screen to show full white display.  [#4140]


## 0.2.8 [19th July 2024]

### Added
- [T3B1] Added support for T3B1.

### Fixed
- Fix TOUCH VERSION command  [#3900]


## 0.2.7 [10th June 2024]

### Added
- Added REBOOT command  [#3932]

### Fixed
- Fix TOUCH_VERSION command  [#3932]


## 0.2.6 [6th May 2024]

### Added
- Added FIRMWARE VERSION command.

### Changed
- [T3T1] Changed USB manufacturer string to "Trezor Company" and product string to "Trezor Safe 5" in the USB descriptor strings.  [#3770]

### Fixed
- [T3T1] Fixed `WIPE` command on STM32U5.  [#3769]


## 0.2.5 [16th April 2024]

### Added
- Added basic support for STM32U5.  [#3370]
- [T3T1] Added support for T3T1.
- [T3T1] Added `HAPTIC` to test haptic feedback.
- [T2T1, T3T1] Added `TOUCH VERSION` to get version number of touch controller.
- Added `VARIANT READ` to read out result of `VARIANT` command.


## 0.2.4 [20th December 2023]

### Added

- [T2B1] `SEC READ` to read out value of SEC counter.
- [T2B1] Check certificate chain upon `CERTDEV READ`, to block bad Optiga signatures
  from being written to device.

### Fixed

- [T2B1] Improve Optiga metadata handling.

## 0.2.3 [06th October 2023]

### Added
- Started changelog.

### Changed
- [T2B1] Start with all-white screen instead of border.  [#3325]

[#3325]: https://github.com/trezor/trezor-firmware/pull/3325
[#3370]: https://github.com/trezor/trezor-firmware/pull/3370
[#3752]: https://github.com/trezor/trezor-firmware/pull/3752
[#3769]: https://github.com/trezor/trezor-firmware/pull/3769
[#3770]: https://github.com/trezor/trezor-firmware/pull/3770
[#3900]: https://github.com/trezor/trezor-firmware/pull/3900
[#3932]: https://github.com/trezor/trezor-firmware/pull/3932
[#4064]: https://github.com/trezor/trezor-firmware/pull/4064
[#4140]: https://github.com/trezor/trezor-firmware/pull/4140
