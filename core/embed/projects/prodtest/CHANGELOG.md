
## 0.3.0 [16th July 2025]

### Added
- [T3B1,T3T1] Added hw-revision command.  [#4682]
- Added device ID write/read commands.  [#4735]
- Added command for updating bootloader.  [#5227]

### Changed
- Show device ID in protest QR code.  [#4735]
- Report build version in prodtest intro and version command.  [#5050]

### Fixed
- [T2B1,T3B1] Fix displaying QR code and text.  [#4564]

### Incompatible changes
- Completely redesigned. See the updated documentation for details.  [#4534]

## 0.2.12 [22th January 2025]

### Changed
- Changed resolution of TOUCH_POWER command parameter to milliseconds.  [#4407]

### Fixed
- Fix BOOTLOADER VERSION command.  [#4405]

## 0.2.11 [20th November 2024]

### Fixed
- Fixed a device crash in the CPUID READ command.  [#4310]
- Fixed writing data (variant, batch) to OTP.  [#4313]

## 0.2.10 [20th November 2024]

### Added
- Added TOUCH_POWER command to allow testing touch power supply without connected touch screen.  [#4252]

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
[#4252]: https://github.com/trezor/trezor-firmware/pull/4252
[#4310]: https://github.com/trezor/trezor-firmware/pull/4310
[#4313]: https://github.com/trezor/trezor-firmware/pull/4313
[#4405]: https://github.com/trezor/trezor-firmware/pull/4405
[#4407]: https://github.com/trezor/trezor-firmware/pull/4407
[#4534]: https://github.com/trezor/trezor-firmware/pull/4534
[#4564]: https://github.com/trezor/trezor-firmware/pull/4564
[#4682]: https://github.com/trezor/trezor-firmware/pull/4682
[#4735]: https://github.com/trezor/trezor-firmware/pull/4735
[#5050]: https://github.com/trezor/trezor-firmware/pull/5050
[#5227]: https://github.com/trezor/trezor-firmware/pull/5227
