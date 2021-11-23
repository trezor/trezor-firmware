# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## 2.4.3 [8th December 2021]

### Added
- Convert timestamps to human-readable dates and times.  [#741]
- Support no_script_type option in SignMessage.  [#1586]
- Show address confirmation in SignMessage.  [#1586]
- Support pre-signed external Taproot inputs in Bitcoin.  [#1656]
- Show warning dialog in SignMessage if a non-standard path is used.  [#1656]
- Support spending from Taproot UTXOs.  [#1656]
- Support GetAddress for Taproot addresses.  [#1656]
- Support sending to Taproot addresses.  [#1656]
- Support replacement transactions with Taproot inputs in Bitcoin.  [#1656]
- Support of BIP-340 Schnorr signatures (using secp256k1-zkp).  [#1678]
- Support for Taproot descriptors.  [#1710]
- Ethereum: support 64-bit chain IDs.  [#1771]
- Support for Cardano multi-sig transactions, token minting, script addresses, multi-sig keys, minting keys and native script verification.  [#1772]
- For compatibility with other Cardano implementations, it is now possible to specify which Cardano derivation type is used.  [#1783]
- Full type-checking for Ethereum app.  [#1794]
- Ethereum - support for EIP712 - signing typed data.  [#1835]
- Stellar: add support for StellarManageBuyOfferOp and StellarPathPaymentStrictSendOp.  [#1838]
- Add script_pubkey field to TxInput message.  [#1857]

### Changed
- Cardano root is derived together with the normal master secret.  [#1231]
- Update QR-code-generator library version.  [#1639]
- Faster ECDSA signing and verification (using secp256k1-zkp).  [#1678]
- Most Stellar fields are now required on protobuf level.  [#1755]
- Type-checking enabled for apps.stellar.  [#1755]
- Updated micropython to version 1.17.  [#1789]
- Errors from protobuf decoding are now more expressive.  [#1811]

### Removed
- Disable previous transaction streaming in Bitcoin if all internal inputs are Taproot.  [#1656]
- Remove BELL, ZNY support.  [#1872]

### Fixed
- Remove altcoin message definitions from bitcoin-only build.  [#1633]
- Ethereum: make it optional to view the entire data field when signing transaction.  [#1819]

### Security
- Ensure that the user is always warned about non-standard paths.
- Avoid accidental build with broken stack protector.  [#1642]

### Incompatible changes
- Session must be configured with Initialize(derive_cardano=True), otherwise Cardano functions will fail.  [#1231]
- Timebounds must be set for a Stellar transaction.  [#1755]
- Cardano derivation type must be specified for all Cardano functions.  [#1783]
- Ethereum non-EIP-155 cross-chain signing is no longer supported.  [#1794]
- Stellar: rename StellarManageOfferOp to StellarManageSellOfferOp, StellarPathPaymentOp to StellarPathPaymentStrictReceiveOp and StellarCreatePassiveOfferOp to StellarCreatePassiveSellOfferOp.  [#1838]


## 2.4.2 [16th September 2021]

### Added
- [emulator] Added option to dump detailed Micropython memory layout  [#1557]
- Support for Ethereum EIP1559 transactions  [#1604]
- Re-enabled Firo support  [#1767]

### Changed
- Converted all remaining code to common layouts.  [#1545]
- Memory optimization of BTC signing and CBOR decoding.  [#1581]
- Cardano transaction parameters are now streamed into the device one by one instead of being sent as one large object  [#1683]
- Thanks to transaction streaming, Cardano now supports larger transactions (tested with 62kB transactions, but supposedly even larger transactions are supported)  [#1683]
- Refactor RLP codec for better clarity and some small memory savings.  [#1704]
- Refer to `m/48'/...` multisig derivation paths as BIP-48 instead of Purpose48.  [#1744]

### Removed
- Removed support for Lisk  [#1765]

### Fixed
- Disable TT features (SD card, SBU, FAT) for T1 build.  [#1163]
- It is no longer possible to sign Cardano transactions containing paths belonging to multiple accounts (except for Byron to Shelley migration)  [#1683]
- Add new rpId to Binance's FIDO definition.  [#1705]
- Don't use format strings in keyctl-proxy  [#1707]
- Properly respond to USB events while on a paginated screen.  [#1708]

### Incompatible changes
- Due to transaction streaming in Cardano, it isn't possible to return the whole serialized transaction anymore. Instead the transaction hash, transaction witnesses and auxiliary data supplement are returned and the serialized transaction needs to be assembled by the client.  [#1683]


## 2.4.1 [14th July 2021]

### Added
- ButtonRequest for multi-page views contains number of pages.  [#1671]

### Changed
- Converted altcoin apps to common layout code.  [#1538]
- Reimplement protobuf codec and library in Rust  [#1541]
- Cardano: Reintroduce maximum transaction output size limitation  [#1606]
- Cardano: Improve address validation and decouple it from address derivation  [#1606]
- Cardano: Remove sorting of policies, assets and withdrawals. Rather add them to the transaction in the order they arrived in.  [#1672]
- Cardano: Forbid withdrawals with the same path in a single transaction  [#1672]

### Removed
- Removed support for Firo  [#1647]
- Removed support for Hatch  [#1650]

### Fixed
- Unify Features.revision reporting with legacy  [#1620]
- Fix red screen on shutdown.  [#1658]
- Empty passphrase is properly cached in Cardano functions  [#1659]

### Security
- Ensure that all testnet coins use SLIP-44 coin type 1.
- Disable all testnet coins from accessing Bitcoin paths.
- Restrict BIP-45 paths to Bitcoin and coins with strong replay protection.
- Fix operation source account encoding in Stellar.


## 2.4.0 [9th June 2021]

### Added
- Decred staking.  [#1249]
- Locking the device by holding finger on the homescreen for 2.5 seconds.  [#1404]
- Public key to ECDHSessionKey.  [#1518]
- Rust FFI for MicroPython.  [#1540]

### Changed
- Support PIN of unlimited length.  [#1167]
- Allow decreasing the output value in RBF transactions.  [#1491]
- Cardano: Allow stake pool registrations with zero margin.  [#1502]
- Cardano: Assets are now shown as CIP-0014.  [#1510]
- Random delays use ChaCha-based DRBG instead of HMAC-DRBG.  [#1554]
- Reduce memory fragmentation by clearing memory after every workflow.  [#1565]
- Update some FIDO icons.  [#1456]

### Fixed
- Import errors on T1 startup.  [#24]
- Improve wording when showing multisig XPUBs.  [#1431]


## 2.3.6 [15th February 2021]

### Added
- Compatibility paths for Unchained Capital.  [#1467]

## 2.3.5 [10th February 2021]

### Added
- CoinJoin preauthorization and signing flow.  [#1053]
- Value of the `safety-checks` setting to the `Features` message.  [#1193]
- ERC20 tokens show contract address for confirmation. Unknown ERC20 tokens show wei amount.  [#800]
- Replacement transaction signing for replace-by-fee and PayJoin.  [#1292]
- Support for Output Descriptors export.  [#1363]
- Paginated display for signing/verifying long messages.  [#1271]
- Show Ypub/Zpub correctly for multisig GetAddress.  [#1415]
- Show amounts in mBTC, uBTC and sat denominations.  [#1369]

### Changed
- The `safety-checks` setting gained new possible value `PromptTemporarily` which overrides safety checks until device reboot.  [#1133]
- Protobuf codec now enforces `required` fields and pre-fills default values.  [#379]
- `TxAck` messages are now decoded into "polymorphic" subtypes instead of the common `TxAck` type.
- Bump nanopb dependency to 0.4.3.  [#1105]
- BIP-32 paths must now match a pre-defined path schema to be considered valid.  [#1184]
- Minimum auto-lock delay to 1 minute. The former value of 10 seconds still applies for debug builds.  [#1351]
- It is again possible to sign for Ethereum clones that are not officially supported.  [#1335]
- Bump nanopb dependency to 0.4.4.  [#1402]
- Automatic breaking text on whitespace.  [#1384]
- Introduced limit of 32 characters for device label.  [#1399]

### Deprecated

### Removed
- PIVX support
- dropped debug-only `DebugLinkShowText` functionality

### Fixed
- Path warning is not shown on `GetAddress(show_display=False)` call.  [#1206]
- Settings are also erased from RAM when device is wiped.  [#1322]

### Security

## 2.3.4 [7th October 2020]

### Added
- Support for the upcoming Monero hard fork.  [#1246]

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

[#24]: https://github.com/trezor/trezor-firmware/issues/24
[#379]: https://github.com/trezor/trezor-firmware/issues/379
[#741]: https://github.com/trezor/trezor-firmware/issues/741
[#800]: https://github.com/trezor/trezor-firmware/issues/800
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
[#1105]: https://github.com/trezor/trezor-firmware/issues/1105
[#1115]: https://github.com/trezor/trezor-firmware/issues/1115
[#1118]: https://github.com/trezor/trezor-firmware/issues/1118
[#1126]: https://github.com/trezor/trezor-firmware/issues/1126
[#1133]: https://github.com/trezor/trezor-firmware/issues/1133
[#1139]: https://github.com/trezor/trezor-firmware/issues/1139
[#1159]: https://github.com/trezor/trezor-firmware/issues/1159
[#1163]: https://github.com/trezor/trezor-firmware/issues/1163
[#1165]: https://github.com/trezor/trezor-firmware/pull/1165
[#1167]: https://github.com/trezor/trezor-firmware/issues/1167
[#1173]: https://github.com/trezor/trezor-firmware/pull/1173
[#1184]: https://github.com/trezor/trezor-firmware/issues/1184
[#1188]: https://github.com/trezor/trezor-firmware/issues/1188
[#1190]: https://github.com/trezor/trezor-firmware/issues/1190
[#1193]: https://github.com/trezor/trezor-firmware/issues/1193
[#1206]: https://github.com/trezor/trezor-firmware/issues/1206
[#1231]: https://github.com/trezor/trezor-firmware/issues/1231
[#1246]: https://github.com/trezor/trezor-firmware/issues/1246
[#1249]: https://github.com/trezor/trezor-firmware/issues/1249
[#1271]: https://github.com/trezor/trezor-firmware/issues/1271
[#1292]: https://github.com/trezor/trezor-firmware/issues/1292
[#1322]: https://github.com/trezor/trezor-firmware/issues/1322
[#1335]: https://github.com/trezor/trezor-firmware/issues/1335
[#1351]: https://github.com/trezor/trezor-firmware/issues/1351
[#1363]: https://github.com/trezor/trezor-firmware/pull/1363
[#1369]: https://github.com/trezor/trezor-firmware/pull/1369
[#1384]: https://github.com/trezor/trezor-firmware/issues/1384
[#1399]: https://github.com/trezor/trezor-firmware/issues/1399
[#1402]: https://github.com/trezor/trezor-firmware/pull/1402
[#1404]: https://github.com/trezor/trezor-firmware/issues/1404
[#1415]: https://github.com/trezor/trezor-firmware/pull/1415
[#1431]: https://github.com/trezor/trezor-firmware/pull/1431
[#1456]: https://github.com/trezor/trezor-firmware/pull/1456
[#1467]: https://github.com/trezor/trezor-firmware/issues/1467
[#1491]: https://github.com/trezor/trezor-firmware/issues/1491
[#1502]: https://github.com/trezor/trezor-firmware/issues/1502
[#1510]: https://github.com/trezor/trezor-firmware/issues/1510
[#1518]: https://github.com/trezor/trezor-firmware/issues/1518
[#1538]: https://github.com/trezor/trezor-firmware/issues/1538
[#1540]: https://github.com/trezor/trezor-firmware/issues/1540
[#1541]: https://github.com/trezor/trezor-firmware/issues/1541
[#1545]: https://github.com/trezor/trezor-firmware/issues/1545
[#1554]: https://github.com/trezor/trezor-firmware/issues/1554
[#1557]: https://github.com/trezor/trezor-firmware/issues/1557
[#1565]: https://github.com/trezor/trezor-firmware/issues/1565
[#1581]: https://github.com/trezor/trezor-firmware/issues/1581
[#1586]: https://github.com/trezor/trezor-firmware/issues/1586
[#1604]: https://github.com/trezor/trezor-firmware/issues/1604
[#1606]: https://github.com/trezor/trezor-firmware/issues/1606
[#1620]: https://github.com/trezor/trezor-firmware/issues/1620
[#1633]: https://github.com/trezor/trezor-firmware/issues/1633
[#1639]: https://github.com/trezor/trezor-firmware/issues/1639
[#1642]: https://github.com/trezor/trezor-firmware/issues/1642
[#1647]: https://github.com/trezor/trezor-firmware/issues/1647
[#1650]: https://github.com/trezor/trezor-firmware/issues/1650
[#1656]: https://github.com/trezor/trezor-firmware/issues/1656
[#1658]: https://github.com/trezor/trezor-firmware/issues/1658
[#1659]: https://github.com/trezor/trezor-firmware/issues/1659
[#1671]: https://github.com/trezor/trezor-firmware/issues/1671
[#1672]: https://github.com/trezor/trezor-firmware/issues/1672
[#1678]: https://github.com/trezor/trezor-firmware/issues/1678
[#1683]: https://github.com/trezor/trezor-firmware/issues/1683
[#1704]: https://github.com/trezor/trezor-firmware/issues/1704
[#1705]: https://github.com/trezor/trezor-firmware/issues/1705
[#1707]: https://github.com/trezor/trezor-firmware/issues/1707
[#1708]: https://github.com/trezor/trezor-firmware/issues/1708
[#1710]: https://github.com/trezor/trezor-firmware/issues/1710
[#1744]: https://github.com/trezor/trezor-firmware/issues/1744
[#1755]: https://github.com/trezor/trezor-firmware/issues/1755
[#1765]: https://github.com/trezor/trezor-firmware/issues/1765
[#1767]: https://github.com/trezor/trezor-firmware/issues/1767
[#1771]: https://github.com/trezor/trezor-firmware/issues/1771
[#1772]: https://github.com/trezor/trezor-firmware/issues/1772
[#1783]: https://github.com/trezor/trezor-firmware/issues/1783
[#1789]: https://github.com/trezor/trezor-firmware/issues/1789
[#1794]: https://github.com/trezor/trezor-firmware/issues/1794
[#1811]: https://github.com/trezor/trezor-firmware/issues/1811
[#1819]: https://github.com/trezor/trezor-firmware/issues/1819
[#1835]: https://github.com/trezor/trezor-firmware/issues/1835
[#1838]: https://github.com/trezor/trezor-firmware/issues/1838
[#1857]: https://github.com/trezor/trezor-firmware/issues/1857
[#1872]: https://github.com/trezor/trezor-firmware/issues/1872
