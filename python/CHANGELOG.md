# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.13.10] (2025-02-12)
[0.13.10]: https://github.com/trezor/trezor-firmware/compare/python/v0.13.9...python/v0.13.10

### Added
- Added support for T3B1.  [#3728]
- Added support for Trezor models not known by the current version of the library.  [#3993]
- Added ability to set Optiga's security event counter to maximum: `trezorctl debug optiga-set-sec-max`.  [#4000]
- Enum for valid device rotations.  [#4041]
- Added pretty-printing of protobuf messages in IPython (`_repr_pretty_`).  [#4076]
- Added support for benchmarks.  [#4101]
- Added support for entropy check workflow in `device.reset()`.  [#4155]
- Added shortcut for loading a debug device with the "academic" SLIP39 seed.  [#4282]
- Added support for lexicographic sorting of pubkeys in multisig.  [#4351]
- Added an `expect` argument to `TrezorClient.call()`, to enforce the returned message type.  [#4464]
- Introduced `device.setup()` as a cleaner upgrade to `device.reset()`.  [#4464]

### Changed
- Most USB level errors are now converted to `TransportException`.  [#4089]

### Deprecated
- `@expect` decorator is deprecated -- use `TrezorClient.call(expect=...)` instead.  [#4464]
- String return values are deprecated in functions where the semantic result is a success (specifically those that were returning the message from Trezor's `Success` response). Type annotations are updated to `str | None`, and in a future release those functions will be returning `None` on success, or raise an exception on a failure.  [#4464]
- `device.reset()` is deprecated, migrate to `device.setup()`.  [#4464]
- Return value of `device.recover()` is deprecated. In the future, this function will return `None`.  [#4464]

### Removed
- CoSi functionality.  [#3442]
- Removed display_random feature.  [#4119]

### Fixed
- It is now possible to interrupt USB communication (via Ctrl+C, or a signal, or any other way).  [#4089]
- Use `frozenset` for `models.TREZORS` to prevent accidental modification.

### Incompatible changes
- Return values in `solana` module were changed from the wrapping protobuf messages to the raw inner values (`str` for address, `bytes` for pubkey / signature).  [#4464]
- `trezorctl device` commands whose default result is a success will not print anything to stdout anymore, in line with Unix philosophy.  [#4464]

## [0.13.9] (2024-06-19)
[0.13.9]: https://github.com/trezor/trezor-firmware/compare/python/v0.13.8...python/v0.13.9

### Added
- trezorctl: Automatically go to bootloader when upgrading firmware.  [#2919]
- Support interaction-less upgrade.  [#2919]
- Added user adjustable brightness setting.  [#3208]
- Added Solana support.  [#3359]
- trezorctl: support for human-friendly Trezor Safe device authenticity check (requires separate installation of `cryptography` library).  [#3364]
- Added support for T3T1.  [#3422]
- Stellar: add support for StellarClaimClaimableBalanceOp.  [#3434]
- Cardano: Added support for tagged sets in CBOR (tag 258).  [#3496]
- Cardano: Added support for Conway certificates.  [#3496]
- Added ability to request Shamir backups with any number of groups/shares.  [#3636]
- Added flag for setting up device using SLIP39 "single".  [#3868]
- Added `--quality` argument to `trezorctl set homescreen`.  [#3893]

### Changed
- Renamed `trezorctl device self-test` command to `trezorctl device prodtest-t1`.  [#3504]
- Increased default JPEG quality for uploaded homescreen.  [#3893]

### Incompatible changes
- Renamed flag used for setting up device using BIP39 to `bip39`.  [#3868]
- Minimum required Python version is now 3.8.


## [0.13.8] (2023-10-19)
[0.13.8]: https://github.com/trezor/trezor-firmware/compare/python/v0.13.7...python/v0.13.8

### Added
- Added full support for Trezor Safe 3 (T2B1).
- Added support for STM32F429I-DISC1 board  [#2989]
- Add support for address chunkification in Receive and Sign flow.  [#3237]
- Implement device authenticate command.  [#3255]
- trezorctl: support unlocking bootloader via `trezorctl device unlock-bootloader`.

### Changed
- Use 'h' character for hardened BIP-32 components in help texts.  [#3037]
- trezorctl: Use 'h' character in generated descriptors.  [#3037]
- ClickUI: notify user in terminal that they should enter PIN or passphrase on Trezor.  [#3203]
- Internal names are used consistently in constants and names. Original model-based names are kept as aliases for backwards compatibility.
- Trezor model detection will try to use the `internal_name` field.

### Fixed
- Drop simple-rlp dependency and use internal copy  [#3045]
- Fixed printing Trezor model when validating firmware image  [#3227]
- Corrected vendor header signing keys for Safe 3 (T2B1).


## [0.13.7] (2023-06-02)
[0.13.7]: https://github.com/trezor/trezor-firmware/compare/python/v0.13.6...python/v0.13.7

### Added
- Recognize signing keys for T2B1.
- Add possibility to call tutorial flow  [#2795]
- Add ability to change homescreen for Model R  [#2967]
- Recognize hw model field in vendor headers.  [#3048]


## [0.13.6] (2023-04-24)
[0.13.6]: https://github.com/trezor/trezor-firmware/compare/python/v0.13.5...python/v0.13.6

### Added
- Signed Ethereum network and token definitions from host  [#15]
- Support SLIP-25 in get-descriptor.  [#2541]
- trezorctl: Support prompt configuration for `encrypt-keyvalue` / `decrypt-keyvalue`.  [#2608]
- Support for external reward addresses in Cardano CIP-36 registrations  [#2692]
- Auto-convert image to Trezor's homescreen format.  [#2880]

### Changed
- `trezorctl firmware verify` changed order of checks - fingerprint is validated before signatures.  [#2745]

### Fixed
- Removed attempt to initialize the device after wipe in bootloader mode  [#2221]
- Limit memory exhaustion in protobuf parser.  [#2439]
- `trezorctl ethereum sign-tx`: renamed `--gas-limit` shortcut to `-G` to avoid collision with `-t/--token`  [#2535]
- Fixed behavior of UDP transport search by path when full path is provided and prefix_search is True  [#2786]
- Fixed behavior of `trezorctl fw` with unsigned Trezor One firmwares.  [#2801]
- Improve typing information when `TrezorClient` has a more intelligent UI object.  [#2832]
- When enabling passphrase force-on-device, do not also prompt to enable passphrase if it is already enabled.  [#2833]


## [0.13.5] (2022-12-28)
[0.13.5]: https://github.com/trezor/trezor-firmware/compare/python/v0.13.4...python/v0.13.5

### Added
- Add support for model field in firmware image.  [#2701]
- Add support for v3-style Trezor One signatures.  [#2701]

### Changed
- More structured information about signing keys for different models.  [#2701]

### Incompatible changes
- Instead of accepting a list of public keys, `FirmwareType.verify()` accepts a parameter configuring whether to use production or development keys.  [#2701]


## [0.13.4] (2022-11-04)
[0.13.4]: https://github.com/trezor/trezor-firmware/compare/python/v0.13.3...python/v0.13.4

### Added
- Add UnlockPath message.  [#2289]
- Added new TOI formats - little endian full-color and even-high grayscale  [#2414]
- Add device set-busy command to trezorctl.  [#2445]
- Support SLIP-25 accounts in get-public-node and get-address.  [#2517]
- Add possibility to save emulator screenshots.  [#2547]
- Support for Cardano CIP-36 governance registration format  [#2561]

### Removed
- Remove DATA parameter from trezorctl cosi commit.
- Remove firmware dumping capability.  [#2433]

### Fixed
- Fixed issue where type declarations were not visible to consumer packages.  [#2542]

### Incompatible changes
- Refactored firmware parsing and validation to a more object oriented approach.  [#2576]


## [0.13.3] (2022-07-13)
[0.13.3]: https://github.com/trezor/trezor-firmware/compare/python/v0.13.2...python/v0.13.3

### Added
- Support for Cardano Babbage era transaction items  [#2354]

### Fixed
- Fix Click 7.x compatibility.  [#2364]


## [0.13.2] (2022-06-30)
[0.13.2]: https://github.com/trezor/trezor-firmware/compare/python/v0.13.1...python/v0.13.2

### Fixed
- Fixed dependency error when running trezorctl without PIL.
- Fixed dependency error when running trezorctl on Python 3.6 without rlp.
- Fix `trezorctl --version` crash.  [#1702]


## [0.13.1] (2022-06-29)
[0.13.1]: https://github.com/trezor/trezor-firmware/compare/python/v0.13.0...python/v0.13.1

### Added
- New exception type `DeviceIsBusy` indicates that the device is in use by another process.  [#1026]
- Support payment requests and GetNonce command.  [#1430]
- Add press_info() to DebugLink.  [#1430]
- Add support for blind EIP-712 signing for Trezor One  [#1970]
- Add ScriptUI for trezorctl, spawned by --script option  [#2023]
- Support T1 screenshot saving in Debuglink  [#2093]
- Support generating Electrum-compatible message signatures in CLI.  [#2100]
- Support Cardano Alonzo-era transaction items and --include-network-id flag  [#2114]
- trezorctl: Bitcoin commands can detect script type from derivation path.  [#2159]
- Add support for model R  [#2230]
- Add firmware get-hash command.  [#2239]
- Jump and stay in bootloader from firmware through SVC call reverse trampoline.  [#2284]

### Changed
- Unify boolean arguments/options in trezorlib commands to on/off  [#2123]
- Rename `normalize_nfc` to `prepare_message_bytes` in tools.py  [#2126]
- `trezorctl monero` network type arguments now accept symbolic names instead of numbers.  [#2219]

### Fixed
- trezorctl will correctly report that device is in use.  [#1026]
- Allow passing empty `message_hash` for domain-only EIP-712 hashes
  for Trezor T1 (i.e. when `primaryType`=`EIP712Domain`)  [#2036]
- Fixed error when printing protobuf message with a missing required field.  [#2135]
- Add compatibility with Click 8.1  [#2199]


## [0.13.0] - 2021-12-09
[0.13.0]: https://github.com/trezor/trezor-firmware/compare/python/v0.12.4...python/v0.13.0

### Added
- `trezorctl firmware update` shows progress bar (Model T only)
- Enabled session management via `EndSession`  [#1227]
- Added parameters to enable Cardano derivation when calling `init_device()`.  [#1231]
- two new trezorctl commands - `trezorctl firmware download` and `trezorctl firmware verify`  [#1258]
- Support no_script_type option in SignMessage.  [#1586]
- Support for Ethereum EIP1559 transactions  [#1604]
- Debuglink can automatically scroll through paginated views.  [#1671]
- Support for Taproot descriptors  [#1710]
- `trezorlib.stellar.from_envelope` was added, it includes support for the Stellar [TransactionV1](https://github.com/stellar/stellar-protocol/blob/master/core/cap-0015.md#xdr) format transaction.  [#1745]
- Ethereum: support 64-bit chain IDs  [#1771]
- Support for Cardano multi-sig transactions, token minting, script addresses, multi-sig keys, minting keys and native script verification  [#1772]
- Added parameters to specify kind of Cardano derivation to all functions and `trezorctl` commands.  [#1783]
- Support for EIP-712 in library and `trezorctl ethereum sign-typed-data`  [#1835]
- Add script_pubkey field to TxInput message.  [#1857]
- Full type hinting checkable with pyright  [#1893]

### Changed
- protobuf is aware of `required` fields and default values  [#379]
- `trezorctl firmware-update` command changed to `trezorctl firmware update`  [#1258]
- `btc.sign_tx()` accepts keyword arguments for transaction metadata  [#1266]
- Raise `ValueError` when the txid for an input is not present in `prev_txes` during `btc.sign_tx`  [#1442]
- `trezorlib.mappings` was refactored for easier customization  [#1449]
- Refactor protobuf codec for better clarity  [#1541]
- `UdpTransport.wait_until_ready` no longer sets socket to nonblocking  [#1668]
- Cardano transaction parameters are now streamed into the device one by one instead of being sent as one large object  [#1683]
- `trezorlib.stellar` will refuse to process transactions containing MuxedAccount  [#1838]
- Use unified descriptors format.  [#1885]
- Introduce Trezor models as an abstraction over USB IDs, vendor strings, and possibly protobuf mappings.  [#1967]

### Deprecated
- instantiating protobuf objects with positional arguments is deprecated  [#379]
- `details` argument to `btc.sign_tx()` is deprecated. Use keyword arguments instead.  [#379]
- values of required fields must be supplied at instantiation time. Omitting them is deprecated.  [#379]

### Removed
- dropped Python 3.5 support  [#810]
- dropped debug-only `trezorctl debug show-text` functionality  [#1531]
- Removed support for Lisk  [#1765]

### Fixed
- fix operator precedence issue for ethereum sign-tx command  [#1867]
- Updated `tools/build_tx.py` to work with Blockbook's API protections.  [#1896]
- Fix PIN and passphrase entry in certain terminals on Windows  [#1959]

### Incompatible changes
- `client.init_device(derive_cardano=True)` must be used before calling Cardano functions.  [#1231]
- The type of argument to `ui.button_request(x)` is changed from int to ButtonRequest.
  The original int value can be accessed as `x.code`  [#1671]
- Due to transaction streaming in Cardano, it isn't possible to return the whole serialized transaction anymore. Instead the transaction hash, transaction witnesses and auxiliary data supplement are returned and the serialized transaction needs to be assembled by the client.  [#1683]
- `trezorlib.stellar` was reworked to use stellar-sdk instead of providing local implementations  [#1745]
- Cardano derivation now defaults to Icarus method. This will result in different keys for users with 24-word seed.  [#1783]


## [0.12.4] - 2021-09-07
[0.12.4]: https://github.com/trezor/trezor-firmware/compare/python/v0.12.3...python/v0.12.4

### Fixed

- trezorctl: fixed "Invalid value for <param>" when using Click 8 and param is not specified [#1798]

## [0.12.3] - 2021-07-29
[0.12.3]: https://github.com/trezor/trezor-firmware/compare/python/v0.12.2...python/v0.12.3

### Added

- `trezorctl btc get-descriptor` support [#1363]
- `trezorctl btc reboot-to-bootloader` support [#1738]
- distinguishing between temporary and permanent safety checks
- trezorctl accepts PIN entered by letters (useful on laptops)
- support for 50-digit PIN for T1

### Changed

- allowed Click 8.x as a requirement
- replaced all references to Trezor Wallet with Trezor Suite, and modified all mentions
  of Beta Wallet

### Fixed

- added missing requirement `attrs`
- properly parse big numbers in `tools/build_tx.py` [#1257], [#1296]
- it is now possible to set safety checks for T1


## [0.12.2] - 2020-08-27
[0.12.2]: https://github.com/trezor/trezor-firmware/compare/python/v0.12.1...python/v0.12.2

### Added

- `trezorlib.toif` module (moved from internal) can encode and decode TOIF image format
- `trezorctl set homescreen` was improved and extended to support PNG images for Trezor T

### Changed

- trezorctl will correctly notify the user if the image decoding library is missing

### Fixed

- fix exception in `trezorctl btc get-address`  [#1179]
- fix exception in `trezorctl lisk sign-message`
- fix exception in trezorctl commands that accept filenames  [#1196]
- fix "Invalid homescreen" error when un-setting homescreen

### Removed

- removed option `--skip-vendor-header` from `trezorctl firmware-update` which did nothing  [#1210]


## [0.12.1] - 2020-08-05
[0.12.1]: https://github.com/trezor/trezor-firmware/compare/python/v0.12.0...python/v0.12.1

### Added

- `trezorctl set safety-checks` controls the new "safety checks" feature.  [#1126]
- `trezorctl btc get-address` can create multisig addresses.
- the following commands are now equivalent in trezorctl: `firmware-update`, `firmware-upgrade`,
  `update-firmware`, `upgrade-firmware`
- support for EXTERNAL input type  [#38], [#1052]
- support for ownership proofs
- support for pre-authorized CoinJoin transactions  [#37]
- support for Cardano Shelley  [#948]

### Changed

- do not allow setting auto-lock delay unless PIN is configured

### Fixed

- correctly calculate hashes for very small firmwares  [f#1082]
- unified file arguments in trezorctl
- `TrezorClient.ping()` does not crash when device is PIN-locked


## [0.12.0] - 2020-04-01
[0.12.0]: https://github.com/trezor/trezor-firmware/compare/python/v0.11.6...python/v0.12.0

### Incompatible changes

- `trezorlib.coins`, `trezorlib.tx_api`, and the file `coins.json`, were removed
- `TrezorClient` argument `ui` is now mandatory. `state` argument was renamed to `session_id`.
- UI callback `get_passphrase()` has a new argument `available_on_device`.
- API for `cosi` module was changed
- other changes may also introduce incompatibilities, please review the full list below

### Added

- support for firmwares 1.9.0 and 2.3.0
- Model T now defaults to entering passphrase on device. New trezorctl option `-P`
  enforces entering passphrase on host.
- support for "passphrase always on device" mode on model T
- new trezorctl command `get-session` and option `-s` allows entering passphrase once
  for multiple subsequent trezorctl operations
- built-in functionality of UdpTransport to wait until an emulator comes up, and the
  related command `trezorctl wait-for-emulator`
- `trezorctl debug send-bytes` can send raw messages to the device [f#116]
- when updating firmware, user is warned that the requested version does not match their device [f#823]
- `trezorctl list` can now show name, model and id of device

### Changed

- `trezorlib.tx_api.json_to_tx` was reduced to only support Bitcoin fields, and moved
  to `trezorlib.btc.from_json`.
- API for `cosi` module was streamlined: `verify_m_of_n` is now `verify`, the old
  `verify` is `verify_combined`
- internals of firmware parsing were reworked to support signing firmware headers
- `get_default_client` respects `TREZOR_PATH` environment variable
- UI callback `get_passphrase` has an additional argument `available_on_device`,
  indicating that the connected Trezor is capable of on-device entry
- `Transport.write` and `read` method signatures changed to accept bytes instead of
  protobuf messages
- trezorctl subcommands have a common `@with_client` decorator that manages exception
  handling and connecting to device

### Fixed

- trezorctl does not print empty line when there is no output
- trezorctl cleanly reports wire exceptions [f#226]

### Removed

- `trezorlib.tx_api` was removed
- `trezorlib.coins` and coin data was removed
- `trezorlib.ckd_public`, which was deprecated in 0.10, was now removed.
- `btc.sign_tx` will not preload transaction data from `prev_txes`, as usage with TxApi
  is being removed
- PIN protection and passphrase protection for `ping()` command was removed
- compatibility no-op code from trezorlib 0.9 was removed from `trezorlib.client`
- `trezorlib.tools.CallException` was dropped, use `trezorlib.exceptions.TrezorFailure` instead


## [0.11.6] - 2019-12-30
[0.11.6]: https://github.com/trezor/trezor-firmware/compare/python/v0.11.5...python/v0.11.6

### Added

- support for get-and-increase FIDO counter operation
- support for setting wipe code
- `trezorctl device recover` supports `--u2f-counter` option to set the FIDO counter to a custom value

### Changed

- `trezorctl` command was reworked for ease of use and maintenance. See `trezorctl --help` and `OPTIONS.rst` for details. [f#510]
- updated EOS transaction parser to match `cleos` in `delegatebw` and `undelegatebw` actions [f#680] [f#681]
- `RecoveryDevice` does not set fields when doing dry-run recovery [f#666]

### Fixed

- fixed "expand words" functionality in `trezorctl device recover` [f#778]

### Removed

- trezorctl no longer interactively signs Bitcoin-like transactions, the only allowed
  input format is JSON. See [`docs/transaction-format.md`](docs/transaction-format.md)
  for details.
- support for "load device by xprv" was removed from firmware and trezorlib


## [0.11.5] - 2019-09-26

[0.11.5]: https://github.com/trezor/trezor-firmware/compare/python/v0.11.4...python/v0.11.5

### Added

- trezorctl can dump raw protobuf bytes in debug output [f#117]
- trezorctl shows a warning when activating Shamir Backup if the device does not support it [f#445]
- warnings are emitted when encountering unknown value for a protobuf enum [f#363]
- debug messages show enum value names instead of raw numbers
- support for packed repeated encoding in the protobuf decoder
- in `trezorctl firmware-update`, the new `--beta` switch enables downloading beta
  firmwares. By default, only stable firmware is used. [f#411], [f#420]
- in `trezorctl firmware-update`, the new `--bitcoin-only` switch enables downloading
  Bitcoin-only firmware
- support for FIDO2 resident credential management
- support for SD-protect features

### Changed

- package directory structure was changed: `src` subdirectory contains sources and
  `tests` subdirectory contains tests, so that cwd is not cluttered
- `trezorctl` script was moved into a module `trezorlib.cli.trezorctl` and is launched
  through the `entry_points` mechanism. This makes it usable on Windows
- `pyblake2` is no longer required on Python 3.6 and up
- input flows can only be used in with-block (only relevant for unit tests)
- if not specified, trezorctl will set label to "SLIP-0014" in SLIP-0014 mode
- in `clear_session` the client also forgets the passphrase state for TT [f#525]

### Fixed

- trezorctl will properly check if a firmware is present on a new T1 [f#224]

### Removed

- device test suite was moved out of trezor package

## [0.11.4] - 2019-07-31

[0.11.4]: https://github.com/trezor/trezor-firmware/compare/python/v0.11.3...python/v0.11.4

### Added

- trezorctl support for SLIP-39 Shamir Backup
- support for Binance Chain

## [0.11.3] - 2019-05-29

[0.11.3]: https://github.com/trezor/trezor-firmware/compare/python/v0.11.2...python/v0.11.3

### Added

- trezorctl can now send ERC20 tokens
- trezorctl usb-reset will perform USB reset on devices in inconsistent state
- set-display-rotation command added for TT firmware 2.1.1
- EOS support [f#87]
- Tezos: add voting support [f#41]
- `dict_to_proto` now allows enum values as strings

### Changed

- Minimum firmware versions bumped to 1.8.0 and 2.1.0
- Cleaner errors when UI object is not supplied
- Generated files are now part of the source tarball again. That means that `protoc` is no longer required.

### Fixed

- Ethereum commands in trezorctl now work
- Memory debugging tools now work again

### Removed

- Tron and Ontology support removed until implementations exist in Trezor firmware

## [0.11.2] - 2019-02-27

[0.11.2]: https://github.com/trezor/python-trezor/compare/v0.11.1...v0.11.2

### Added

- full support for bootloader 1.8.0 and relevant firmware upgrade functionality
- trezorctl: support fully offline signing JSON-encoded transaction data
- trezorctl: dry-run for firmware upgrade command
- client: new convenience function `get_default_client` for simple script usage
- Dash: support DIP-2 special inputs [#351]
- Ethereum: add get_public_key methods

### Changed

- coins with BIP-143 fork id (BCH, BTG) won't require prev_tx [#352]
- device recovery will restore U2F counter
- Cardano: change `network` to `protocol_magic`
- tests can run interactively when `INTERACT=1` environment variable is set
- protobuf: improved `to_dict` function

### Deprecated

- trezorctl: interactive signing with `sign-tx` is considered deprecated

## [0.11.1] - 2018-12-28

[0.11.1]: https://github.com/trezor/python-trezor/compare/v0.11.0...v0.11.1

### Fixed

- crash when entering passphrase on device with Trezor T
- Qt widgets should only import QtCore [#349]

## [0.11.0] - 2018-12-06

[0.11.0]: https://github.com/trezor/python-trezor/compare/v0.10.2...v0.11.0

### Incompatible changes

- removed support for Python 3.3 and 3.4
- major refactor of `TrezorClient` and UI handling. Implementers must now provide a "UI" object instead of overriding callbacks [#307], [#314]
- protobuf classes now use a `get_fields()` method instead of `FIELDS` field [#312]
- all methods on `TrezorClient` class are now in separate modules and take a `TrezorClient` instance as argument [#276]
- mixin classes are also removed, you are not supposed to extend `TrezorClient` anymore
- `TrezorClientDebugLink` was moved to `debuglink` module
- changed signature of `trezorlib.btc.sign_tx`
- `@field` decorator was replaced by an argument to `@expect`

### Added

- trezorlib now has a hardcoded check preventing use of outdated firmware versions [#283]
- Ripple support [#286]
- Zencash support [#287]
- Cardano support [#300]
- Ontology support [#301]
- Tezos support [#302]
- Capricoin support [#325]
- limited Monero support (can only get address/watch key, monerowallet is required for signing)
- support for input flow in tests makes it easier to control complex UI workflows [#314]
- `protobuf.dict_to_proto` can create a protobuf instance from a plain dict
- support for smarter methods in trezord 2.0.25 and up
- support for seedless setup
- trezorctl: firmware handling is greatly improved [#304], [#308]
- trezorctl: Bitcoin-like signing flow is more user-friendly
- `tx_api` now supports Blockbook backend servers

### Changed

- better reporting for debuglink expected messages
- replaced Ed25519 module with a cleaner, optimized version
- further reorganization of transports makes them more robust when dependencies are missing
- codebase now follows [Black](https://github.com/ambv/black) code style
- in Qt modules, Qt5 is imported first [#315]
- `TxApiInsight` is just `TxApi`
- `device.reset` and `device.recover` now have reasonable defaults for all arguments
- protobuf classes are no longer part of the source distribution and must be compiled locally [#284]
- Stellar: addresses are always strings

### Removed

- `set_tx_api` method on `TrezorClient` is replaced by an argument for `sign_tx`
- caching functionality of `TxApi` was moved to a separate test-support class
- Stellar: public key methods removed
- `EncryptMessage` and `DecryptMessage` actions are gone

### Fixed:

- `TrezorClient` can now detect when a HID device is removed and a different one is plugged in on the same path
- trezorctl now works with Click 7.0 and considers "`_`" and "`-`" as same in command names [#314]
- bash completion fixed
- Stellar: several bugs in the XDR parser were fixed

## [0.10.2] - 2018-06-21

[0.10.2]: https://github.com/trezor/python-trezor/compare/v0.10.1...v0.10.2

### Added

- `stellar_get_address` and `_public_key` functions support `show_display` parameter
- trezorctl: `stellar_get_address` and `_public_key` commands for the respective functionality

### Removed

- trezorctl: `list_coins` is removed because we no longer parse the relevant protobuf field
  (and newer Trezor firmwares don't send it) [#277]

### Fixed

- test support module was not included in the release, so code relying on the deprecated `ckd_public` module would fail [#280]

## [0.10.1] - 2018-06-11

[0.10.1]: https://github.com/trezor/python-trezor/compare/v0.10.0...v0.10.1

### Fixed

- previous release fails to build on Windows [#274]

## [0.10.0] - 2018-06-08

[0.10.0]: https://github.com/trezor/python-trezor/compare/v0.9.1...v0.10.0

### Added

- Lisk support [#197]
- Stellar support [#167], [#268]
- Wanchain support [#230]
- support for "auto lock delay" feature
- `TrezorClient` takes an additional argument `state` that allows reusing the previously entered passphrase [#241]
- USB transports mention udev rules in exception messages [#245]
- `log.enable_debug_output` function turns on wire logging, instead of having to use `TrezorClientVerbose`
- BIP32 paths now support `123h` in addition to `123'` to indicate hardening
- trezorctl: `-p` now supports prefix search for device path [#226]
- trezorctl: smarter handling of firmware updates [#242], [#269]

### Changed

- reorganized transports and moved into their own `transport` submodule
- protobuf messages and coins info is now regenerated at build time from the `trezor-common` repository [#248]
- renamed `ed25519raw` to `_ed25519` to indicate its privateness
- renamed `ed25519cosi` to `cosi` and expanded its API
- protobuf messages are now logged through Python's `logging` facility instead of custom printing through `VerboseWireMixin`
- `client.format_protobuf` is moved to `protobuf.format_message`
- `tools.Hash` is renamed to `tools.btc_hash`
- `coins` module `coins_txapi` is renamed to `tx_api`.
  `coins_slip44` is renamed to `slip44`.
- build: stricter flake8 checks
- build: split requirements to separate files
- tests: unified finding test device, while respecting `TREZOR_PATH` env variable.
- tests: auto-skip appropriately marked tests based on Trezor device version
- tests: only show wire output when run with `-v`
- tests: allow running `xfail`ed tests selectively based on `pytest.ini`
- docs: updated README with clearer install instructions [#185]
- docs: switched changelog to Keep a Changelog format [#94]

### Deprecated

- `ckd_public` is only maintained in `tests.support` submodule and considered private
- `TrezorClient.expand_path` is moved to plain function `tools.parse_path`
- `TrezorDevice` is deprecated in favor of `transport.enumerate_devices` and `transport.get_transport`
- XPUB-related handling in `tools` is slated for removal

### Removed

- most Python 2 compatibility constructs are gone [#229]
- `TrezorClientVerbose` and `VerboseWireMixin` is removed
- specific `tx_api.TxApi*` classes removed in favor of `coins.tx_api`
- `client.PRIME_DERIVATION_FLAG` is removed in favor of `tools.HARDENED_FLAG` and `tools.H_()`
- hard dependency on Ethereum libraries and HIDAPI is changed into extras that need to be
  specified explicitly. Require `trezor[hidapi]` or `trezor[ethereum]` to get them.

### Fixed

- WebUSB enumeration returning bad devices on Windows 10 [#223]
- `sign_tx` operation sending empty address string [#237]
- Wrongly formatted Ethereum signatures [#236]
- protobuf layer would wrongly encode signed integers [#249], [#250]
- protobuf pretty-printing broken on Python 3.4 [#256]
- trezorctl: Matrix recovery on Windows wouldn't allow backspace [#207]
- aes_encfs_getpass.py: fixed Python 3 bug [#169]

## [0.9.1] - 2018-03-05

[0.9.1]: https://github.com/trezor/python-trezor/compare/v0.9.0...v0.9.1

### Added

- proper support for Trezor model T
- support for Monacoin
- improvements to `trezorctl`:
  - add pretty-printing of features and protobuf debug dumps (fixes [#199])
  - support `TREZOR_PATH` environment variable to preselect a Trezor device.

### Removed

- gradually dropping Python 2 compatibility (pypi package will now be marked as Python 3 only)

[f#41]: https://github.com/trezor/trezor-firmware/pull/41
[f#87]: https://github.com/trezor/trezor-firmware/pull/87
[f#116]: https://github.com/trezor/trezor-firmware/pull/116
[f#117]: https://github.com/trezor/trezor-firmware/pull/117
[f#224]: https://github.com/trezor/trezor-firmware/pull/224
[f#226]: https://github.com/trezor/trezor-firmware/pull/226
[f#363]: https://github.com/trezor/trezor-firmware/pull/363
[f#411]: https://github.com/trezor/trezor-firmware/pull/411
[f#420]: https://github.com/trezor/trezor-firmware/pull/420
[f#445]: https://github.com/trezor/trezor-firmware/pull/445
[f#510]: https://github.com/trezor/trezor-firmware/pull/510
[f#525]: https://github.com/trezor/trezor-firmware/pull/525
[f#666]: https://github.com/trezor/trezor-firmware/pull/666
[f#680]: https://github.com/trezor/trezor-firmware/pull/680
[f#681]: https://github.com/trezor/trezor-firmware/pull/681
[f#778]: https://github.com/trezor/trezor-firmware/pull/778
[f#823]: https://github.com/trezor/trezor-firmware/pull/823
[f#1082]: https://github.com/trezor/trezor-firmware/pull/1082
[#15]: https://github.com/trezor/trezor-firmware/pull/15
[#37]: https://github.com/trezor/trezor-firmware/pull/37
[#38]: https://github.com/trezor/trezor-firmware/pull/38
[#94]: https://github.com/trezor/python-trezor/pull/94
[#167]: https://github.com/trezor/python-trezor/pull/167
[#169]: https://github.com/trezor/python-trezor/pull/169
[#185]: https://github.com/trezor/python-trezor/pull/185
[#197]: https://github.com/trezor/python-trezor/pull/197
[#199]: https://github.com/trezor/python-trezor/pull/199
[#207]: https://github.com/trezor/python-trezor/pull/207
[#223]: https://github.com/trezor/python-trezor/pull/223
[#226]: https://github.com/trezor/python-trezor/pull/226
[#229]: https://github.com/trezor/python-trezor/pull/229
[#230]: https://github.com/trezor/python-trezor/pull/230
[#236]: https://github.com/trezor/python-trezor/pull/236
[#237]: https://github.com/trezor/python-trezor/pull/237
[#241]: https://github.com/trezor/python-trezor/pull/241
[#242]: https://github.com/trezor/python-trezor/pull/242
[#245]: https://github.com/trezor/python-trezor/pull/245
[#248]: https://github.com/trezor/python-trezor/pull/248
[#249]: https://github.com/trezor/python-trezor/pull/249
[#250]: https://github.com/trezor/python-trezor/pull/250
[#256]: https://github.com/trezor/python-trezor/pull/256
[#268]: https://github.com/trezor/python-trezor/pull/268
[#269]: https://github.com/trezor/python-trezor/pull/269
[#274]: https://github.com/trezor/python-trezor/pull/274
[#276]: https://github.com/trezor/python-trezor/pull/276
[#277]: https://github.com/trezor/python-trezor/pull/277
[#280]: https://github.com/trezor/python-trezor/pull/280
[#283]: https://github.com/trezor/python-trezor/pull/283
[#284]: https://github.com/trezor/python-trezor/pull/284
[#286]: https://github.com/trezor/python-trezor/pull/286
[#287]: https://github.com/trezor/python-trezor/pull/287
[#300]: https://github.com/trezor/python-trezor/pull/300
[#301]: https://github.com/trezor/python-trezor/pull/301
[#302]: https://github.com/trezor/python-trezor/pull/302
[#304]: https://github.com/trezor/python-trezor/pull/304
[#307]: https://github.com/trezor/python-trezor/pull/307
[#308]: https://github.com/trezor/python-trezor/pull/308
[#312]: https://github.com/trezor/python-trezor/pull/312
[#314]: https://github.com/trezor/python-trezor/pull/314
[#315]: https://github.com/trezor/python-trezor/pull/315
[#325]: https://github.com/trezor/python-trezor/pull/325
[#349]: https://github.com/trezor/python-trezor/pull/349
[#351]: https://github.com/trezor/python-trezor/pull/351
[#352]: https://github.com/trezor/python-trezor/pull/352
[#379]: https://github.com/trezor/trezor-firmware/pull/379
[#810]: https://github.com/trezor/trezor-firmware/pull/810
[#948]: https://github.com/trezor/trezor-firmware/pull/948
[#1026]: https://github.com/trezor/trezor-firmware/pull/1026
[#1052]: https://github.com/trezor/trezor-firmware/pull/1052
[#1126]: https://github.com/trezor/trezor-firmware/pull/1126
[#1179]: https://github.com/trezor/trezor-firmware/pull/1179
[#1196]: https://github.com/trezor/trezor-firmware/pull/1196
[#1210]: https://github.com/trezor/trezor-firmware/pull/1210
[#1227]: https://github.com/trezor/trezor-firmware/pull/1227
[#1231]: https://github.com/trezor/trezor-firmware/pull/1231
[#1257]: https://github.com/trezor/trezor-firmware/pull/1257
[#1258]: https://github.com/trezor/trezor-firmware/pull/1258
[#1266]: https://github.com/trezor/trezor-firmware/pull/1266
[#1296]: https://github.com/trezor/trezor-firmware/pull/1296
[#1363]: https://github.com/trezor/trezor-firmware/pull/1363
[#1430]: https://github.com/trezor/trezor-firmware/pull/1430
[#1442]: https://github.com/trezor/trezor-firmware/pull/1442
[#1449]: https://github.com/trezor/trezor-firmware/pull/1449
[#1531]: https://github.com/trezor/trezor-firmware/pull/1531
[#1541]: https://github.com/trezor/trezor-firmware/pull/1541
[#1586]: https://github.com/trezor/trezor-firmware/pull/1586
[#1604]: https://github.com/trezor/trezor-firmware/pull/1604
[#1668]: https://github.com/trezor/trezor-firmware/pull/1668
[#1671]: https://github.com/trezor/trezor-firmware/pull/1671
[#1683]: https://github.com/trezor/trezor-firmware/pull/1683
[#1702]: https://github.com/trezor/trezor-firmware/pull/1702
[#1710]: https://github.com/trezor/trezor-firmware/pull/1710
[#1738]: https://github.com/trezor/trezor-firmware/pull/1738
[#1745]: https://github.com/trezor/trezor-firmware/pull/1745
[#1765]: https://github.com/trezor/trezor-firmware/pull/1765
[#1771]: https://github.com/trezor/trezor-firmware/pull/1771
[#1772]: https://github.com/trezor/trezor-firmware/pull/1772
[#1783]: https://github.com/trezor/trezor-firmware/pull/1783
[#1798]: https://github.com/trezor/trezor-firmware/pull/1798
[#1835]: https://github.com/trezor/trezor-firmware/pull/1835
[#1838]: https://github.com/trezor/trezor-firmware/pull/1838
[#1857]: https://github.com/trezor/trezor-firmware/pull/1857
[#1867]: https://github.com/trezor/trezor-firmware/pull/1867
[#1885]: https://github.com/trezor/trezor-firmware/pull/1885
[#1893]: https://github.com/trezor/trezor-firmware/pull/1893
[#1896]: https://github.com/trezor/trezor-firmware/pull/1896
[#1959]: https://github.com/trezor/trezor-firmware/pull/1959
[#1967]: https://github.com/trezor/trezor-firmware/pull/1967
[#1970]: https://github.com/trezor/trezor-firmware/pull/1970
[#2023]: https://github.com/trezor/trezor-firmware/pull/2023
[#2036]: https://github.com/trezor/trezor-firmware/pull/2036
[#2093]: https://github.com/trezor/trezor-firmware/pull/2093
[#2100]: https://github.com/trezor/trezor-firmware/pull/2100
[#2114]: https://github.com/trezor/trezor-firmware/pull/2114
[#2123]: https://github.com/trezor/trezor-firmware/pull/2123
[#2126]: https://github.com/trezor/trezor-firmware/pull/2126
[#2135]: https://github.com/trezor/trezor-firmware/pull/2135
[#2159]: https://github.com/trezor/trezor-firmware/pull/2159
[#2199]: https://github.com/trezor/trezor-firmware/pull/2199
[#2219]: https://github.com/trezor/trezor-firmware/pull/2219
[#2221]: https://github.com/trezor/trezor-firmware/pull/2221
[#2230]: https://github.com/trezor/trezor-firmware/pull/2230
[#2239]: https://github.com/trezor/trezor-firmware/pull/2239
[#2284]: https://github.com/trezor/trezor-firmware/pull/2284
[#2289]: https://github.com/trezor/trezor-firmware/pull/2289
[#2354]: https://github.com/trezor/trezor-firmware/pull/2354
[#2364]: https://github.com/trezor/trezor-firmware/pull/2364
[#2414]: https://github.com/trezor/trezor-firmware/pull/2414
[#2433]: https://github.com/trezor/trezor-firmware/pull/2433
[#2439]: https://github.com/trezor/trezor-firmware/pull/2439
[#2445]: https://github.com/trezor/trezor-firmware/pull/2445
[#2517]: https://github.com/trezor/trezor-firmware/pull/2517
[#2535]: https://github.com/trezor/trezor-firmware/pull/2535
[#2541]: https://github.com/trezor/trezor-firmware/pull/2541
[#2542]: https://github.com/trezor/trezor-firmware/pull/2542
[#2547]: https://github.com/trezor/trezor-firmware/pull/2547
[#2561]: https://github.com/trezor/trezor-firmware/pull/2561
[#2576]: https://github.com/trezor/trezor-firmware/pull/2576
[#2608]: https://github.com/trezor/trezor-firmware/pull/2608
[#2692]: https://github.com/trezor/trezor-firmware/pull/2692
[#2701]: https://github.com/trezor/trezor-firmware/pull/2701
[#2745]: https://github.com/trezor/trezor-firmware/pull/2745
[#2786]: https://github.com/trezor/trezor-firmware/pull/2786
[#2795]: https://github.com/trezor/trezor-firmware/pull/2795
[#2801]: https://github.com/trezor/trezor-firmware/pull/2801
[#2832]: https://github.com/trezor/trezor-firmware/pull/2832
[#2833]: https://github.com/trezor/trezor-firmware/pull/2833
[#2880]: https://github.com/trezor/trezor-firmware/pull/2880
[#2919]: https://github.com/trezor/trezor-firmware/pull/2919
[#2967]: https://github.com/trezor/trezor-firmware/pull/2967
[#2989]: https://github.com/trezor/trezor-firmware/pull/2989
[#3037]: https://github.com/trezor/trezor-firmware/pull/3037
[#3045]: https://github.com/trezor/trezor-firmware/pull/3045
[#3048]: https://github.com/trezor/trezor-firmware/pull/3048
[#3203]: https://github.com/trezor/trezor-firmware/pull/3203
[#3208]: https://github.com/trezor/trezor-firmware/pull/3208
[#3227]: https://github.com/trezor/trezor-firmware/pull/3227
[#3237]: https://github.com/trezor/trezor-firmware/pull/3237
[#3255]: https://github.com/trezor/trezor-firmware/pull/3255
[#3359]: https://github.com/trezor/trezor-firmware/pull/3359
[#3364]: https://github.com/trezor/trezor-firmware/pull/3364
[#3422]: https://github.com/trezor/trezor-firmware/pull/3422
[#3434]: https://github.com/trezor/trezor-firmware/pull/3434
[#3442]: https://github.com/trezor/trezor-firmware/pull/3442
[#3496]: https://github.com/trezor/trezor-firmware/pull/3496
[#3504]: https://github.com/trezor/trezor-firmware/pull/3504
[#3636]: https://github.com/trezor/trezor-firmware/pull/3636
[#3728]: https://github.com/trezor/trezor-firmware/pull/3728
[#3868]: https://github.com/trezor/trezor-firmware/pull/3868
[#3893]: https://github.com/trezor/trezor-firmware/pull/3893
[#3993]: https://github.com/trezor/trezor-firmware/pull/3993
[#4000]: https://github.com/trezor/trezor-firmware/pull/4000
[#4041]: https://github.com/trezor/trezor-firmware/pull/4041
[#4076]: https://github.com/trezor/trezor-firmware/pull/4076
[#4089]: https://github.com/trezor/trezor-firmware/pull/4089
[#4101]: https://github.com/trezor/trezor-firmware/pull/4101
[#4119]: https://github.com/trezor/trezor-firmware/pull/4119
[#4155]: https://github.com/trezor/trezor-firmware/pull/4155
[#4282]: https://github.com/trezor/trezor-firmware/pull/4282
[#4351]: https://github.com/trezor/trezor-firmware/pull/4351
[#4464]: https://github.com/trezor/trezor-firmware/pull/4464
