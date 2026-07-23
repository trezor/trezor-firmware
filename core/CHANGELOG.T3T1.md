# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [2.12.3] (24th July 2026)

### Fixed
- Fixed a crash during PIN verification when upgrading from firmware versions older than 2.9.0.  [#7354]

## [2.12.2] (22nd July 2026)

### Added
- Ethereum: Improved clear signing support.  [#6733]
- Tron: Claim voting rewards.  [#7101]

### Fixed
- Solana: allow chunkified addresses.  [#3446]
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
- Hide written characters in passphrase keyboard.  [#6342]
- Improved Tron TRX transfer flow.  [#6520]
- Improve Stellar confirmations flows.  [#6709]

### Security
- Fix device locking if only SD card protection is enabled.

## [2.12.0] (21st May 2026)

### Added
- Added UI flows for some ERC-4626 vault interactions.  [#6435]
- Introduced font kerning.  [#6620]

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
- Fixed touch issue causing stuck hold-to-confirm buttons.  [#6075]

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
- Provider contract address in ETH approve.  [#5139]
- Add support for displaying the message hash when signing Ethereum EIP-712 typed data.  [#5344]

### Changed
- Change Unicode normalization from NFKC to NFC.  [#5106]
- Allow using Ethereum mainnet addresses on all non-Ethereum networks. This enables access to networks like Hyperliquid that use conflicting chain IDs and cannot obtain official SLIP-44 registration.  [#5134]
- Improved Stellar transaction signing interface for a more streamlined user experience.  [#5148]
- Limit swipe detection to the component's bounds.  [#5314]
- Make space between value and unit non-breakable.  [#5464]

### Fixed
- Add optional value parameter in brightness setting flow.  [#4410]
- Fix Solana signing crash.  [#5308]
- Show homescreen after updating translations.  [#5316]
- Do not hide the shown PIN until the touch is released.  [#5317]
- Fixed Solana signature failure.  [#5369]
- Fix crash on first boot.  [#5378]
- Fix incomplete disabling of haptics.  [#5532]

## [2.9.0] (16th July 2025)

### Added
- Homescreen picture can now be uploaded using a stream instead of single protobuf message.  [#1120]
- Ethereum "approve" flow.  [#4542]
- Added new translation blob format to support larger fonts.  [#4975]

### Changed
- Migrate storage to version 6.  [#4747]
- Change multiple accounts warning to danger.  [#5218]

### Removed
- Remove BNB Beacon Chain support.  [#4227]
- Remove Turkish language support.  [#5108]
- Don't enter/exit menu via horizontal swipe.  [#5189]

### Fixed
- Show confirmation layout after sending address, public key or signature to host.  [#3666]
- Fixed tutorial-related translations.  [#3821]
- Not being able to tap to continue in request number dialog.  [#4751]
- Don't confirm known Solana tokens' details.  [#5043]
- Incorrect number of shares input.  [#5099]
- Delay "enter passphrase on host" dialog.  [#5114]

## [2.8.10] (21st May 2025)

### Added
- Add Nostr support (in debug mode only!).  [#4160]
- Visual cues to distinguish unlocked state on Homescreen.  [#4964]
- Solana: rent fee calculation  [#4933]
- Solana: loadable token definitions  [#3541]

### Fixed
- Replaced "next page" icon with "..." ellipsis when confirming long message.  [#4623]
- Updated EIP-1559 fee-related labels.  [#4819]
- Allow firmware upgrade even if language change failed.  [#4827]
- Solana: fees calculation is now exact  [#4965]

## [2.8.9] (19th March 2025)

### Added
- Ability to cancel recovery on word count selection screen.  [#3503]
- New UI for confirming long messages.  [#4541]
- Solana staking confirmation dialogs.  [#4560]
- Upgrade bundled bootloader to 2.1.10.  [#4665]

### Changed
- Changed "swipe to continue" to "tap to continue". Screens still respond to swipe-up, but the preferred interaction method is now tapping the lower part of the screen.  [#4571]

### Fixed
- Cancelling device recovery after aborting from Suite.  [#3503]

## [2.8.8] (internal release)

### Fixed
- Fixed flashing old content when fading.  [#4492]

## [2.8.7] (22nd January 2025)

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

[#69]: https://github.com/trezor/trezor-firmware/pull/69
[#1120]: https://github.com/trezor/trezor-firmware/pull/1120
[#2299]: https://github.com/trezor/trezor-firmware/pull/2299
[#3035]: https://github.com/trezor/trezor-firmware/pull/3035
[#3442]: https://github.com/trezor/trezor-firmware/pull/3442
[#3445]: https://github.com/trezor/trezor-firmware/pull/3445
[#3446]: https://github.com/trezor/trezor-firmware/pull/3446
[#3458]: https://github.com/trezor/trezor-firmware/pull/3458
[#3475]: https://github.com/trezor/trezor-firmware/pull/3475
[#3477]: https://github.com/trezor/trezor-firmware/pull/3477
[#3496]: https://github.com/trezor/trezor-firmware/pull/3496
[#3503]: https://github.com/trezor/trezor-firmware/pull/3503
[#3509]: https://github.com/trezor/trezor-firmware/pull/3509
[#3536]: https://github.com/trezor/trezor-firmware/pull/3536
[#3541]: https://github.com/trezor/trezor-firmware/pull/3541
[#3627]: https://github.com/trezor/trezor-firmware/pull/3627
[#3633]: https://github.com/trezor/trezor-firmware/pull/3633
[#3666]: https://github.com/trezor/trezor-firmware/pull/3666
[#3797]: https://github.com/trezor/trezor-firmware/pull/3797
[#3813]: https://github.com/trezor/trezor-firmware/pull/3813
[#3821]: https://github.com/trezor/trezor-firmware/pull/3821
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
[#3947]: https://github.com/trezor/trezor-firmware/pull/3947
[#3965]: https://github.com/trezor/trezor-firmware/pull/3965
[#3969]: https://github.com/trezor/trezor-firmware/pull/3969
[#3972]: https://github.com/trezor/trezor-firmware/pull/3972
[#3976]: https://github.com/trezor/trezor-firmware/pull/3976
[#3987]: https://github.com/trezor/trezor-firmware/pull/3987
[#3992]: https://github.com/trezor/trezor-firmware/pull/3992
[#4000]: https://github.com/trezor/trezor-firmware/pull/4000
[#4006]: https://github.com/trezor/trezor-firmware/pull/4006
[#4019]: https://github.com/trezor/trezor-firmware/pull/4019
[#4023]: https://github.com/trezor/trezor-firmware/pull/4023
[#4030]: https://github.com/trezor/trezor-firmware/pull/4030
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
[#4160]: https://github.com/trezor/trezor-firmware/pull/4160
[#4165]: https://github.com/trezor/trezor-firmware/pull/4165
[#4167]: https://github.com/trezor/trezor-firmware/pull/4167
[#4176]: https://github.com/trezor/trezor-firmware/pull/4176
[#4227]: https://github.com/trezor/trezor-firmware/pull/4227
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
[#4410]: https://github.com/trezor/trezor-firmware/pull/4410
[#4421]: https://github.com/trezor/trezor-firmware/pull/4421
[#4446]: https://github.com/trezor/trezor-firmware/pull/4446
[#4492]: https://github.com/trezor/trezor-firmware/pull/4492
[#4541]: https://github.com/trezor/trezor-firmware/pull/4541
[#4542]: https://github.com/trezor/trezor-firmware/pull/4542
[#4560]: https://github.com/trezor/trezor-firmware/pull/4560
[#4571]: https://github.com/trezor/trezor-firmware/pull/4571
[#4623]: https://github.com/trezor/trezor-firmware/pull/4623
[#4665]: https://github.com/trezor/trezor-firmware/pull/4665
[#4747]: https://github.com/trezor/trezor-firmware/pull/4747
[#4751]: https://github.com/trezor/trezor-firmware/pull/4751
[#4819]: https://github.com/trezor/trezor-firmware/pull/4819
[#4827]: https://github.com/trezor/trezor-firmware/pull/4827
[#4933]: https://github.com/trezor/trezor-firmware/pull/4933
[#4951]: https://github.com/trezor/trezor-firmware/pull/4951
[#4964]: https://github.com/trezor/trezor-firmware/pull/4964
[#4965]: https://github.com/trezor/trezor-firmware/pull/4965
[#4975]: https://github.com/trezor/trezor-firmware/pull/4975
[#5043]: https://github.com/trezor/trezor-firmware/pull/5043
[#5099]: https://github.com/trezor/trezor-firmware/pull/5099
[#5106]: https://github.com/trezor/trezor-firmware/pull/5106
[#5108]: https://github.com/trezor/trezor-firmware/pull/5108
[#5114]: https://github.com/trezor/trezor-firmware/pull/5114
[#5134]: https://github.com/trezor/trezor-firmware/pull/5134
[#5139]: https://github.com/trezor/trezor-firmware/pull/5139
[#5148]: https://github.com/trezor/trezor-firmware/pull/5148
[#5189]: https://github.com/trezor/trezor-firmware/pull/5189
[#5218]: https://github.com/trezor/trezor-firmware/pull/5218
[#5220]: https://github.com/trezor/trezor-firmware/pull/5220
[#5308]: https://github.com/trezor/trezor-firmware/pull/5308
[#5314]: https://github.com/trezor/trezor-firmware/pull/5314
[#5316]: https://github.com/trezor/trezor-firmware/pull/5316
[#5317]: https://github.com/trezor/trezor-firmware/pull/5317
[#5344]: https://github.com/trezor/trezor-firmware/pull/5344
[#5358]: https://github.com/trezor/trezor-firmware/pull/5358
[#5369]: https://github.com/trezor/trezor-firmware/pull/5369
[#5378]: https://github.com/trezor/trezor-firmware/pull/5378
[#5464]: https://github.com/trezor/trezor-firmware/pull/5464
[#5526]: https://github.com/trezor/trezor-firmware/pull/5526
[#5532]: https://github.com/trezor/trezor-firmware/pull/5532
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
[#6075]: https://github.com/trezor/trezor-firmware/pull/6075
[#6103]: https://github.com/trezor/trezor-firmware/pull/6103
[#6109]: https://github.com/trezor/trezor-firmware/pull/6109
[#6165]: https://github.com/trezor/trezor-firmware/pull/6165
[#6202]: https://github.com/trezor/trezor-firmware/pull/6202
[#6211]: https://github.com/trezor/trezor-firmware/pull/6211
[#6225]: https://github.com/trezor/trezor-firmware/pull/6225
[#6228]: https://github.com/trezor/trezor-firmware/pull/6228
[#6247]: https://github.com/trezor/trezor-firmware/pull/6247
[#6321]: https://github.com/trezor/trezor-firmware/pull/6321
[#6342]: https://github.com/trezor/trezor-firmware/pull/6342
[#6348]: https://github.com/trezor/trezor-firmware/pull/6348
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
[#6620]: https://github.com/trezor/trezor-firmware/pull/6620
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
[#7354]: https://github.com/trezor/trezor-firmware/pull/7354
