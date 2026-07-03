# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [2.12.2] (22nd July 2026)

### Added
- Ethereum: Improved clear signing support.  [#6733]
- Tron: Claim voting rewards.  [#7101]

### Fixed
- Solana: Allow chunkified addresses.  [#3446]
- Avoid failing backup flow on I/O errors.  [#6348]
- Return an explicit error when try to derive seed on Bitcoin-only firmware.  [#6941]
- Solana: Show program id instead of 'unsupported program' label.  [#7065]

### Security
- Ask user for confirmation of some previously hidden Solana instruction parameters.
- Solana: Fixed token transfer recipient for ALT addresses.
- Fix external input misidentification in bitcoin signing.
- Reject new external outputs in bitcoin replacement transactions.

## [2.12.1] (17th June 2026)

### Added
- Added support for `AccountDelete` transaction in Ripple.  [#6370]
- Support for Solana off-chain message signing (OCMS) v0.  [#6759]

### Changed
- Solana System Program's Transfer instruction now allows multisig.  [#6843]

### Fixed
- Improved Tron TRX transfer flow.  [#6520]
- Improve Stellar confirmations flows.  [#6709]

## [2.12.0] (21st May 2026)

### Added
- Added UI flows for some ERC-4626 vault interactions.  [#6435]

### Changed
- Improved EVM address chunking.  [#6601]

### Fixed
- Updated translations in Cardano flow.  [#5723]
- Re-introduced initial blob confirmation layout for Ethereum.  [#6597]
- Fixed out-of-memory failure when confirming large input data.  [#6780]

### Security
- Cached confirmed EIP-712 domain.
- Fixed Solana ALT recipient account parsing.
- Fixed bug in Solana account type identification.

## [2.11.1] (22nd April 2026)

### Added
- Add clear signing support for select swap functions from Uniswap.  [#69]
- Support receive-side THP ACK piggybacking.  [#6202]
- Support WebAuthn credentials' pagination.  [#6349]
- Added support for `VoteWitnessContract` in Tron.  [#6524]

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
- Added version build number to Features message.  [#6225]

### Fixed
- Allow loading translations with different BUILD_VERSION.  [#6228]
- Fixed address chunkification in certain cases.  [#6279]

### Security
- Fixed side-channel vulnerability in BIP-39 mnemonic processing.

## [2.9.6] (internal release)

### Fixed
- Fixed Stellar Amount and Bitcoin lock time font.  [#6109]

## [2.9.5] (internal release)

### Fixed
- Fixed tamper RSOD not showing.  [#6165]

## [2.9.4] (19th November 2025)

### Added
- Show an explicit warning when `ButtonRequest` ACK is delayed.  [#5884]
- Show warning on Ripple destination tag missing.  [#5931]

### Changed
- Deprecate ETH Holesky testnet and use Hoodi testnet instead.  [#5942]

### Fixed
- Fix false "NO USB CONNECTION" warning on the home screen.  [#5980]
- Restart bluetooth on reboot from device menu.  [#6023]
- Removed warning screen for some non-ERC20 contract calls.  [#6032]
- Removed "More info" menu item from screens that don't have more info.  [#6053]

## [2.9.3] (internal release)

### Fixed
- Fix incorrect chunkified address rendering.  [#5882]

## [2.9.2] (internal release)

### Added
- Add dependency check between the PIN and the wipe code.  [#4446]
- Generation of SLIP-21 node for a new way of storing labels (using Evolu).  [#5220]

### Fixed
- Don't allocate tracebacks in optimized builds.  [#5526]
- Allow backup check only when the backup exists.  [#5763]

## [2.9.1] (17th September 2025)

### Added
- Cardano: Add support for signing arbitrary messages.  [#3509]
- Added SLIP-24 swaps.  [#4951]
- Add support for displaying the message hash when signing Ethereum EIP-712 typed data.  [#5344]

### Changed
- Change Unicode normalization from NFKC to NFC.  [#5106]
- Allow using Ethereum mainnet addresses on all non-Ethereum networks. This enables access to networks like Hyperliquid that use conflicting chain IDs and cannot obtain official SLIP-44 registration.  [#5134]
- Improved Stellar transaction signing interface for a more streamlined user experience.  [#5148]
- Implement multi-item menus for Solana staking.  [#5189]
- Limit swipe detection to the component's bounds.  [#5314]
- Make space between value and unit non-breakable.  [#5464]

### Fixed
- Add optional value parameter in brightness setting flow.  [#4410]
- Fix Solana signing crash.  [#5308]
- Show homescreen after updating translations.  [#5316]
- Fixed Solana signature failure.  [#5369]

## [2.9.0] (16th July 2025)

### Added
- Homescreen picture can now be uploaded using a stream instead of single protobuf message.  [#1120]
- Ethereum "approve" flow.  [#4542]
- Added new translation blob format to support larger fonts.  [#4975]

### Changed
- Migrate storage to version 6.  [#4747]
- Changed unknown contract address warning screen.  [#5045]

### Removed
- Remove BNB Beacon Chain support.  [#4227]
- Remove Turkish language support.  [#5108]

### Fixed
- Fixed tutorial-related translations.  [#3821]
- Fix horizontal scroll of the title when setting Wipe code.  [#4750]
- Don't confirm known Solana tokens' details.  [#5043]
- Fix screen title when confirming installation.  [#5057]
- Delay "enter passphrase on host" dialog.  [#5114]

## [2.8.10] (21st May 2025)

### Added
- Add Nostr support (in debug mode only!).  [#4160]
- Solana: rent fee calculation  [#4933]
- Solana: loadable token definitions  [#3541]

### Fixed
- Replaced "next page" icon with "..." ellipsis when confirming long message.  [#4623]
- Fixed Solana staking dialog title.  [#4787]
- Updated EIP-1559 fee-related labels.  [#4819]
- Allow firmware upgrade even if language change failed.  [#4827]
- Solana: fees calculation is now exact  [#4965]

## [2.8.9] (19th March 2025)

### Added
- Ability to cancel recovery on word count selection screen.  [#3503]
- New UI for confirming long messages.  [#4541]
- Solana staking confirmation dialogs.  [#4560]

### Fixed
- Cancelling device recovery after aborting from Suite.  [#3503]

## [2.8.8] (internal release)

### Fixed
- Fix "PIN attempts exceeded" screen.  [#3324]

## [2.8.7] (22nd January 2025)

### Added
- Add benchmark application.  [#4101]
- Show last typed PIN number for short period of time.  [#3863]
- Add P2WSH support for Unchained BIP32 paths.  [#4271]
- Entropy check workflow in ResetDevice.  [#4155]
- Added support for lexicographic sorting of pubkeys in multisig.  [#4351]

### Changed
- Simplify UI of Cardano transactions initiated by Trezor Suite.  [#4284]
- Included bootloader 2.1.8.
- Improve UI synchronization, ordering, and responsiveness (Global Layout project).  [#2299]
- Improve device responsiveness by removing unnecessary screen refreshes.  [#3633]
- Forbid multisig to singlesig change outputs.  [#4351]
- Forbid per-node paths in multisig change outputs and multisig receive addresses.  [#4351]

### Removed
- Removed deprecated Unchained Capital's multisig path.  [#4351]

### Fixed
- Fix ETH account number detection.  [#3627]
- New EVM call contract flow UI.  [#4251]
- Fix translation of the 'Enable labeling' screen.  [#3813]
- Improve paginated blob display.  [#4302]
- UI: Fix auto-mover hitting wall scenario.  [#3692]

## [2.8.6] (internal release)

## [2.8.5] (internal release)

## [2.8.4] (internal release)

## [2.8.3] (18th September 2024)

### Added
- Reduce the choices to select wordcount when unlocking repeated backup to 20 or 33.  [#4099]

### Changed
- Changed prefix of public key returned by `get_ecdh_session_key` for curve25519.  [#4093]
- Renamed MATIC to POL, following a network upgrade.  [#4151]

### Removed
- Removed `display_random` feature.  [#4119]

### Fixed
- Fix persistent word when going to previous word during recovery process.  [#3859]
- Fix display orientation _south_.  [#3990]
- Fixed SLIP-10 fingerprints for ed25519 and curve25519.  [#4093]

## [2.8.1] (21st August 2024)

### Added
- Improve precision of PIN timeout countdown.  [#4000]

### Fixed
- Solana: added support for deprecated AToken Create `rent_sysvar` argument.  [#3976]

## [2.8.0] (9th July 2024)

### Added
- Expose value of the Optiga SEC counter in `Features` message.

### Changed
- Reworked PIN processing.

### Removed
- CoSi functionality.  [#3442]

### Fixed
- Increase Optiga read timeout to avoid spurious RSODs.


## [2.7.2] (14th June 2024)

### Fixed
- Fixed device freeze after setup.  [#3925]
- Translation fixes.  [#3916]


## [2.7.1] (internal release)

### Added
- Added basic support for STM32U5.  [#3370]
- Cardano: Added support for tagged sets in CBOR (tag 258).  [#3496]
- Cardano: Added support for Conway certificates.  [#3496]
- Added ability to request Shamir backups with any number of groups/shares.  [#3636]
- Added support for repeated backups.  [#3640]
- Support extendable backup flag in SLIP-39.

### Changed
- Cardano: Increased max URL length to 128 bytes.  [#3496]

### Fixed
- Translate also texts for PIN progress loaders.  [#3520]


## [2.7.0] (20th March 2024)

### Added
- Add translations capability.  [#3206]
- Stellar: add support for `StellarClaimClaimableBalanceOp`.  [#3434]
- Add loader to homescreen when locking the device.  [#3440]
- Allow for going back to previous word in recovery process.  [#3458]
- Clear sign ETH staking transactions on Everstake pool.  [#3517]
- Send BIP-380 descriptor in GetPublicKey response.  [#3539]

### Changed
- Display descriptors for BTC Taproot public keys.  [#3475]

### Fixed
- Improved UI of multiple Solana instructions.  [#3445]
- Solana multisig instruction warning will be displayed before instruction details are displayed.  [#3445]
- Fixed Solana Memo instruction being unknown - it will now be recognized and displayed properly.  [#3445]
- Add missing semicolon character to the passphrase entry.  [#3477]


## [2.6.4] (20th December 2023)

### Added
- Added Solana support.  [#3359]

### Changed
- Always display Ethereum fees in Gwei.  [#3246]

### Fixed
- Fix invalid encoding of signatures from Optiga.  [#3411]
- Re-added missing address confirmation screens.  [#3424]


## [2.6.3] (15th November 2023)

### Added
- Support interaction-less upgrade.  [#2919]
- Allowed non-zero address index in Cardano staking paths.  [#3242]
- Turn the screen off when device is locked, to prolong OLED life.  [#3377]


[#69]: https://github.com/trezor/trezor-firmware/pull/69
[#1120]: https://github.com/trezor/trezor-firmware/pull/1120
[#2299]: https://github.com/trezor/trezor-firmware/pull/2299
[#2919]: https://github.com/trezor/trezor-firmware/pull/2919
[#3206]: https://github.com/trezor/trezor-firmware/pull/3206
[#3242]: https://github.com/trezor/trezor-firmware/pull/3242
[#3246]: https://github.com/trezor/trezor-firmware/pull/3246
[#3324]: https://github.com/trezor/trezor-firmware/pull/3324
[#3359]: https://github.com/trezor/trezor-firmware/pull/3359
[#3370]: https://github.com/trezor/trezor-firmware/pull/3370
[#3377]: https://github.com/trezor/trezor-firmware/pull/3377
[#3411]: https://github.com/trezor/trezor-firmware/pull/3411
[#3424]: https://github.com/trezor/trezor-firmware/pull/3424
[#3434]: https://github.com/trezor/trezor-firmware/pull/3434
[#3440]: https://github.com/trezor/trezor-firmware/pull/3440
[#3442]: https://github.com/trezor/trezor-firmware/pull/3442
[#3445]: https://github.com/trezor/trezor-firmware/pull/3445
[#3446]: https://github.com/trezor/trezor-firmware/pull/3446
[#3458]: https://github.com/trezor/trezor-firmware/pull/3458
[#3475]: https://github.com/trezor/trezor-firmware/pull/3475
[#3477]: https://github.com/trezor/trezor-firmware/pull/3477
[#3496]: https://github.com/trezor/trezor-firmware/pull/3496
[#3503]: https://github.com/trezor/trezor-firmware/pull/3503
[#3509]: https://github.com/trezor/trezor-firmware/pull/3509
[#3517]: https://github.com/trezor/trezor-firmware/pull/3517
[#3520]: https://github.com/trezor/trezor-firmware/pull/3520
[#3539]: https://github.com/trezor/trezor-firmware/pull/3539
[#3541]: https://github.com/trezor/trezor-firmware/pull/3541
[#3627]: https://github.com/trezor/trezor-firmware/pull/3627
[#3633]: https://github.com/trezor/trezor-firmware/pull/3633
[#3636]: https://github.com/trezor/trezor-firmware/pull/3636
[#3640]: https://github.com/trezor/trezor-firmware/pull/3640
[#3692]: https://github.com/trezor/trezor-firmware/pull/3692
[#3813]: https://github.com/trezor/trezor-firmware/pull/3813
[#3821]: https://github.com/trezor/trezor-firmware/pull/3821
[#3859]: https://github.com/trezor/trezor-firmware/pull/3859
[#3863]: https://github.com/trezor/trezor-firmware/pull/3863
[#3916]: https://github.com/trezor/trezor-firmware/pull/3916
[#3925]: https://github.com/trezor/trezor-firmware/pull/3925
[#3976]: https://github.com/trezor/trezor-firmware/pull/3976
[#3990]: https://github.com/trezor/trezor-firmware/pull/3990
[#4000]: https://github.com/trezor/trezor-firmware/pull/4000
[#4093]: https://github.com/trezor/trezor-firmware/pull/4093
[#4099]: https://github.com/trezor/trezor-firmware/pull/4099
[#4101]: https://github.com/trezor/trezor-firmware/pull/4101
[#4119]: https://github.com/trezor/trezor-firmware/pull/4119
[#4151]: https://github.com/trezor/trezor-firmware/pull/4151
[#4155]: https://github.com/trezor/trezor-firmware/pull/4155
[#4160]: https://github.com/trezor/trezor-firmware/pull/4160
[#4227]: https://github.com/trezor/trezor-firmware/pull/4227
[#4251]: https://github.com/trezor/trezor-firmware/pull/4251
[#4271]: https://github.com/trezor/trezor-firmware/pull/4271
[#4284]: https://github.com/trezor/trezor-firmware/pull/4284
[#4302]: https://github.com/trezor/trezor-firmware/pull/4302
[#4351]: https://github.com/trezor/trezor-firmware/pull/4351
[#4410]: https://github.com/trezor/trezor-firmware/pull/4410
[#4446]: https://github.com/trezor/trezor-firmware/pull/4446
[#4541]: https://github.com/trezor/trezor-firmware/pull/4541
[#4542]: https://github.com/trezor/trezor-firmware/pull/4542
[#4560]: https://github.com/trezor/trezor-firmware/pull/4560
[#4623]: https://github.com/trezor/trezor-firmware/pull/4623
[#4747]: https://github.com/trezor/trezor-firmware/pull/4747
[#4750]: https://github.com/trezor/trezor-firmware/pull/4750
[#4787]: https://github.com/trezor/trezor-firmware/pull/4787
[#4819]: https://github.com/trezor/trezor-firmware/pull/4819
[#4827]: https://github.com/trezor/trezor-firmware/pull/4827
[#4933]: https://github.com/trezor/trezor-firmware/pull/4933
[#4951]: https://github.com/trezor/trezor-firmware/pull/4951
[#4965]: https://github.com/trezor/trezor-firmware/pull/4965
[#4975]: https://github.com/trezor/trezor-firmware/pull/4975
[#5043]: https://github.com/trezor/trezor-firmware/pull/5043
[#5045]: https://github.com/trezor/trezor-firmware/pull/5045
[#5057]: https://github.com/trezor/trezor-firmware/pull/5057
[#5106]: https://github.com/trezor/trezor-firmware/pull/5106
[#5108]: https://github.com/trezor/trezor-firmware/pull/5108
[#5114]: https://github.com/trezor/trezor-firmware/pull/5114
[#5134]: https://github.com/trezor/trezor-firmware/pull/5134
[#5148]: https://github.com/trezor/trezor-firmware/pull/5148
[#5189]: https://github.com/trezor/trezor-firmware/pull/5189
[#5220]: https://github.com/trezor/trezor-firmware/pull/5220
[#5308]: https://github.com/trezor/trezor-firmware/pull/5308
[#5314]: https://github.com/trezor/trezor-firmware/pull/5314
[#5316]: https://github.com/trezor/trezor-firmware/pull/5316
[#5344]: https://github.com/trezor/trezor-firmware/pull/5344
[#5358]: https://github.com/trezor/trezor-firmware/pull/5358
[#5369]: https://github.com/trezor/trezor-firmware/pull/5369
[#5464]: https://github.com/trezor/trezor-firmware/pull/5464
[#5526]: https://github.com/trezor/trezor-firmware/pull/5526
[#5723]: https://github.com/trezor/trezor-firmware/pull/5723
[#5763]: https://github.com/trezor/trezor-firmware/pull/5763
[#5882]: https://github.com/trezor/trezor-firmware/pull/5882
[#5884]: https://github.com/trezor/trezor-firmware/pull/5884
[#5931]: https://github.com/trezor/trezor-firmware/pull/5931
[#5942]: https://github.com/trezor/trezor-firmware/pull/5942
[#5980]: https://github.com/trezor/trezor-firmware/pull/5980
[#6023]: https://github.com/trezor/trezor-firmware/pull/6023
[#6032]: https://github.com/trezor/trezor-firmware/pull/6032
[#6048]: https://github.com/trezor/trezor-firmware/pull/6048
[#6053]: https://github.com/trezor/trezor-firmware/pull/6053
[#6103]: https://github.com/trezor/trezor-firmware/pull/6103
[#6109]: https://github.com/trezor/trezor-firmware/pull/6109
[#6165]: https://github.com/trezor/trezor-firmware/pull/6165
[#6202]: https://github.com/trezor/trezor-firmware/pull/6202
[#6211]: https://github.com/trezor/trezor-firmware/pull/6211
[#6225]: https://github.com/trezor/trezor-firmware/pull/6225
[#6228]: https://github.com/trezor/trezor-firmware/pull/6228
[#6247]: https://github.com/trezor/trezor-firmware/pull/6247
[#6279]: https://github.com/trezor/trezor-firmware/pull/6279
[#6321]: https://github.com/trezor/trezor-firmware/pull/6321
[#6349]: https://github.com/trezor/trezor-firmware/pull/6349
[#6358]: https://github.com/trezor/trezor-firmware/pull/6358
[#6370]: https://github.com/trezor/trezor-firmware/pull/6370
[#6394]: https://github.com/trezor/trezor-firmware/pull/6394
[#6435]: https://github.com/trezor/trezor-firmware/pull/6435
[#6448]: https://github.com/trezor/trezor-firmware/pull/6448
[#6483]: https://github.com/trezor/trezor-firmware/pull/6483
[#6520]: https://github.com/trezor/trezor-firmware/pull/6520
[#6524]: https://github.com/trezor/trezor-firmware/pull/6524
[#6597]: https://github.com/trezor/trezor-firmware/pull/6597
[#6601]: https://github.com/trezor/trezor-firmware/pull/6601
[#6709]: https://github.com/trezor/trezor-firmware/pull/6709
[#6710]: https://github.com/trezor/trezor-firmware/pull/6710
[#6733]: https://github.com/trezor/trezor-firmware/pull/6733
[#6759]: https://github.com/trezor/trezor-firmware/pull/6759
[#6780]: https://github.com/trezor/trezor-firmware/pull/6780
[#6843]: https://github.com/trezor/trezor-firmware/pull/6843
[#6900]: https://github.com/trezor/trezor-firmware/pull/6900
[#6941]: https://github.com/trezor/trezor-firmware/pull/6941
[#6984]: https://github.com/trezor/trezor-firmware/pull/6984
[#7065]: https://github.com/trezor/trezor-firmware/pull/7065
[#7101]: https://github.com/trezor/trezor-firmware/pull/7101
[#7202]: https://github.com/trezor/trezor-firmware/pull/7202
