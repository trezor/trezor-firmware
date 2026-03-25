# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [2.11.1] (22nd April 2026)

### Added
- Add clear signing support for select swap functions from Uniswap.  [#69]
- Support receive-side THP ACK piggybacking.  [#6202]
- Support WebAuthn credentials' pagination.  [#6349]
- Improved information on the Homescreen.  [#6501]
- Added support for `VoteWitnessContract` in Tron.  [#6524]

### Fixed
- Avoid THP deadlock over USB.  [#6506]
- Improved scrolling experience in longer menus.  [#6551]
- Fix device menu refresh on BLE-related events.  [#6589]

## [2.11.0] (18th March 2026)

### Added
- Adding TRON support for TRX and other TRC-20 tokens, smart contracts, and Stake 2.0.  [#5358]
- ETH: Add support for EIP-7702.  [#6394]

### Changed
- Updated libtropic to version 3.0.0.  [#6247]
- Allow ETH staking operations regardless of source.  [#6358]
- Avoid backup workflow cancellation.  [#6483]

### Removed
- Deprecate uploading language blob during firmware update.  [#6103]

### Fixed
- Solana: allow optional program reference for SetComputeUnitLimit.  [#6048]
- Fix crash for ETH Approve calls containing ERC-8021 data.  [#6321]
- Fix 'Connected Trezor is used by another application' bug.  [#6448]

### Security
- Confirm all data during Ethereum transaction hashing.
- Fixed bug in multisig verification.

## [2.10.0] (21st January 2026)

### Added
- Reset Tropic and retry command when alarm mode is detected.  [#6104]
- Introduce wear leveling of mac-and-destroy slots in Tropic.  [#6136]
- Added version build number to Features message.  [#6225]

### Changed
- Update Regulatory screen in the device menu.  [#6281]

### Fixed
- Allow loading translations with different BUILD_VERSION.  [#6228]
- Change bootscreen homebar text to 'Unlock'.  [#6257]
- Fixed address chunkification in certain cases.  [#6279]

### Security
- Fixed side-channel vulnerability in BIP-39 mnemonic processing.

## [2.9.6] (10th December 2025)

### Fixed
- Fixed Stellar Amount and Bitcoin lock time font.  [#6109]
- Make sure to increment THP `seq_bit`.  [#6138]
- Don't stall THP handling during PIN unlock.  [#6145]
- Fixed external tamper trigger clearing.  [#6186]

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

[#69]: https://github.com/trezor/trezor-firmware/pull/69
[#5358]: https://github.com/trezor/trezor-firmware/pull/5358
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
[#6048]: https://github.com/trezor/trezor-firmware/pull/6048
[#6053]: https://github.com/trezor/trezor-firmware/pull/6053
[#6075]: https://github.com/trezor/trezor-firmware/pull/6075
[#6076]: https://github.com/trezor/trezor-firmware/pull/6076
[#6096]: https://github.com/trezor/trezor-firmware/pull/6096
[#6100]: https://github.com/trezor/trezor-firmware/pull/6100
[#6103]: https://github.com/trezor/trezor-firmware/pull/6103
[#6104]: https://github.com/trezor/trezor-firmware/pull/6104
[#6109]: https://github.com/trezor/trezor-firmware/pull/6109
[#6136]: https://github.com/trezor/trezor-firmware/pull/6136
[#6138]: https://github.com/trezor/trezor-firmware/pull/6138
[#6145]: https://github.com/trezor/trezor-firmware/pull/6145
[#6165]: https://github.com/trezor/trezor-firmware/pull/6165
[#6186]: https://github.com/trezor/trezor-firmware/pull/6186
[#6202]: https://github.com/trezor/trezor-firmware/pull/6202
[#6225]: https://github.com/trezor/trezor-firmware/pull/6225
[#6228]: https://github.com/trezor/trezor-firmware/pull/6228
[#6247]: https://github.com/trezor/trezor-firmware/pull/6247
[#6257]: https://github.com/trezor/trezor-firmware/pull/6257
[#6279]: https://github.com/trezor/trezor-firmware/pull/6279
[#6281]: https://github.com/trezor/trezor-firmware/pull/6281
[#6321]: https://github.com/trezor/trezor-firmware/pull/6321
[#6349]: https://github.com/trezor/trezor-firmware/pull/6349
[#6358]: https://github.com/trezor/trezor-firmware/pull/6358
[#6394]: https://github.com/trezor/trezor-firmware/pull/6394
[#6448]: https://github.com/trezor/trezor-firmware/pull/6448
[#6483]: https://github.com/trezor/trezor-firmware/pull/6483
[#6501]: https://github.com/trezor/trezor-firmware/pull/6501
[#6506]: https://github.com/trezor/trezor-firmware/pull/6506
[#6524]: https://github.com/trezor/trezor-firmware/pull/6524
[#6551]: https://github.com/trezor/trezor-firmware/pull/6551
[#6589]: https://github.com/trezor/trezor-firmware/pull/6589
