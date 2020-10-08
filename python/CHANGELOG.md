# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.13.0] - Unreleased
[0.13.0]: https://github.com/trezor/trezor-firmware/compare/python/v0.12.2...master

### Added

- Enabled session management via `EndSession`  [#1227]
- Support for temporary or permanent `safety-checks` setting

### Changed

- protobuf is aware of `required` fields and default values
- `btc.sign_tx()` accepts keyword arguments for transaction metadata  [#1266]

### Deprecated

- instantiating protobuf objects with positional arguments is deprecated
- values of required fields must be supplied at instantiation time. Omitting them is deprecated.
- `details` argument to `btc.sign_tx()` is deprecated. Use keyword arguments instead.

### Fixed

- added missing dependency on `attrs`  [#1232]
- fixed number imprecision in `build_tx.py` that could cause "invalid prevhash" errors

### Removed

- dropped Python 3.5 support  [#810]


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

[f#41]: https://github.com/trezor/trezor-firmware/issues/41
[f#87]: https://github.com/trezor/trezor-firmware/issues/87
[f#116]: https://github.com/trezor/trezor-firmware/issues/116
[f#117]: https://github.com/trezor/trezor-firmware/issues/117
[f#224]: https://github.com/trezor/trezor-firmware/issues/224
[f#226]: https://github.com/trezor/trezor-firmware/issues/226
[f#363]: https://github.com/trezor/trezor-firmware/issues/363
[f#411]: https://github.com/trezor/trezor-firmware/issues/411
[f#420]: https://github.com/trezor/trezor-firmware/issues/420
[f#445]: https://github.com/trezor/trezor-firmware/issues/445
[f#510]: https://github.com/trezor/trezor-firmware/issues/510
[f#525]: https://github.com/trezor/trezor-firmware/issues/525
[f#666]: https://github.com/trezor/trezor-firmware/issues/666
[f#680]: https://github.com/trezor/trezor-firmware/issues/680
[f#681]: https://github.com/trezor/trezor-firmware/issues/681
[f#778]: https://github.com/trezor/trezor-firmware/issues/778
[f#823]: https://github.com/trezor/trezor-firmware/issues/823
[f#1082]: https://github.com/trezor/trezor-firmware/issues/1082
[#37]: https://github.com/trezor/trezor-firmware/issues/37
[#38]: https://github.com/trezor/trezor-firmware/issues/38
[#94]: https://github.com/trezor/python-trezor/issues/94
[#167]: https://github.com/trezor/python-trezor/issues/167
[#169]: https://github.com/trezor/python-trezor/issues/169
[#185]: https://github.com/trezor/python-trezor/issues/185
[#197]: https://github.com/trezor/python-trezor/issues/197
[#199]: https://github.com/trezor/python-trezor/issues/199
[#207]: https://github.com/trezor/python-trezor/issues/207
[#223]: https://github.com/trezor/python-trezor/issues/223
[#226]: https://github.com/trezor/python-trezor/issues/226
[#229]: https://github.com/trezor/python-trezor/issues/229
[#230]: https://github.com/trezor/python-trezor/issues/230
[#236]: https://github.com/trezor/python-trezor/issues/236
[#237]: https://github.com/trezor/python-trezor/issues/237
[#241]: https://github.com/trezor/python-trezor/issues/241
[#242]: https://github.com/trezor/python-trezor/issues/242
[#245]: https://github.com/trezor/python-trezor/issues/245
[#248]: https://github.com/trezor/python-trezor/issues/248
[#249]: https://github.com/trezor/python-trezor/issues/249
[#250]: https://github.com/trezor/python-trezor/issues/250
[#256]: https://github.com/trezor/python-trezor/issues/256
[#268]: https://github.com/trezor/python-trezor/issues/268
[#269]: https://github.com/trezor/python-trezor/issues/269
[#274]: https://github.com/trezor/python-trezor/issues/274
[#276]: https://github.com/trezor/python-trezor/issues/276
[#277]: https://github.com/trezor/python-trezor/issues/277
[#280]: https://github.com/trezor/python-trezor/issues/280
[#283]: https://github.com/trezor/python-trezor/issues/283
[#284]: https://github.com/trezor/python-trezor/issues/284
[#286]: https://github.com/trezor/python-trezor/issues/286
[#287]: https://github.com/trezor/python-trezor/issues/287
[#300]: https://github.com/trezor/python-trezor/issues/300
[#301]: https://github.com/trezor/python-trezor/issues/301
[#302]: https://github.com/trezor/python-trezor/issues/302
[#304]: https://github.com/trezor/python-trezor/issues/304
[#307]: https://github.com/trezor/python-trezor/issues/307
[#308]: https://github.com/trezor/python-trezor/issues/308
[#312]: https://github.com/trezor/python-trezor/issues/312
[#314]: https://github.com/trezor/python-trezor/issues/314
[#315]: https://github.com/trezor/python-trezor/issues/315
[#325]: https://github.com/trezor/python-trezor/issues/325
[#349]: https://github.com/trezor/python-trezor/issues/349
[#351]: https://github.com/trezor/python-trezor/issues/351
[#352]: https://github.com/trezor/python-trezor/issues/352
[#810]: https://github.com/trezor/trezor-firmware/issues/810
[#948]: https://github.com/trezor/trezor-firmware/issues/948
[#1052]: https://github.com/trezor/trezor-firmware/issues/1052
[#1126]: https://github.com/trezor/trezor-firmware/issues/1126
[#1179]: https://github.com/trezor/trezor-firmware/issues/1179
[#1196]: https://github.com/trezor/trezor-firmware/issues/1196
[#1210]: https://github.com/trezor/trezor-firmware/issues/1210
[#1227]: https://github.com/trezor/trezor-firmware/issues/1227
[#1232]: https://github.com/trezor/trezor-firmware/issues/1232
[#1266]: https://github.com/trezor/trezor-firmware/issues/1266
