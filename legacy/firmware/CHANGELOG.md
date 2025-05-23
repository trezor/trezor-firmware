# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## 1.13.1 [21st May 2025]

### Added
- Clear sign ETH staking transactions on Everstake pool.  [#4851]
- Entropy check workflow in ResetDevice.

### Fixed
- Use `GWei` when formatting large ETH amounts.  [#4932]

## 1.13.0 [19th February 2025]

### Added
- Signed Ethereum network and token definitions from host.  [#15]
- Unchained paths for p2wsh multisig.  [#4324]
- Added support for lexicographic sorting of pubkeys in multisig.  [#4396]

### Changed
- Changed prefix of public key returned by `get_ecdh_session_key` for curve25519.  [#4093]
- Remove deprecated Unchained Capital's multisig path.  [#4396]
- Forbid per-node paths in multisig change outputs and multisig receive addresses.  [#4396]
- Forbid multisig to singlesig change outputs.  [#4396]
- Reworked PIN processing.  [#3949]

### Removed
- CoSi functionality.  [#2675]
- MUE support.  [#3216]
- Removed display_random feature.  [#4119]

### Fixed
- Allow showing XPUB using a QR code.  [#3043]
- Stellar: resolves the issue of incorrect signature generation when the transaction source account differs from the signing account.  [#3691]
- Fixed SLIP-10 fingerprints for ed25519 and curve25519.  [#4093]

## 1.12.1 [15th March 2023]

### Added
- Support Ledger Live legacy derivation path `m/44'/coin_type'/0'/account`.  [#1749]
- Show fee rate when replacing transaction.  [#2442]
- T1 bootloader: verify firmware signatures based on SignMessage, add signature debugging.  [#2568]
- Allow proposed Casa m/45' multisig paths for Bitcoin and Ethereum.  [#2682]
- Implement SLIP-0025 coinjoin accounts.  [#2718]
- Implement `serialize` option in SignTx.  [#2718]
- Support native SegWit external inputs with non-ownership proof.  [#2718]
- Implement SLIP-0019 proofs of ownership for native SegWit.  [#2718]
- Implement coinjoin signing.  [#2718]

### Changed
- Do not convert bech32 addresses to uppercase in QR code to increase compatibility.  [#2190]
- Extend decimals of fee rate to 2 digits.  [#2486]
- Display only sat instead of sat BTC.  [#2487]
- Increase `SignIdentity.challenge_hidden` max_size to 512 bytes.  [#2743]
- Included bootloader 1.12.1.

### Fixed
- Bootloader VTOR and FW handover fix.
- Show full Stellar address and QR code.  [#1453]
- Wrap long Ethereum fee to next line if it does not fit.  [#2373]

### Security
- Match and validate script type of change-outputs in Bitcoin signing.


## 1.11.2 [17th August 2022]

### Added
- Show the fee rate on the signing confirmation screen.  [#2249]
- Show thousands separator when displaying large amounts.  [#2394]

### Changed
- Updated secp256k1-zkp.  [#2261]

### Removed
- Remove firmware dumping capability.  [#2433]

### Security
- Fix potential security issues in recovery workflow.
- Fix key extraction vulnerability in Cothority Collective Signing (CoSi).
- Fix nonce bias in CoSi signing.


## 1.11.1 [18th May 2022]

### Added
- Show "signature is valid" dialog when VerifyMessage succeeds.  [#1880]
- Add extra check for Taproot scripts validity.  [#2077]
- Support Electrum signatures in VerifyMessage.  [#2100]
- \[emulator] Added support for `DebugLinkReseedRandom`.  [#2115]
- Support unverified external inputs.  [#2144]
- Support Zcash version 5 transaction format.  [#2031]
- Add firmware hashing functionality.  [#2239]

### Changed
- Ensure input's script type and path match the scriptPubKey.  [#1018]
- Included bootloader 1.11.0.

### Removed
- \[emulator] Removed support for /dev/urandom or custom entropy source.  [#2115]
- GAME, NIX and POLIS support.  [#2181]

### Fixed
- Fix domain-only EIP-712 hashes (i.e. when `primaryType`=`EIP712Domain`).  [#2036]
- Fix legacy technical debt in USB handling (readability and FSM unwanted states).  [#2107]

### Security
- Strict path validations for altcoins.
- Fix soft-lock bypass vulnerability.
- Make Bitcoin path checks as strict as in Trezor T.

### Incompatible changes
- Trezor will refuse to sign UTXOs that do not match the provided derivation path (e.g., transactions belonging to a different wallet, or synthetic transaction inputs).  [#1018]


## 1.10.5 [19th January 2022]

### Added
- Support for blindly signing EIP-712 data.  [#131]

### Fixed
- Prevent recursing in handling RebootToBootloader by USB flush.  [#1985]


## 1.10.4 [8th December 2021]

### Added
- Support no_script_type option in SignMessage.  [#1586]
- Implement pagination in SignMessage and VerifyMessage.  [#1586]
- Show address confirmation in SignMessage.  [#1586]
- Support GetAddress for Taproot addresses.  [#1656]
- Support sending to Taproot addresses.  [#1656]
- Support spending from Taproot UTXOs.  [#1656]
- Support for Taproot descriptors.  [#1710]
- Ethereum: support 64-bit chain IDs.  [#1771]
- Support for Ethereum EIP-1559 transactions.  [#1834]
- Stellar: add support for StellarManageBuyOfferOp and StellarPathPaymentStrictSendOp.  [#1838]
- Add script_pubkey field to TxInput message.  [#1857]
- Support of BIP-340 Schnorr signatures (using secp256k1-zkp).  [#1897]

### Changed
- Update QR-code-generator library version.  [#1639]
- Show warning dialog in SignMessage if a non-standard path is used.  [#1656]
- Disable previous transaction streaming in Bitcoin if all internal inputs are Taproot.  [#1656]
- Faster ECDSA signing and verification (using secp256k1-zkp).  [#1897]

### Removed
- Remove BELL, ZNY support.  [#1872]

### Fixed
- Remove rest of altcoin logic from bitcoin-only build.  [#1633]
- Fix incorrect compile-time check of maximum protobuf message size.  [#1854]

### Security
- Ensure that the user is always warned about non-standard paths.
- Avoid accidental build with broken stack protector.  [#1642]

### Incompatible changes
- Timebounds must be set for a Stellar transaction.  [#1755]
- Ethereum non-EIP-155 cross-chain signing is no longer supported.  [#1794]
- Stellar: rename StellarManageOfferOp to StellarManageSellOfferOp, StellarPathPaymentOp to StellarPathPaymentStrictReceiveOp and StellarCreatePassiveOfferOp to StellarCreatePassiveSellOfferOp.  [#1838]


## 1.10.3 [16th September 2021]

### Added
- Re-enabled Firo support  [#1767]

### Changed
- Emulator properly waits for IO without busy loop  [#1743]

### Removed
- Removed support for Lisk  [#1765]

### Fixed
- Add new rpId to Binance's FIDO definition.  [#1705]

### Security
- Stricter protobuf field handling in Stellar.


## 1.10.2 [14th July 2021]

### Removed
- Removed support for Firo  [#1647]
- Removed support for Hatch  [#1650]

### Fixed
- Allow non-standard paths used by Unchained Capital, Green Address and Casa.  [#1660]

### Security
- Ensure that all testnet coins use SLIP-44 coin type 1.
- Restrict BIP-45 paths to Bitcoin and coins with strong replay protection.
- Don't show addresses that have an unrecognized path.
- Disable all testnet coins from accessing Bitcoin paths.
- Restrict the BIP-32 path ranges of `account`, `change` and `address_index` fields.
- Fix operation source account encoding in Stellar.


## 1.10.1 [9th June 2021]

### Added
- Safety checks setting in T1.  [#1627]

### Security
- Fix incorrect empty string handling in BLAKE implementation used by Decred.


## 1.10.0 [12th May 2021]

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

[#15]: https://github.com/trezor/trezor-firmware/pull/15
[#131]: https://github.com/trezor/trezor-firmware/pull/131
[#965]: https://github.com/trezor/trezor-firmware/pull/965
[#1018]: https://github.com/trezor/trezor-firmware/pull/1018
[#1030]: https://github.com/trezor/trezor-firmware/pull/1030
[#1098]: https://github.com/trezor/trezor-firmware/pull/1098
[#1105]: https://github.com/trezor/trezor-firmware/pull/1105
[#1165]: https://github.com/trezor/trezor-firmware/pull/1165
[#1167]: https://github.com/trezor/trezor-firmware/pull/1167
[#1188]: https://github.com/trezor/trezor-firmware/pull/1188
[#1351]: https://github.com/trezor/trezor-firmware/pull/1351
[#1363]: https://github.com/trezor/trezor-firmware/pull/1363
[#1367]: https://github.com/trezor/trezor-firmware/pull/1367
[#1369]: https://github.com/trezor/trezor-firmware/pull/1369
[#1402]: https://github.com/trezor/trezor-firmware/pull/1402
[#1415]: https://github.com/trezor/trezor-firmware/pull/1415
[#1453]: https://github.com/trezor/trezor-firmware/pull/1453
[#1461]: https://github.com/trezor/trezor-firmware/pull/1461
[#1491]: https://github.com/trezor/trezor-firmware/pull/1491
[#1518]: https://github.com/trezor/trezor-firmware/pull/1518
[#1549]: https://github.com/trezor/trezor-firmware/pull/1549
[#1586]: https://github.com/trezor/trezor-firmware/pull/1586
[#1627]: https://github.com/trezor/trezor-firmware/pull/1627
[#1633]: https://github.com/trezor/trezor-firmware/pull/1633
[#1639]: https://github.com/trezor/trezor-firmware/pull/1639
[#1642]: https://github.com/trezor/trezor-firmware/pull/1642
[#1647]: https://github.com/trezor/trezor-firmware/pull/1647
[#1650]: https://github.com/trezor/trezor-firmware/pull/1650
[#1656]: https://github.com/trezor/trezor-firmware/pull/1656
[#1660]: https://github.com/trezor/trezor-firmware/pull/1660
[#1705]: https://github.com/trezor/trezor-firmware/pull/1705
[#1710]: https://github.com/trezor/trezor-firmware/pull/1710
[#1743]: https://github.com/trezor/trezor-firmware/pull/1743
[#1749]: https://github.com/trezor/trezor-firmware/pull/1749
[#1755]: https://github.com/trezor/trezor-firmware/pull/1755
[#1765]: https://github.com/trezor/trezor-firmware/pull/1765
[#1767]: https://github.com/trezor/trezor-firmware/pull/1767
[#1771]: https://github.com/trezor/trezor-firmware/pull/1771
[#1794]: https://github.com/trezor/trezor-firmware/pull/1794
[#1834]: https://github.com/trezor/trezor-firmware/pull/1834
[#1838]: https://github.com/trezor/trezor-firmware/pull/1838
[#1854]: https://github.com/trezor/trezor-firmware/pull/1854
[#1857]: https://github.com/trezor/trezor-firmware/pull/1857
[#1872]: https://github.com/trezor/trezor-firmware/pull/1872
[#1880]: https://github.com/trezor/trezor-firmware/pull/1880
[#1897]: https://github.com/trezor/trezor-firmware/pull/1897
[#1985]: https://github.com/trezor/trezor-firmware/pull/1985
[#2031]: https://github.com/trezor/trezor-firmware/pull/2031
[#2036]: https://github.com/trezor/trezor-firmware/pull/2036
[#2077]: https://github.com/trezor/trezor-firmware/pull/2077
[#2100]: https://github.com/trezor/trezor-firmware/pull/2100
[#2107]: https://github.com/trezor/trezor-firmware/pull/2107
[#2115]: https://github.com/trezor/trezor-firmware/pull/2115
[#2144]: https://github.com/trezor/trezor-firmware/pull/2144
[#2181]: https://github.com/trezor/trezor-firmware/pull/2181
[#2190]: https://github.com/trezor/trezor-firmware/pull/2190
[#2239]: https://github.com/trezor/trezor-firmware/pull/2239
[#2249]: https://github.com/trezor/trezor-firmware/pull/2249
[#2261]: https://github.com/trezor/trezor-firmware/pull/2261
[#2289]: https://github.com/trezor/trezor-firmware/pull/2289
[#2373]: https://github.com/trezor/trezor-firmware/pull/2373
[#2394]: https://github.com/trezor/trezor-firmware/pull/2394
[#2422]: https://github.com/trezor/trezor-firmware/pull/2422
[#2433]: https://github.com/trezor/trezor-firmware/pull/2433
[#2442]: https://github.com/trezor/trezor-firmware/pull/2442
[#2486]: https://github.com/trezor/trezor-firmware/pull/2486
[#2487]: https://github.com/trezor/trezor-firmware/pull/2487
[#2568]: https://github.com/trezor/trezor-firmware/pull/2568
[#2675]: https://github.com/trezor/trezor-firmware/pull/2675
[#2682]: https://github.com/trezor/trezor-firmware/pull/2682
[#2718]: https://github.com/trezor/trezor-firmware/pull/2718
[#2743]: https://github.com/trezor/trezor-firmware/pull/2743
[#3043]: https://github.com/trezor/trezor-firmware/pull/3043
[#3216]: https://github.com/trezor/trezor-firmware/pull/3216
[#3691]: https://github.com/trezor/trezor-firmware/pull/3691
[#3949]: https://github.com/trezor/trezor-firmware/pull/3949
[#4093]: https://github.com/trezor/trezor-firmware/pull/4093
[#4119]: https://github.com/trezor/trezor-firmware/pull/4119
[#4324]: https://github.com/trezor/trezor-firmware/pull/4324
[#4396]: https://github.com/trezor/trezor-firmware/pull/4396
[#4851]: https://github.com/trezor/trezor-firmware/pull/4851
[#4932]: https://github.com/trezor/trezor-firmware/pull/4932
