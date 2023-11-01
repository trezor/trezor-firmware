# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## 2.1.4 [November 2023]

### Added
- Minimize risk of losing seed when upgrading firmware.  [#2794]
- Support interaction-less upgrade.  [#2919]


## 2.1.3 [September 2023]

### Changed
- Split builds of different parts to use simple util.s assembler, while FW+bootloader use interconnected ones.  [#3205]
- No longer erases seed when firmware is corrupted but firmware header is correct and signed. Added firmware corrupted info to bootloader screen.  [#3122]
- Correctly reinitialize Optiga SE when rebooting.  [#3303]


## 2.1.2 [August 2023]

Internal only release for Model R prototypes.

### Added
- Added support for STM32F429I-DISC1 board  [#2989]
- Locked bootloader support: bootloader will disallow installation of unofficial firmware unless the Optiga pairing secret is erased.
- Support unlocking the bootloader via `UnlockBootloader` message.

### Changed
- Show "empty lock" logo together with model name (replacing the "filled lock" logo for bootloader entirely).  [#3222]
- When building a `PRODUCTION=0` bootloader, it will recognize the development signing keys instead of production ones.

### Fixed
- Fixed gamma correction settings for Model T  [#2955]


## 2.1.1 [June 2023]

Internal only release for Model R prototypes.

### Added
- Added production public keys for T2B1.  [#3048]
- Added UI for T2B1.

### Fixed
- Fix installation of images smaller than 128kB.  [#2941]


## 2.1.0 [April 2023]

### Added
- Optimize touch controller communication  [#262]
- Bootloader redesign  [#1049]
- Add basic Trezor Model R hardware support  [#2243]
- Jump and stay in bootloader from firmware through SVC call reverse trampoline.  [#2284]
- Add RGB LED for Model R  [#2300]
- Using hardware acceleration (dma2d) for rendering  [#2414]
- Add stack overflow detection  [#2427]
- Add model info to image and check when installing/running firmware  [#2623]
- Introduced bootloader emulator.  [#2879]

### Changed
- Update logic of vendor header comparison.  [#1599]
- CPU Frequency increased to 180 MHz  [#2587]
- Fixed display blinking by increasing backlight PWM frequency  [#2595]

### Fixed
- Fixed retries counter when reading from USB  [#2896]

### Security
- Avoid accidental build with broken stack protector  [#1642]


## 2.0.4 [May 2022]

### Security
- Intentionally skipped this version due to fake devices

## 2.0.3 [March 2019]

### Security
- Enable MPU
- Introduce delays to USB stack

## 2.0.2 [December 2018]

### Added
- Support for a new display driver

## 2.0.1 [February 2018]

### Added
- First public release
[#262]: https://github.com/trezor/trezor-firmware/pull/262
[#1049]: https://github.com/trezor/trezor-firmware/pull/1049
[#1599]: https://github.com/trezor/trezor-firmware/pull/1599
[#1642]: https://github.com/trezor/trezor-firmware/pull/1642
[#2243]: https://github.com/trezor/trezor-firmware/pull/2243
[#2284]: https://github.com/trezor/trezor-firmware/pull/2284
[#2300]: https://github.com/trezor/trezor-firmware/pull/2300
[#2414]: https://github.com/trezor/trezor-firmware/pull/2414
[#2427]: https://github.com/trezor/trezor-firmware/pull/2427
[#2587]: https://github.com/trezor/trezor-firmware/pull/2587
[#2595]: https://github.com/trezor/trezor-firmware/pull/2595
[#2623]: https://github.com/trezor/trezor-firmware/pull/2623
[#2794]: https://github.com/trezor/trezor-firmware/pull/2794
[#2879]: https://github.com/trezor/trezor-firmware/pull/2879
[#2896]: https://github.com/trezor/trezor-firmware/pull/2896
[#2919]: https://github.com/trezor/trezor-firmware/pull/2919
[#2941]: https://github.com/trezor/trezor-firmware/pull/2941
[#2955]: https://github.com/trezor/trezor-firmware/pull/2955
[#2989]: https://github.com/trezor/trezor-firmware/pull/2989
[#3048]: https://github.com/trezor/trezor-firmware/pull/3048
[#3122]: https://github.com/trezor/trezor-firmware/pull/3122
[#3205]: https://github.com/trezor/trezor-firmware/pull/3205
[#3222]: https://github.com/trezor/trezor-firmware/pull/3222
[#3303]: https://github.com/trezor/trezor-firmware/pull/3303
