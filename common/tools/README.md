# Common Tools

This directory contains mostly tools that can manipulate definitions in [defs/](../defs).

Tools are written with [Click](http://click.pocoo.org/6/), so you always get a help text
if you use the `--help` option.

All tools require Python 3.8 or higher and a bunch of dependencies, listed in `requirements.txt`.
You can install them all with `pip3 install -r requirements.txt`.

## Tools overview

### `cointool.py`

This is a general-purpose tool to examine coin definitions. Currently it implements
the following commands:

* **`render`**: generate code based on a [Mako](http://docs.makotemplates.org/en/latest/index.html)
  template. By default, `cointool.py render foo.bar.mako` will put its result into
  file `foo.bar` in the same directory. See [usage in `trezor-core`](https://github.com/trezor/trezor-core/commit/348b99b8dc5bcfc4ab85e1e7faad3fb4ef3e8763).
* **`check`**: check validity of json definitions and associated data. Used in CI.
* **`dump`**: dump coin information, including support status, in JSON format. Various
  filtering options are available, check help for details.

Use `cointool.py command --help` to get more information on each command.

### `support.py`

Used to query and manage info in `support.json`. This mainly supports the release flow.

The following commands are available:

* **`check`**: check validity of json data. Used in CI.
* **`fix`**: prune keys without associated coins.
* **`show`**: keyword-search for a coin and show its support status for each device.
* **`set`**: set support data.
* **`release`**: perform the [release workflow](#release-workflow).

Use `support.py command --help` to get more information on each command.

### `coin_info.py`

In case where code generation with `cointool.py render` is impractical or not sufficient,
you can query the data directly through Python. Short usage example:

```python
import coin_info

defs = coin_info.coin_info()
list_of_all_coins = defs.as_list()
dict_by_coin_key = defs.as_dict()

for token in defs.erc20:
    print(token["key"], token["name"], token["shortcut"])

support_info = coin_info.support_info(defs.misc)
for key, support in support_info.values():
    t2_support = support["T2T1"]
    coin_name = dict_by_coin_key[key]
    if t2_support:
        print(coin_name, "is supported since version", t2_support)
    else:
        print(coin_name, "is not supported")
```

See docstrings for the most important functions: `coin_info()` and `support_info()`.

The file `coindef.py` is a protobuf definition for passing coin data to Trezor
from the outside.

### `marketcap.py`

Module for obtaining market cap and price data used by `maxfee.py`.

### `maxfee.py`

Updates the `maxfee_kb` coin property based on a specified maximum per-transaction fee. The command
fetches current price data from https://coinmarketcap.com/ to convert from fiat-denominated maximum
fee.

# Release Workflow

This entails collecting information on coins whose support status is unknown and
bumping timestamp of external definitions <??? TODO>.

## Maintaining Support Status

When a new coin definition is added, its support status is _unknown_. It is excluded
from code generation by default. If you want to include a coin in a firmware build,
you need to switch it to supported in a particular version first. You can set multiple
support statuses at the same time:

```
$ ./support.py show Ontology
misc:ONT - Ontology (ONT)
 * connect : NO
 * T1B1 : support info missing
 * T2T1 : support info missing
 * suite : NO

$ ./support.py set misc:ONT T1B1=no -r "not planned on T1" T2T1=2.4.7
misc:ONT - Ontology (ONT)
 * connect : NO
 * T1B1 : NO (reason: not planned on T1)
 * T2T1 : 2.4.7
 * suite : NO
```

Afterwards, review and commit changes to `defs/support.json`, and update the `trezor-common`
submodule in your target firmware.

## Releasing a new firmware

#### **Step 1:** run the release script

```sh
./tools/release.sh
```

Coins in state _unknown_, i.e., coins that are known in the definitions but not listed
in support files, will be interactively added one by one. To avoid that, run `support.py
release -y` separately.

#### **Step 2:** review and commit your changes

Use `git diff` to review changes made, commit and push.
