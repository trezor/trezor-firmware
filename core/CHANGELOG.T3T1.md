# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [2.8.7] (22th January 2025)

### Added
- Add benchmark application.  [#4101]
- Show last typed PIN number for short period of time.  [#3863]
- Add P2WSH support for Unchained BIP32 paths.  [#4271]
- Entropy check workflow in ResetDevice.  [#4155]
- Added support for lexicographic sorting of pubkeys in multisig.  [#4351]

### Changed
- Simplify UI of Cardano transactions initiated by Trezor Suite.  [#4284]
- Included bootloader 2.1.9.
- Improve UI synchronization, ordering, and responsiveness (Global Layout project).  [#2299]
- Improve device responsiveness by removing unnecessary screen refreshes.  [#3633]
- Forbid multisig to singlesig change outputs.  [#4351]
- Forbid per-node paths in multisig change outputs and multisig receive addresses.  [#4351]

### Removed
- Removed deprecated Unchained Capital's multisig path.  [#4351]

### Fixed
- Show account info in ETH send/stake flow.  [#3536]
- Fix ETH account number detection.  [#3627]
- Fix XPUB confirmed success screen title.  [#3947]
- Display menu items on two lines when one line is not enough.  [#4019]
- Fix missing footer page hints in info about remaining shares in super-shamir recovery.  [#4165]
- Fix swipe in ETH stake flow menu and address confirmation.  [#4167]
- New EVM call contract flow UI.  [#4251]
- Add instruction to Swipe up after changing brightness.  [#4261]
- Fix translation of the 'Enable labeling' screen.  [#3813]
- Add swipe back in FIDO confirm flow menu.  [#4176]
- Make swipe back action in tutorial flow menu consistent with menu cancel action.  [#4294]
- Fix color and icon for 'Success' string in `set_brightness` flow.  [#4295]
- Improve paginated blob display.  [#4302]
- Fix incorrect navigation in handy menu while signing BTC message.  [#4309]
- Fix information screen when signing BTC fee bump transaction.  [#4326]
- Fix unexpected info button when confirming passphrase coming from host.  [#4402]
- Fix swiping into empty page.  [#4421]

## [2.8.6] (internal release)

## [2.8.5] (internal release)

## [2.8.4] (internal release)

## [2.8.3] (18th September 2024)

### Added
- Added reassuring screen when entering empty passphrase.  [#4054]
- Reduce the choices to select wordcount when unlocking repeated backup to 20 or 33.  [#4099]

### Changed
- Changed prefix of public key returned by `get_ecdh_session_key` for curve25519.  [#4093]
- Renamed MATIC to POL, following a network upgrade.  [#4151]
- Included bootloader 2.1.8.

### Removed
- Removed `display_random` feature.  [#4119]

### Fixed
- Improved ETH staking flow.
- Redesigned FIDO2 UI.  [#3797]
- Improved ETH send flow.  [#3858]
- Fix persistent word when going to previous word during recovery process.  [#3859]
- Fixed SLIP-10 fingerprints for ed25519 and curve25519.  [#4093]
- Added missing info about remaining shares in super-shamir recovery.  [#4142]

## [2.8.1] (21st August 2024)

### Added
- Added PIN keyboard animation.  [#3885]
- Added menu entry animation.  [#3896]
- Improve precision of PIN timeout countdown.  [#4000]
- New UI of confirming interaction-less firmware update.  [#4030]

### Changed
- Smoothened screen transitions by removing backlight fading.
- Improved resuming of interrupted animations.  [#3987]
- Improve instruction screens during multi-share recovery process.  [#3992]
- Improve share words swiping animation.  [#4063]

### Fixed
- Added a progress indicator for the formatting operation.  [#3035]
- Improved screen brightness settings.  [#3969]
- Improve touch layer precision.  [#3972]
- Fix More info screen during multi-share backup creation.  [#4006]
- Fixed title sometimes not fitting into result screen.  [#4023]
- Adjusted detection of swipes: vertical swipes are preferred over horizontal swipes.  [#4060]
- Solana: added support for deprecated AToken Create `rent_sysvar` argument.  [#3976]


## [2.8.0] (9th July 2024)

### Added
- Animated device label on homescreen/lockscreen.  [#3895]
- Improved change homescreen flow.  [#3907]
- Added word counter during wallet creation.  [#3917]
- Expose value of the Optiga SEC counter in `Features` message.

### Changed
- Reworked PIN processing.

### Removed
- CoSi functionality.  [#3442]

### Fixed
- Fixed swipe back from address QR code screen.  [#3919]
- Fixed device authenticity check.  [#3922]
- Improve swipe behavior and animations.  [#3965]
- Increase Optiga read timeout to avoid spurious RSODs.


## [2.7.2] (14th June 2024)

### Fixed
- Fixed device authenticity check.  [#3922]
- Wrong XPUB screen title.  [#3911]
- Translation fixes.  [#3916]


## [2.7.1] (internal release)

### Added
- Added basic support for STM32U5.  [#3370]
- Cardano: Added support for tagged sets in CBOR (tag 258).  [#3496]
- Cardano: Added support for Conway certificates.  [#3496]
- Added ability to request Shamir backups with any number of groups/shares.  [#3636]
- Added support for repeated backups.  [#3640]
- Support extendable backup flag in SLIP-39.
- User interface implementation.

### Changed
- Cardano: Increased max URL length to 128 bytes.  [#3496]
- Upgrade to bootloader 2.1.6.  [#3855]

### Fixed
- Translate also texts for PIN progress loaders.  [#3520]


## [2.7.0] (20th March 2024)

### Added
- Add translations capability.  [#3206]
- Stellar: add support for `StellarClaimClaimableBalanceOp`.  [#3434]
- Allow for going back to previous word in recovery process.  [#3458]
- Clear sign ETH staking transactions on Everstake pool.  [#3517]
- Send BIP-380 descriptor in GetPublicKey response.  [#3539]

### Changed
- Display descriptors for BTC Taproot public keys.  [#3475]

### Fixed
- Improved UI of multiple Solana instructions.  [#3445]
- Solana multisig instruction warning will be displayed before instruction details are displayed.  [#3445]
- Fixed Solana Memo instruction being unknown - it will now be recognized and displayed properly.  [#3445]


## [2.6.4] (20th December 2023)

### Added
- Added Solana support.  [#3359]

### Changed
- Always display Ethereum fees in Gwei.  [#3246]

### Fixed
- Fix invalid encoding of signatures from Optiga.  [#3411]


## [2.6.3] (15th November 2023)

### Added
- Support interaction-less upgrade.  [#2919]
- Allowed non-zero address index in Cardano staking paths.  [#3242]

### Changed

### Fixed


## [2.6.2] (internal release)

### Added


## [2.6.1] (internal release)

### Added
- QR code display when exporting XPUBs.  [#3047]
- Added hw model field to all vendor headers.  [#3048]
- Added firmware update without interaction.  [#3205]
- Split builds of different parts to use simple util.s assembler, while FW+bootloader use interconnected ones.  [#3205]
- Add support for address chunkification in Receive and Sign flow.  [#3237]

### Changed
- Update to MicroPython 1.19.1.  [#2341]
- Introduce multisig warning to BTC receive flow.  [#2937]
- Introduce multiple account warning to BTC send flow.  [#2937]

### Removed
- MUE coin support.  [#3216]

### Fixed


## [2.6.0] (19th April 2023)

### Added
- Signed Ethereum network and token definitions from host.  [#15]
- CoSi collective signatures on Model T.  [#450]
- Support Ledger Live legacy derivation path `m/44'/coin_type'/0'/account`.  [#1749]
- Updated bootloader to 2.1.0.  [#1901]
- Show source account path in BTC signing.  [#2151]
- Show path for internal outputs in BTC signing.  [#2152]
- Add model info to image and check when installing bootloader, prevent bootloader downgrade.  [#2623]
- Allow proposed Casa m/45' multisig paths for Bitcoin and Ethereum.  [#2682]
- Support for external reward addresses in Cardano CIP-36 registrations.  [#2692]
- Add address confirmation screen to EIP712 signing flow.  [#2818]
- Add the possibility of rebooting the device into bootloader mode.  [#2841]

### Changed
- Switched to redesigned, Rust-based user interface.  [#1922]
- Ignore channel ID in U2F.  [#2205]
- Micropython code optimizations to make the code take less flash space.  [#2525]
- CPU Frequency increased to 180 MHz.  [#2587]
- Fixed display blinking by increasing backlight PWM frequency.  [#2595]
- Updated FAT FS library to R0.15.  [#2611]
- Auto-lock timer is no longer restarted by USB messages, only touch screen activity.  [#2651]
- Updated UI and terminology in Cardano CIP-36 registrations.  [#2692]
- Ethereum's EIP-712 signing no longer restricts the maximum field size to 1024 bytes.  [#2746]
- Force basic attestation in FIDO2 for google.com.  [#2834]

### Fixed
- Enable Trezor to work as a FIDO2 authenticator for Apple.  [#2784]
- Fix RNG for bootloader and make insecure PRNG opt-in, not opt-out.  [#2899]

### Security
- Match and validate script type of change-outputs in Bitcoin signing.


## [2.5.3] (16th November 2022)

### Added
- Optimize touch controller communication.  [#262]
- Add SLIP-0025 CoinJoin accounts.  [#2289]
- Show red error header when USB data pins are not connected.  [#2366]
- Add support for Zcash unified addresses.  [#2398]
- Using hardware acceleration (dma2d) for rendering.  [#2414]
- Add stack overflow detection.  [#2427]
- Show fee rate when replacing transaction.  [#2442]
- Support SetBusy message.  [#2445]
- Add serialize option to SignTx.  [#2507]
- Support for Cardano CIP-36 governance registration format.  [#2561]
- Implement CoinJoin requests.  [#2577]

### Changed
- Extend decimals of fee rate to 2 digits.  [#2486]
- Display only sat instead of sat BTC.  [#2487]
- Remove old BulletProof code from Monero.  [#2570]

### Fixed
- Fix sending XMR transaction to an integrated address.  [#2213]
- Fix XMR primary address display.  [#2453]


## [2.5.2] (17th August 2022)

### Added
- Add model R emulator  [#2230]
- Add support for Monero HF15 features.  [#2232]
- Add basic Trezor Model R hardware support  [#2243]
- Show the fee rate on the signing confirmation screen.  [#2249]
- Jump and stay in bootloader from firmware through SVC call reverse trampoline.  [#2284]
- Expose raw pixel access to Rust  [#2297]
- Add RGB LED for Model R  [#2300]
- Boardloader capabilities structure  [#2324]
- Support for Cardano Babbage era transaction items  [#2354]
- Add "Show All"/"Show Simple" choice to Cardano transaction signing  [#2355]
- Documentation for embedded C+Rust debugging  [#2380]
- Show thousands separator when displaying large amounts.  [#2394]

### Changed
- Refactor and cleanup of Monero code.  [#642]
- Remove power-down power-up cycle from touch controller initialization in firmware  [#2130]
- Updated secp256k1-zkp.  [#2261]
- Cardano internal refactors  [#2313]
- Allow Cardano's `required_signers` in ordinary and multisig transactions
  Allow Cardano's `datum_hash` in non-script outputs  [#2354]

### Removed
- Removed support for obsolete Monero hardfork 12 and below  [#642]
- Remove firmware dumping capability.  [#2433]

### Fixed
- _(Emulator)_ Emulator window will always react to shutdown events, even while waiting for USB packets.  [#973]
- Ensure correct order when verifying external inputs in Bitcoin signing.  [#2415]
- Fix Decred transaction weight calculation.  [#2422]


## 2.5.1 [18th May 2022]

### Added
- Support Bitcoin payment requests.  [#1430]
- Show "signature is valid" dialog when VerifyMessage succeeds.  [#1880]
- Support ownership proofs for Taproot addresses.  [#1944]
- Add extra check for Taproot scripts validity.  [#2077]
- Support Electrum signatures in VerifyMessage.  [#2100]
- Support Cardano Alonzo-era transactions (Plutus).  [#2114]
- Support unverified external inputs.  [#2144]
- Support Zcash version 5 transaction format  [#2166]
- Add firmware hashing functionality.  [#2239]

### Changed
- Ensure input's script type and path match the scriptPubKey.  [#1018]
- Automatically choose best size and encoding for QR codes.  [#1751]
- Bitcoin bech32 addresses are encoded in lower-case for QR codes.  [#1751]
- Full type-checking for Python code (except Monero app).  [#1939]
- \[debuglink] Do not wait for screen refresh when _disabling_ layout watching.  [#2135]

### Removed
- GAME, NIX and POLIS support.  [#2181]

### Fixed
- EIP-1559 transaction correctly show final Hold to Confirm screen.  [#2020]
- Fix sighash computation in proofs of ownership.  [#2034]
- Fix domain-only EIP-712 hashes (i.e. when `primaryType`=`EIP712Domain`).  [#2036]
- Support EIP-712 messages where a struct type is only used as an array element.  [#2167]

### Security
- Fix a coin loss vulnerability related to replacement transactions with multisig inputs and unverified external inputs.

### Incompatible changes
- Trezor will refuse to sign UTXOs that do not match the provided derivation path (e.g., transactions belonging to a different wallet, or synthetic transaction inputs).  [#1018]


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

[#15]: https://github.com/trezor/trezor-firmware/pull/15
[#24]: https://github.com/trezor/trezor-firmware/pull/24
[#262]: https://github.com/trezor/trezor-firmware/pull/262
[#379]: https://github.com/trezor/trezor-firmware/pull/379
[#450]: https://github.com/trezor/trezor-firmware/pull/450
[#642]: https://github.com/trezor/trezor-firmware/pull/642
[#741]: https://github.com/trezor/trezor-firmware/pull/741
[#800]: https://github.com/trezor/trezor-firmware/pull/800
[#948]: https://github.com/trezor/trezor-firmware/pull/948
[#958]: https://github.com/trezor/trezor-firmware/pull/958
[#973]: https://github.com/trezor/trezor-firmware/pull/973
[#982]: https://github.com/trezor/trezor-firmware/pull/982
[#1018]: https://github.com/trezor/trezor-firmware/pull/1018
[#1027]: https://github.com/trezor/trezor-firmware/pull/1027
[#1030]: https://github.com/trezor/trezor-firmware/pull/1030
[#1042]: https://github.com/trezor/trezor-firmware/pull/1042
[#1049]: https://github.com/trezor/trezor-firmware/pull/1049
[#1052]: https://github.com/trezor/trezor-firmware/pull/1052
[#1053]: https://github.com/trezor/trezor-firmware/pull/1053
[#1056]: https://github.com/trezor/trezor-firmware/pull/1056
[#1067]: https://github.com/trezor/trezor-firmware/pull/1067
[#1074]: https://github.com/trezor/trezor-firmware/pull/1074
[#1087]: https://github.com/trezor/trezor-firmware/pull/1087
[#1089]: https://github.com/trezor/trezor-firmware/pull/1089
[#1095]: https://github.com/trezor/trezor-firmware/pull/1095
[#1098]: https://github.com/trezor/trezor-firmware/pull/1098
[#1105]: https://github.com/trezor/trezor-firmware/pull/1105
[#1115]: https://github.com/trezor/trezor-firmware/pull/1115
[#1118]: https://github.com/trezor/trezor-firmware/pull/1118
[#1126]: https://github.com/trezor/trezor-firmware/pull/1126
[#1133]: https://github.com/trezor/trezor-firmware/pull/1133
[#1139]: https://github.com/trezor/trezor-firmware/pull/1139
[#1159]: https://github.com/trezor/trezor-firmware/pull/1159
[#1163]: https://github.com/trezor/trezor-firmware/pull/1163
[#1165]: https://github.com/trezor/trezor-firmware/pull/1165
[#1167]: https://github.com/trezor/trezor-firmware/pull/1167
[#1173]: https://github.com/trezor/trezor-firmware/pull/1173
[#1184]: https://github.com/trezor/trezor-firmware/pull/1184
[#1188]: https://github.com/trezor/trezor-firmware/pull/1188
[#1190]: https://github.com/trezor/trezor-firmware/pull/1190
[#1193]: https://github.com/trezor/trezor-firmware/pull/1193
[#1206]: https://github.com/trezor/trezor-firmware/pull/1206
[#1231]: https://github.com/trezor/trezor-firmware/pull/1231
[#1246]: https://github.com/trezor/trezor-firmware/pull/1246
[#1249]: https://github.com/trezor/trezor-firmware/pull/1249
[#1271]: https://github.com/trezor/trezor-firmware/pull/1271
[#1292]: https://github.com/trezor/trezor-firmware/pull/1292
[#1322]: https://github.com/trezor/trezor-firmware/pull/1322
[#1335]: https://github.com/trezor/trezor-firmware/pull/1335
[#1351]: https://github.com/trezor/trezor-firmware/pull/1351
[#1363]: https://github.com/trezor/trezor-firmware/pull/1363
[#1369]: https://github.com/trezor/trezor-firmware/pull/1369
[#1384]: https://github.com/trezor/trezor-firmware/pull/1384
[#1399]: https://github.com/trezor/trezor-firmware/pull/1399
[#1402]: https://github.com/trezor/trezor-firmware/pull/1402
[#1404]: https://github.com/trezor/trezor-firmware/pull/1404
[#1415]: https://github.com/trezor/trezor-firmware/pull/1415
[#1430]: https://github.com/trezor/trezor-firmware/pull/1430
[#1431]: https://github.com/trezor/trezor-firmware/pull/1431
[#1456]: https://github.com/trezor/trezor-firmware/pull/1456
[#1467]: https://github.com/trezor/trezor-firmware/pull/1467
[#1491]: https://github.com/trezor/trezor-firmware/pull/1491
[#1502]: https://github.com/trezor/trezor-firmware/pull/1502
[#1510]: https://github.com/trezor/trezor-firmware/pull/1510
[#1518]: https://github.com/trezor/trezor-firmware/pull/1518
[#1538]: https://github.com/trezor/trezor-firmware/pull/1538
[#1540]: https://github.com/trezor/trezor-firmware/pull/1540
[#1541]: https://github.com/trezor/trezor-firmware/pull/1541
[#1545]: https://github.com/trezor/trezor-firmware/pull/1545
[#1554]: https://github.com/trezor/trezor-firmware/pull/1554
[#1557]: https://github.com/trezor/trezor-firmware/pull/1557
[#1565]: https://github.com/trezor/trezor-firmware/pull/1565
[#1581]: https://github.com/trezor/trezor-firmware/pull/1581
[#1586]: https://github.com/trezor/trezor-firmware/pull/1586
[#1604]: https://github.com/trezor/trezor-firmware/pull/1604
[#1606]: https://github.com/trezor/trezor-firmware/pull/1606
[#1620]: https://github.com/trezor/trezor-firmware/pull/1620
[#1633]: https://github.com/trezor/trezor-firmware/pull/1633
[#1639]: https://github.com/trezor/trezor-firmware/pull/1639
[#1642]: https://github.com/trezor/trezor-firmware/pull/1642
[#1647]: https://github.com/trezor/trezor-firmware/pull/1647
[#1650]: https://github.com/trezor/trezor-firmware/pull/1650
[#1656]: https://github.com/trezor/trezor-firmware/pull/1656
[#1658]: https://github.com/trezor/trezor-firmware/pull/1658
[#1659]: https://github.com/trezor/trezor-firmware/pull/1659
[#1671]: https://github.com/trezor/trezor-firmware/pull/1671
[#1672]: https://github.com/trezor/trezor-firmware/pull/1672
[#1678]: https://github.com/trezor/trezor-firmware/pull/1678
[#1683]: https://github.com/trezor/trezor-firmware/pull/1683
[#1704]: https://github.com/trezor/trezor-firmware/pull/1704
[#1705]: https://github.com/trezor/trezor-firmware/pull/1705
[#1707]: https://github.com/trezor/trezor-firmware/pull/1707
[#1708]: https://github.com/trezor/trezor-firmware/pull/1708
[#1710]: https://github.com/trezor/trezor-firmware/pull/1710
[#1744]: https://github.com/trezor/trezor-firmware/pull/1744
[#1749]: https://github.com/trezor/trezor-firmware/pull/1749
[#1751]: https://github.com/trezor/trezor-firmware/pull/1751
[#1755]: https://github.com/trezor/trezor-firmware/pull/1755
[#1765]: https://github.com/trezor/trezor-firmware/pull/1765
[#1767]: https://github.com/trezor/trezor-firmware/pull/1767
[#1771]: https://github.com/trezor/trezor-firmware/pull/1771
[#1772]: https://github.com/trezor/trezor-firmware/pull/1772
[#1783]: https://github.com/trezor/trezor-firmware/pull/1783
[#1789]: https://github.com/trezor/trezor-firmware/pull/1789
[#1794]: https://github.com/trezor/trezor-firmware/pull/1794
[#1811]: https://github.com/trezor/trezor-firmware/pull/1811
[#1819]: https://github.com/trezor/trezor-firmware/pull/1819
[#1835]: https://github.com/trezor/trezor-firmware/pull/1835
[#1838]: https://github.com/trezor/trezor-firmware/pull/1838
[#1857]: https://github.com/trezor/trezor-firmware/pull/1857
[#1872]: https://github.com/trezor/trezor-firmware/pull/1872
[#1880]: https://github.com/trezor/trezor-firmware/pull/1880
[#1901]: https://github.com/trezor/trezor-firmware/pull/1901
[#1922]: https://github.com/trezor/trezor-firmware/pull/1922
[#1939]: https://github.com/trezor/trezor-firmware/pull/1939
[#1944]: https://github.com/trezor/trezor-firmware/pull/1944
[#2020]: https://github.com/trezor/trezor-firmware/pull/2020
[#2034]: https://github.com/trezor/trezor-firmware/pull/2034
[#2036]: https://github.com/trezor/trezor-firmware/pull/2036
[#2077]: https://github.com/trezor/trezor-firmware/pull/2077
[#2100]: https://github.com/trezor/trezor-firmware/pull/2100
[#2114]: https://github.com/trezor/trezor-firmware/pull/2114
[#2130]: https://github.com/trezor/trezor-firmware/pull/2130
[#2135]: https://github.com/trezor/trezor-firmware/pull/2135
[#2144]: https://github.com/trezor/trezor-firmware/pull/2144
[#2151]: https://github.com/trezor/trezor-firmware/pull/2151
[#2152]: https://github.com/trezor/trezor-firmware/pull/2152
[#2161]: https://github.com/trezor/trezor-firmware/pull/2161
[#2166]: https://github.com/trezor/trezor-firmware/pull/2166
[#2167]: https://github.com/trezor/trezor-firmware/pull/2167
[#2181]: https://github.com/trezor/trezor-firmware/pull/2181
[#2205]: https://github.com/trezor/trezor-firmware/pull/2205
[#2213]: https://github.com/trezor/trezor-firmware/pull/2213
[#2230]: https://github.com/trezor/trezor-firmware/pull/2230
[#2232]: https://github.com/trezor/trezor-firmware/pull/2232
[#2239]: https://github.com/trezor/trezor-firmware/pull/2239
[#2243]: https://github.com/trezor/trezor-firmware/pull/2243
[#2249]: https://github.com/trezor/trezor-firmware/pull/2249
[#2261]: https://github.com/trezor/trezor-firmware/pull/2261
[#2284]: https://github.com/trezor/trezor-firmware/pull/2284
[#2289]: https://github.com/trezor/trezor-firmware/pull/2289
[#2297]: https://github.com/trezor/trezor-firmware/pull/2297
[#2299]: https://github.com/trezor/trezor-firmware/pull/2299
[#2300]: https://github.com/trezor/trezor-firmware/pull/2300
[#2313]: https://github.com/trezor/trezor-firmware/pull/2313
[#2324]: https://github.com/trezor/trezor-firmware/pull/2324
[#2341]: https://github.com/trezor/trezor-firmware/pull/2341
[#2354]: https://github.com/trezor/trezor-firmware/pull/2354
[#2355]: https://github.com/trezor/trezor-firmware/pull/2355
[#2366]: https://github.com/trezor/trezor-firmware/pull/2366
[#2380]: https://github.com/trezor/trezor-firmware/pull/2380
[#2394]: https://github.com/trezor/trezor-firmware/pull/2394
[#2398]: https://github.com/trezor/trezor-firmware/pull/2398
[#2414]: https://github.com/trezor/trezor-firmware/pull/2414
[#2415]: https://github.com/trezor/trezor-firmware/pull/2415
[#2422]: https://github.com/trezor/trezor-firmware/pull/2422
[#2427]: https://github.com/trezor/trezor-firmware/pull/2427
[#2433]: https://github.com/trezor/trezor-firmware/pull/2433
[#2442]: https://github.com/trezor/trezor-firmware/pull/2442
[#2445]: https://github.com/trezor/trezor-firmware/pull/2445
[#2453]: https://github.com/trezor/trezor-firmware/pull/2453
[#2486]: https://github.com/trezor/trezor-firmware/pull/2486
[#2487]: https://github.com/trezor/trezor-firmware/pull/2487
[#2507]: https://github.com/trezor/trezor-firmware/pull/2507
[#2525]: https://github.com/trezor/trezor-firmware/pull/2525
[#2561]: https://github.com/trezor/trezor-firmware/pull/2561
[#2570]: https://github.com/trezor/trezor-firmware/pull/2570
[#2577]: https://github.com/trezor/trezor-firmware/pull/2577
[#2587]: https://github.com/trezor/trezor-firmware/pull/2587
[#2595]: https://github.com/trezor/trezor-firmware/pull/2595
[#2610]: https://github.com/trezor/trezor-firmware/pull/2610
[#2611]: https://github.com/trezor/trezor-firmware/pull/2611
[#2623]: https://github.com/trezor/trezor-firmware/pull/2623
[#2651]: https://github.com/trezor/trezor-firmware/pull/2651
[#2682]: https://github.com/trezor/trezor-firmware/pull/2682
[#2692]: https://github.com/trezor/trezor-firmware/pull/2692
[#2746]: https://github.com/trezor/trezor-firmware/pull/2746
[#2784]: https://github.com/trezor/trezor-firmware/pull/2784
[#2818]: https://github.com/trezor/trezor-firmware/pull/2818
[#2834]: https://github.com/trezor/trezor-firmware/pull/2834
[#2841]: https://github.com/trezor/trezor-firmware/pull/2841
[#2888]: https://github.com/trezor/trezor-firmware/pull/2888
[#2899]: https://github.com/trezor/trezor-firmware/pull/2899
[#2919]: https://github.com/trezor/trezor-firmware/pull/2919
[#2937]: https://github.com/trezor/trezor-firmware/pull/2937
[#2955]: https://github.com/trezor/trezor-firmware/pull/2955
[#2989]: https://github.com/trezor/trezor-firmware/pull/2989
[#3035]: https://github.com/trezor/trezor-firmware/pull/3035
[#3047]: https://github.com/trezor/trezor-firmware/pull/3047
[#3048]: https://github.com/trezor/trezor-firmware/pull/3048
[#3205]: https://github.com/trezor/trezor-firmware/pull/3205
[#3206]: https://github.com/trezor/trezor-firmware/pull/3206
[#3208]: https://github.com/trezor/trezor-firmware/pull/3208
[#3216]: https://github.com/trezor/trezor-firmware/pull/3216
[#3218]: https://github.com/trezor/trezor-firmware/pull/3218
[#3237]: https://github.com/trezor/trezor-firmware/pull/3237
[#3242]: https://github.com/trezor/trezor-firmware/pull/3242
[#3244]: https://github.com/trezor/trezor-firmware/pull/3244
[#3246]: https://github.com/trezor/trezor-firmware/pull/3246
[#3255]: https://github.com/trezor/trezor-firmware/pull/3255
[#3256]: https://github.com/trezor/trezor-firmware/pull/3256
[#3296]: https://github.com/trezor/trezor-firmware/pull/3296
[#3311]: https://github.com/trezor/trezor-firmware/pull/3311
[#3359]: https://github.com/trezor/trezor-firmware/pull/3359
[#3370]: https://github.com/trezor/trezor-firmware/pull/3370
[#3377]: https://github.com/trezor/trezor-firmware/pull/3377
[#3411]: https://github.com/trezor/trezor-firmware/pull/3411
[#3424]: https://github.com/trezor/trezor-firmware/pull/3424
[#3434]: https://github.com/trezor/trezor-firmware/pull/3434
[#3440]: https://github.com/trezor/trezor-firmware/pull/3440
[#3442]: https://github.com/trezor/trezor-firmware/pull/3442
[#3445]: https://github.com/trezor/trezor-firmware/pull/3445
[#3458]: https://github.com/trezor/trezor-firmware/pull/3458
[#3475]: https://github.com/trezor/trezor-firmware/pull/3475
[#3477]: https://github.com/trezor/trezor-firmware/pull/3477
[#3496]: https://github.com/trezor/trezor-firmware/pull/3496
[#3517]: https://github.com/trezor/trezor-firmware/pull/3517
[#3520]: https://github.com/trezor/trezor-firmware/pull/3520
[#3536]: https://github.com/trezor/trezor-firmware/pull/3536
[#3539]: https://github.com/trezor/trezor-firmware/pull/3539
[#3627]: https://github.com/trezor/trezor-firmware/pull/3627
[#3633]: https://github.com/trezor/trezor-firmware/pull/3633
[#3636]: https://github.com/trezor/trezor-firmware/pull/3636
[#3640]: https://github.com/trezor/trezor-firmware/pull/3640
[#3692]: https://github.com/trezor/trezor-firmware/pull/3692
[#3728]: https://github.com/trezor/trezor-firmware/pull/3728
[#3797]: https://github.com/trezor/trezor-firmware/pull/3797
[#3813]: https://github.com/trezor/trezor-firmware/pull/3813
[#3855]: https://github.com/trezor/trezor-firmware/pull/3855
[#3858]: https://github.com/trezor/trezor-firmware/pull/3858
[#3859]: https://github.com/trezor/trezor-firmware/pull/3859
[#3863]: https://github.com/trezor/trezor-firmware/pull/3863
[#3885]: https://github.com/trezor/trezor-firmware/pull/3885
[#3895]: https://github.com/trezor/trezor-firmware/pull/3895
[#3896]: https://github.com/trezor/trezor-firmware/pull/3896
[#3907]: https://github.com/trezor/trezor-firmware/pull/3907
[#3911]: https://github.com/trezor/trezor-firmware/pull/3911
[#3916]: https://github.com/trezor/trezor-firmware/pull/3916
[#3917]: https://github.com/trezor/trezor-firmware/pull/3917
[#3919]: https://github.com/trezor/trezor-firmware/pull/3919
[#3922]: https://github.com/trezor/trezor-firmware/pull/3922
[#3925]: https://github.com/trezor/trezor-firmware/pull/3925
[#3940]: https://github.com/trezor/trezor-firmware/pull/3940
[#3947]: https://github.com/trezor/trezor-firmware/pull/3947
[#3965]: https://github.com/trezor/trezor-firmware/pull/3965
[#3969]: https://github.com/trezor/trezor-firmware/pull/3969
[#3972]: https://github.com/trezor/trezor-firmware/pull/3972
[#3976]: https://github.com/trezor/trezor-firmware/pull/3976
[#3987]: https://github.com/trezor/trezor-firmware/pull/3987
[#3990]: https://github.com/trezor/trezor-firmware/pull/3990
[#3992]: https://github.com/trezor/trezor-firmware/pull/3992
[#4000]: https://github.com/trezor/trezor-firmware/pull/4000
[#4006]: https://github.com/trezor/trezor-firmware/pull/4006
[#4019]: https://github.com/trezor/trezor-firmware/pull/4019
[#4023]: https://github.com/trezor/trezor-firmware/pull/4023
[#4030]: https://github.com/trezor/trezor-firmware/pull/4030
[#4041]: https://github.com/trezor/trezor-firmware/pull/4041
[#4047]: https://github.com/trezor/trezor-firmware/pull/4047
[#4054]: https://github.com/trezor/trezor-firmware/pull/4054
[#4060]: https://github.com/trezor/trezor-firmware/pull/4060
[#4063]: https://github.com/trezor/trezor-firmware/pull/4063
[#4093]: https://github.com/trezor/trezor-firmware/pull/4093
[#4099]: https://github.com/trezor/trezor-firmware/pull/4099
[#4101]: https://github.com/trezor/trezor-firmware/pull/4101
[#4119]: https://github.com/trezor/trezor-firmware/pull/4119
[#4142]: https://github.com/trezor/trezor-firmware/pull/4142
[#4151]: https://github.com/trezor/trezor-firmware/pull/4151
[#4155]: https://github.com/trezor/trezor-firmware/pull/4155
[#4161]: https://github.com/trezor/trezor-firmware/pull/4161
[#4165]: https://github.com/trezor/trezor-firmware/pull/4165
[#4167]: https://github.com/trezor/trezor-firmware/pull/4167
[#4176]: https://github.com/trezor/trezor-firmware/pull/4176
[#4251]: https://github.com/trezor/trezor-firmware/pull/4251
[#4261]: https://github.com/trezor/trezor-firmware/pull/4261
[#4271]: https://github.com/trezor/trezor-firmware/pull/4271
[#4284]: https://github.com/trezor/trezor-firmware/pull/4284
[#4294]: https://github.com/trezor/trezor-firmware/pull/4294
[#4295]: https://github.com/trezor/trezor-firmware/pull/4295
[#4302]: https://github.com/trezor/trezor-firmware/pull/4302
[#4309]: https://github.com/trezor/trezor-firmware/pull/4309
[#4326]: https://github.com/trezor/trezor-firmware/pull/4326
[#4351]: https://github.com/trezor/trezor-firmware/pull/4351
[#4402]: https://github.com/trezor/trezor-firmware/pull/4402
[#4421]: https://github.com/trezor/trezor-firmware/pull/4421
[#4462]: https://github.com/trezor/trezor-firmware/pull/4462
