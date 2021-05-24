# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## 1.10.1 [24th May 2021]

### Added
- Safety checks setting in T1.  [#1627]


## 1.10.0 [13rd May 2021]

### Added
- Public key to ECDHSessionKey.  [#1518]

### Changed
- Support long PIN of up to 50 digits.  [#1167]
- Included bootloader 1.10.0.  [#1461]
- Allow decreasing the output value in RBF transactions.  [#1491]
- Display nLockTime in human-readable form.  [#1549]


## 1.9.4 [10th February 2021]

### Added
- Replacement transaction signing for replace-by-fee.  [#1367]
- Support for Output Descriptors export.  [#1363]
- Show Ypub/Zpub correctly for multisig GetAddress.  [#1415]
- Show amounts in mBTC, uBTC and sat denominations.  [#1369]

### Changed
- Bump nanopb dependency to 0.4.3.  [#1105]
- Bump nanopb dependency to 0.4.4.  [#1402]
- Minimum auto-lock delay to 1 minute. The former value of 10 seconds still applies for debug builds.  [#1351]

### Deprecated

### Removed
- PIVX support.

### Fixed

### Security

## 1.9.3 [2nd September 2020]

### Added
- XVG support.  [#1165]
- Ask user to confirm custom nLockTime.

### Changed
- Print inverted question mark for non-printable characters.
- Allow spending coins from Bitcoin paths if the coin has implemented strong replay protection via `SIGHASH_FORKID`.  [#1188]

### Deprecated

### Removed
- ETP, GIN, PTC, ZEL support.

### Fixed

### Security
- Show non-empty passphrase on device when it was entered on host.

## 1.9.2 [5th August 2020]

### Added
- Set initialized in storage to false if no mnemonic is present.  [#965]
- Support multiple change-outputs.  [#1098]

### Changed
- `Features.pin_cached` renamed to `unlocked`, and it is now `true` even if PIN is not set.

### Fixed
- Re-introduce ability to spend pre-Overwinter UTXO on Zcash-like coins.  [#1030]

### Security
- Adds a security check to prevent potential issues with paths used in altcoin transactions.

## 1.9.1 [June 2020]

### Security
- Stream previous tx also for Segwit inputs.

## 1.9.0 [April 2020]

### Added
- Wipe code.
- Cache up to 10 sessions (passphrases).
- Add feature to retrieve the next U2F counter.

### Changed
- Make LoadDevice debug only and drop its XPRV feature.
- Passphrase redesign.
- Update nanopb api to version 0.4.

### Fixed
- Disallow changing of settings via dry-run recovery.
- Show xpubs with multisig get_address.

## 1.8.3 [September 2019]

### Fixed
- Small code improvements.

## 1.8.2 [August 2019]

### Fixed
- OLED display security improvements.
- Fix display of non-divisible OMNI amounts.

## 1.8.1 [May 2019]

### Fixed
- Fix fault when using the device with no PIN.
- Fix OMNI transactions parsing.

## 1.8.0 [February 2019]

### Added
- New coins: ATS, KMD, XPM, XSN, ZCL.
- New ETH tokens.

### Changed
- Included bootloader 1.8.0.

### Fixed
- Stellar and NEM fixes.

### Security
- Security improvements.
- Upgraded to new storage format.

## 1.7.3 [December 2018]

### Fixed
- Fix USB issue on some Windows 10 installations.

## 1.7.2 [December 2018]

### Added
- Add support for OMNI layer: OMNI/MAID/USDT.

### Changed
- Included bootloader 1.6.1.

### Fixed
- U2F fixes.
- Don't ask for PIN if it has been just set.

## 1.7.1 [October 2018]

### Added
- Add support for Lisk.
- Add support for Zcash Sapling hardfork.
- Implement seedless setup.

## 1.7.0 [September 2018]

### Added
- Add support for Stellar.

### Changed
- Switch from HID to WebUSB.
- Included bootloader 1.6.0.

## 1.6.3 [August 2018]

### Added
- Implement RSKIP-60 Ethereum checksum encoding.
- Add support for new Ethereum networks (ESN, AKA, ETHO, MUSI, PIRL, ATH, GO).
- Add support for new 80 Ethereum tokens.

### Changed
- Included bootloader 1.5.1.

### Security
- Improve MPU configuration.

## 1.6.2 [June 2018]

### Added
- Add possibility to set custom auto-lock delay.
- Bitcoin Cash cashaddr support.
- Zcash Overwinter hardfork support.
- Support for new coins (DCR, BTCP, FUJI, GRS, VTC, VIA, XZC).
- Support for new Ethereum networks (EOSC, ETHS, ELLA, CTL, EGEM, WAN).
- Support for 500+ new Ethereum tokens.

### Changed
- Included bootloader 1.5.0.

## 1.6.1 [March 2018]

### Changed
- Use fixed-width font for addresses.
- Lots of under-the-hood improvements.
- Included bootloader 1.4.0.

### Fixed
- Fixed issue with write-protection settings.

## 1.6.0 [November 2017]

### Added
- Native SegWit (Bech32) address support.
- Show recognized BIP44/BIP49 paths in GetAddress dialog.
- NEM support.
- Expanse and UBIQ chains support.
- Support or new coins (BTG, DGB, MONA).
- Ed25519 collective signatures (CoSi) support.

## 1.5.2 [August 2017]

### Security
- Clean memory on start.
- Fix storage import from older versions.

## 1.5.1 [July 2017]

### Added
- Enable Segwit for Bitcoin.
- Bcash aka Bitcoin Cash support.
- Message signing/verification for Ethereum and Segwit.
- Use checksum for Ethereum addresses.
- Add more ERC-20 tokens, handle unrecognized ERC-20 tokens.
- Allow "dry run" recovery procedure.
- Allow separated backup procedure.

### Changed
- Make address dialog nicer (switch text/QR via button).

### Security
- Wipe storage after 16 wrong PIN attempts.

## 1.5.0 [May 2017]

### Added
- Enable Segwit for Testnet and Litecoin.
- Enable ERC-20 tokens for Ethereum chains.

## 1.4.2 [January 2017]

### Added
- New Matrix-based recovery method.

### Fixed
- Minor Ethereum fixes (including EIP-155 replay protection).
- Minor USB, U2F and GPG fixes.

## 1.4.1 [October 2016]

### Added
- Support for Zcash JoinSplit transactions.
- Enable device lock after 10 minutes of inactivity.
- Enable device lock by pressing left button for 2 seconds.
- Confirm dialog for U2F counter change.

## 1.4.0 [August 2016]

### Added
- U2F support.
- Ethereum support.
- GPG decryption support.
- Zcash support.

## 1.3.6 [June 2016]

### Added
- Enable advanced transactions such as ones with REPLACE-BY-FEE and CHECKLOCKTIMEVERIFY.
- Message verification now shows address.
- Enable GPG signing support.
- Enable Ed25519 curve (for SSH and GPG).
- Use separate deterministic hierarchy for NIST256P1 and Ed25519 curves.
- Users using SSH already need to regenerate their keys using the new firmware!

### Fixed
- Fix message signing for altcoins.

## 1.3.5 [February 2016]

### Changed
- Double size font for recovery words during the device setup.

### Fixed
- Optimizations for simultaneous access when more applications try communicate with the device.

## 1.3.4 [August 2015]

### Added
- Screensaver active on ClearSession message.
- Support for NIST P-256 curve.
- Show seconds counter during PIN lockdown.

### Changed
- Updated SignIdentity to v2 format.
- Updated maxfee per kb for coins.

## 1.3.3 [April 2015]

### Added
- Ask for PIN on GetAddress and GetPublicKey.

### Fixed
- Signing speed improved.

## 1.3.2 [March 2015]

### Added
- Login feature via SignIdentity message.
- GetAddress for multisig shows M of N description.

### Fixed
- Fix check during transaction streaming.

### Security
- PIN checking in constant time.

## 1.3.1 [February 2015]

### Added
- Enabled OP_RETURN.
- Added option to change home screen.

### Changed
- Optimized signing speed.
- Moved fee calculation before any signing.

### Fixed
- Made PIN delay increase immune against hardware hacking.

## 1.3.0 [December 2014]

### Added
- Added multisig support.
- Added visual validation of receiving address.
- Added ECIES encryption capabilities.

## 1.2.1 [July 2014]

### Added
- Added stack overflow protection.
- Added compatibility with Trezor Bridge.

## 1.2.0 [July 2014]

### Changed
- Better UI for signing/verifying messages.
- Smaller firmware size.

### Fixed
- Fix false positives for fee warning.

## 1.1.0 [June 2014]

### Added
- Added AES support.

### Fixed
- Minor UI fixes.
- Better handling of unexpected messages.

## 1.0.0 [April 2014]

### Added
- Added support for streaming of transactions into the device.

### Fixed
- Removed all current limits on size of signed transaction.

[#965]: https://github.com/trezor/trezor-firmware/issues/965
[#1030]: https://github.com/trezor/trezor-firmware/issues/1030
[#1098]: https://github.com/trezor/trezor-firmware/issues/1098
[#1105]: https://github.com/trezor/trezor-firmware/issues/1105
[#1165]: https://github.com/trezor/trezor-firmware/pull/1165
[#1167]: https://github.com/trezor/trezor-firmware/issues/1167
[#1188]: https://github.com/trezor/trezor-firmware/issues/1188
[#1351]: https://github.com/trezor/trezor-firmware/issues/1351
[#1363]: https://github.com/trezor/trezor-firmware/pull/1363
[#1367]: https://github.com/trezor/trezor-firmware/issues/1367
[#1369]: https://github.com/trezor/trezor-firmware/pull/1369
[#1402]: https://github.com/trezor/trezor-firmware/pull/1402
[#1415]: https://github.com/trezor/trezor-firmware/pull/1415
[#1461]: https://github.com/trezor/trezor-firmware/issues/1461
[#1491]: https://github.com/trezor/trezor-firmware/issues/1491
[#1518]: https://github.com/trezor/trezor-firmware/issues/1518
[#1549]: https://github.com/trezor/trezor-firmware/issues/1549
[#1627]: https://github.com/trezor/trezor-firmware/issues/1627
