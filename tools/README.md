# Tools directory

### `coin_info.py`

Central module that extracts information from jsons in `defs/` directory.
Its most important function is `get_all()`.

### `cointool.py`

Code and data generator. Has the following functions:

* __`check`__: runs validations. Currently, that is:
  * schema validity in `defs/coins/*.json`
  * availability of bitcore/blockbook backends
  * icon format

* __`coins_json`__: generates `coins.json` for use in python-trezor, connect
  and wallet. By default outputs to current directory.

* __`coindefs`__: generates `coindefs.json`, intended future format for sending
  coin definitions to Trezor.

* __`render`__: for every `filename.ext.mako` passed (or for all found in directory),
  renders the Mako template with coin definitions and stores as corresponding
  `filename.ext`. This is used to generate code in trezor-mcu and trezor-core.

### `coins_details.py`

Regenerates `defs/coins_details.json`, which is a catalog of coins for https://trezor.io/coins.

All information is generated from coin definitions in `defs/`, support info is
taken either from `support.json`, or assumed (see `coin_info.support_info()`).

If needed, any value can be overriden in `coins_details.override.json`.

### `support.py`

Support info management. Ensures `support.json` is in the proper format. Has the
following subcommands:

* __`check`__: checks validity of support data. Ensures that data is valid,
  there are no orphaned keys in `support.json`, no known coins have missing
  support info, etc.

* __`show <keyword>`__: searches coin database, matching key (`coin:BTC`),
  name ("Bitcoin") or shortcut / ticker symbol ("BTC"). Displays all coins that match
  and their support info, if found.

* __`set <key> [symbol=value]...`__: updates support info for coin key (`coin:BTC`,
  can be found with `support.py show`). Basic `symbol`s are: `trezor1 trezor2
  connect webwallet`. Anything else is considered a link name:
  `"Electrum=https://electrum.org"`  
  Allowed `value`s are `yes`, `no`, `soon`, `planned`, URLs and firmware version
  numbers. Empty value (`trezor1=`) clears the respective symbol.

### `requirements.txt`

List of Python requiremens for all tools in `pip` format. Set up your environment with
`pip3 install -r requirements.txt`, or `pipenv install -r requirements.txt`.

Python 3.6 or higher is required.
