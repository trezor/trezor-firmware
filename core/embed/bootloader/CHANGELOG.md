# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

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
[#2879]: https://github.com/trezor/trezor-firmware/pull/2879
[#2896]: https://github.com/trezor/trezor-firmware/pull/2896
