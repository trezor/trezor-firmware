# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## 2.1.3 [July 2024]

### Added
- [T3B1] Added support for T3B1.


## 2.1.2 [April 2024]

### Added
- Added firmware update without interaction.
  Split builds of different parts to use simple util.s assembler, while FW+bootloader use interconnected ones.  [#3205]
- Added basic support for STM32U5  [#3370]


## 2.1.1 [September 2023]

### Added
- Added support for STM32F429I-DISC1 board  [#2989]

### Fixed
- Fixed gamma correction settings for Model T  [#2955]
- Removed unwanted delay when resetting LCD on the Model R.  [#3222]


## 2.1.0 [June 2023]

Internal only release for Model R prototypes.

### Added
- Add basic Trezor Model R hardware support  [#2243]
- Boardloader capabilities structure  [#2324]
- Using hardware acceleration (dma2d) for rendering  [#2414]
- Check image model when replacing bootloader  [#2623]
- Added production public keys for T2B1.  [#3048]

### Changed
- CPU Frequency increased to 180 MHz  [#2587]
- Fixed display blinking by increasing backlight PWM frequency  [#2595]

### Security
- Avoid accidental build with broken stack protector  [#1642]


[#1642]: https://github.com/trezor/trezor-firmware/pull/1642
[#2243]: https://github.com/trezor/trezor-firmware/pull/2243
[#2324]: https://github.com/trezor/trezor-firmware/pull/2324
[#2414]: https://github.com/trezor/trezor-firmware/pull/2414
[#2587]: https://github.com/trezor/trezor-firmware/pull/2587
[#2595]: https://github.com/trezor/trezor-firmware/pull/2595
[#2623]: https://github.com/trezor/trezor-firmware/pull/2623
[#2955]: https://github.com/trezor/trezor-firmware/pull/2955
[#2989]: https://github.com/trezor/trezor-firmware/pull/2989
[#3048]: https://github.com/trezor/trezor-firmware/pull/3048
[#3205]: https://github.com/trezor/trezor-firmware/pull/3205
[#3222]: https://github.com/trezor/trezor-firmware/pull/3222
[#3370]: https://github.com/trezor/trezor-firmware/pull/3370
