# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/).

_At the moment, the project does __not__ adhere to [Semantic Versioning](http://semver.org/spec/v2.0.0.html). That is expected to change with version 1.0._

## [0.11.2] - 2019-02-26
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
- webusb: issue device reset before connecting (fixes weird device states)

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
