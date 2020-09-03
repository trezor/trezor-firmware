# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## 2.3.4 [to be released on 4th November 2020]

### Added
- CoinJoin preauthorization and siging flow.  [#1053]

### Changed

### Deprecated

### Removed

### Fixed

### Security

## 2.3.3 [2nd September 2020]

### Added
- Running the frozen version of the emulator doesn't need arguments.  [#1115]
- XVG support.  [#1165]
- Hard limit on transaction fees. Can be disabled using `safety-checks`. [#1087]

### Changed
- Print inverted question mark for non-printable characters.
- Remove pre-fill bar from text rendering functions.  [#1173]
- Display coin name when signing or verifying messages.  [#1159]
- Allow spending coins from Bitcoin paths if the coin has implemented strong replay protection via `SIGHASH_FORKID`.  [#1188]

### Deprecated

### Removed
- Remove ETP, GIN, PTC, ZEL support.
- Drop support for signing Zcash v3 transactions.  [#982] 

### Fixed
- CRW addresses are properly generated.  [#1139]
- Fix boot loop after uploading invalid homescreen.  [#1118]
- Allow 49/x not 49/x' for Casa.  [#1190]
- Make sure Homescreen is properly initialized.  [#1095] 

### Security
- Show non-empty passphrase on device when it was entered on host.
- Show warning if nLockTime is set but ineffective due to all nSequence values being 0xffffffff.

## 2.3.2 [5th August 2020]

### Added
- Soft lock.  [#958]
- Auto lock.  [#1027]
- Dedicated `initialized` field in storage.
- Support EXTERNAL transaction inputs with a SLIP-0019 proof of ownership.  [#1052]
- Support pre-signed EXTERNAL transaction inputs.
- Support multiple change-outputs.  [#1098]
- New option `safety-checks` allows overriding "forbidden key path" errors.  [#1126]
- Support for Cardano Shelley.  [#948]

### Changed
- `Features.pin_cached` renamed to `unlocked`.
- Forbid all settings if the device is not yet initialized.  [#1056]
- Rewrite USB codec and Protobuf decoder to be more memory-efficient.  [#1089]
- Allow compatibility namespaces for Casa and Green Address. 

### Deprecated
- Deprecate `overwintered` field in `SignTx` and `TxAck`.

### Removed
- Generated protobuf classes now do not contain deprecated fields.

### Fixed
- Fix cancel icon in PIN dialog.  [#1042]
- Fix repaint bug in QR code rendering.  [#1067]
- Fix QR code overlapping in Monero address.  monero-gui#2960, [#1074]
- Re-introduce ability to spend pre-Overwinter UTXO on Zcash-like coins.  [#1030]

## 2.3.1 [June 2020]

### Changed
- Refactor Bitcoin signing
- Refactor Keychain into a decorator

### Security
- Stream previous tx also for Segwit inputs

## 2.3.0 [April 2020]

### Added
- Cache up to 10 sessions (passphrases)
- SD card protection
- Show xpubs with multisig get_address
- Introduce FatFS (version 0.14)
- Support Ed25519 in FIDO2

### Changed
- Passphrase redesign
- Upgrade MicroPython to 1.12

### Fixed
- Properly limit passphrase to 50 bytes and not 50 characters
- Monero: add confirmation dialog for unlock_time

## 2.2.0 [January 2020]

### Added
- Add feature to retrieve the next U2F counter.
- Wipe code.
- Add screen for time bounds in Stellar.

### Fixed
- Fix continuous display blinking with Android in U2F.
- U2F UX improvements.

### Changed
- Rework Recovery persistence internally.

### Removed
- Remove unused ButtonRequest.data field.
- Disallow changing of settings via dry-run recovery.

## 2.1.8 [November 2019]

### Added
- Support Tezos 005-BABYLON hardfork.
- Show XPUBs in GetAddress for multisig.

### Security
- Security improvements.

## 2.1.7 [October 2019]

### Fixed
- Fix low memory issue.

## 2.1.6 [October 2019]

### Added
- Super Shamir.
- FIDO2.
- FIDO2 credential management via trezorctl.
- BackupType in Features.

### Changed
- Refactor Shamir related codebase.

### Fixed
- Fix storage keys module visibility bug (6ad329) introduced in 2.1.3 (46e4c0) which was breaking upgrades.

## 2.1.5 [September 2019]

### Added
- Binance Coin support.
- Introduce Features.Capabilities.

### Fixed
- Fix for sluggish U2F authentication when using Shamir.
- Fix UI for Shamir with 33 words.
- Fix Wanchain signing.

## 2.1.4 [August 2019 hotfix]

### Fixed
- Shamir Backup reset device hotfix.

## 2.1.3 [August 2019]

### Added
- Shamir Backup with Recovery persistence.

### Fixed
- Touchscreen freeze fix.
- Fix display of non-divisible OMNI amounts.

## 2.1.2 [unreleased]

### Added
- Shamir Backup feature preview.

## 2.1.1 [June 2019]

### Added
- EOS support.
- Set screen rotation via user setting.
- Display non-zero locktime values.

### Changed
- Don't rotate the screen via swipe gesture.
- More strict path validations.

### Fixed
- Hotfix for touchscreen freeze.
- Monero UI fixes.
- Speed and memory optimizations.

## 2.1.0 [March 2019]

### Added
- New coins: ATS, AXE, FLO, GIN, KMD, NIX, PIVX, REOSC, XPM, XSN, ZCL.
- New ETH tokens.

### Fixed
- Ripple, Stellar, Cardano and NEM fixes.

### Changed
- Included bootloader 2.0.3.

### Security
- Security improvements.
- Upgraded to new storage format.

## 2.0.10 [December 2018]

### Added
- Add support for OMNI layer: OMNI/MAID/USDT.
- Add support for new coins: BTX, CPC, GAME, RVN.
- Add support for new Ethereum tokens.

### Changed
- Included bootloader 2.0.2.

### Fixed
- Fix Monero payment ID computation.
- Fix issue with touch screen and flickering.

## 2.0.9 [November 2018]

### Fixed
- Small Monero and Segwit bugfixes.

## 2.0.8 [October 2018]

### Added
- Monero support.
- Cardano support.
- Stellar support.
- Ripple support.
- Tezos support.
- Decred support.
- Groestlcoin support.
- Zencash support.
- Zcash sapling hardfork support.
- Implemented seedless setup.

## 2.0.7 [June 2018]

### Added
- Bitcoin Cash cashaddr support.
- Zcash Overwinter hardfork support.
- NEM support.
- Lisk support.
- Show warning on home screen if PIN is not set.
- Support for new coins (BTCP, FUJI, VTC, VIA, XZC).
- Support for new Ethereum networks (EOSC, ETHS, ELLA, CTL, EGEM, WAN).
- Support for 500+ new Ethereum tokens.

## 2.0.6 [March 2018]

### Added
- Add special characters to passphrase keyboard.

### Fixed
- Fix layout for Ethereum transactions.
- Fix public key generation for SSH and GPG.

## 2.0.5 [March 2018]

### Added
- First public release.

[#948]: https://github.com/trezor/trezor-firmware/issues/948
[#958]: https://github.com/trezor/trezor-firmware/issues/958
[#982]: https://github.com/trezor/trezor-firmware/issues/982
[#1027]: https://github.com/trezor/trezor-firmware/issues/1027
[#1030]: https://github.com/trezor/trezor-firmware/issues/1030
[#1042]: https://github.com/trezor/trezor-firmware/issues/1042
[#1052]: https://github.com/trezor/trezor-firmware/issues/1052
[#1053]: https://github.com/trezor/trezor-firmware/issues/1053
[#1056]: https://github.com/trezor/trezor-firmware/issues/1056
[#1067]: https://github.com/trezor/trezor-firmware/issues/1067
[#1074]: https://github.com/trezor/trezor-firmware/issues/1074
[#1087]: https://github.com/trezor/trezor-firmware/issues/1087
[#1089]: https://github.com/trezor/trezor-firmware/issues/1089
[#1095]: https://github.com/trezor/trezor-firmware/issues/1095
[#1098]: https://github.com/trezor/trezor-firmware/issues/1098
[#1115]: https://github.com/trezor/trezor-firmware/issues/1115
[#1118]: https://github.com/trezor/trezor-firmware/issues/1118
[#1126]: https://github.com/trezor/trezor-firmware/issues/1126
[#1139]: https://github.com/trezor/trezor-firmware/issues/1139
[#1159]: https://github.com/trezor/trezor-firmware/issues/1159
[#1165]: https://github.com/trezor/trezor-firmware/pull/1165
[#1173]: https://github.com/trezor/trezor-firmware/pull/1173
[#1188]: https://github.com/trezor/trezor-firmware/issues/1188
[#1190]: https://github.com/trezor/trezor-firmware/issues/1190
