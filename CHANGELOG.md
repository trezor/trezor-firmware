# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/).

_At the moment, the project does __not__ adhere to [Semantic Versioning](http://semver.org/spec/v2.0.0.html). That is expected to change with version 1.0._


## [Unreleased]
[Unreleased]: https://github.com/trezor/python-trezor/compare/v0.10.2...master

### Added
- `tx_api` now supports Blockbook backend servers
- `TxApiInsight` can work purely on cached files, without specifying a URL

### Changed
- protobuf classes are no longer part of the source distribution and must be compiled locally
- Stellar: addresses are always strings

### Removed
- `EncryptMessage` and `DecryptMessage` actions are gone

### Fixed:
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
[#277]: https://github.com/trezor/python-trezor/issues/277
[#280]: https://github.com/trezor/python-trezor/issues/280
