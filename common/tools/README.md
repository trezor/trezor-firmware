# Common Tools

This directory contains mostly tools that can manipulate definitions in [defs/](../defs).

Tools are written with [Click](http://click.pocoo.org/6/), so you always get a help text
if you use the `--help` option.

All tools require Python 3.6 or higher and a bunch of dependencies, listed in `requirements.txt`.
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
* **`coindefs`**: generate signed protobuf descriptions of coins. This is for future use
  and could allow us to not need to store coin data in Trezor itself.

Use `cointool.py command --help` to get more information on each command.

### `support.py`

Used to query and manage info in `support.json`. This mainly supports the release flow.

The following commands are available:

* **`check`**: check validity of json data. Used in CI.
* **`fix`**: fix expected problems: prune keys without associated coins and ensure
  that ERC20 tokens are correctly entered as duplicate.
* **`show`**: keyword-search for a coin and show its support status for each device.
* **`set`**: set support data.
* **`release`**: perform the [release workflow](#release-workflow).

Use `support.py command --help` to get more information on each command.

### `coins_details.py`

Generates `coins_details.json`, source file for https://trezor.io/coins.
Collects data on coins, downloads market caps and puts everything into a single file.
Caches market cap data so you don't have to download it every time.

### `diffize_coins_details.py`

Compares generated `coins_details.json` to the released version currently served
on https://trezor.io/coins, in a format that is nicely readable to humans and
hard(er) to mess up by diff.

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
    t2_support = support["trezor2"]
    coin_name = dict_by_coin_key[key]
    if t2_support == "soon":
        print(coin_name, "will be supported soon!")
    elif t2_support:
        print(coin_name, "is supported since version", t2_support)
    else:
        print(coin_name, "is not supported")
```

See docstrings for the most important functions: `coin_info()` and `support_info()`.

The file `coindef.py` is a protobuf definition for passing coin data to Trezor
from the outside.


# Release Workflow

This entails collecting information on coins whose support status is unknown,
marking coins whose support status is `soon`, and including new ERC20 tokens.

## Maintaining Support Status

When a new coin definition is added, its support status is _unknown_. It is excluded
from code generation by default. If you want to include a coin in a firmware build,
you need to switch it to _soon_ first. You can set multiple support statuses at the
same time:

```
$ ./support.py show Ontology
misc:ONT - Ontology (ONT)
 * connect : NO
 * trezor1 : support info missing
 * trezor2 : support info missing
 * webwallet : NO

$ ./support.py set misc:ONT trezor1=no -r "not planned on T1" trezor2=soon
misc:ONT - Ontology (ONT)
 * connect : NO
 * trezor1 : NO (reason: not planned on T1)
 * trezor2 : SOON
 * webwallet : NO
```

Afterwards, review and commit changes to `defs/support.json`, and update the `trezor-common`
submodule in your target firmware.

If you're adding multiple coins at once, you can use `support.py release 1 --soon` to automatically
add all currently-unknown coins to _soon_. (The `1` indicates that this is for Trezor One)

ERC20 tokens in _unknown_ state are considered _soon_ as well, unless their symbols
are duplicates. Use `support.py fix` to synchronize duplicate status in `support.json` file.
Or mark them as unsupported explicitly.

## Releasing a new firmware

#### **Step 1:** update the tokens repo

```sh
pushd defs/ethereum/tokens
git checkout master
git pull
popd
git add defs/ethereum/tokens
```

#### **Step 2:** run the release flow

```sh
./tools/support.py release 2
```

The number `2` indicates that you are releasing Trezor 2. The version will be
automatically determined, based on currently released firmwares. Or you can explicitly
specify the version with `-r 2.1.0`.

All currently known unreleased ERC20 tokens are automatically set to the given version.

All coins marked _soon_ are set to the current version. This is automatic - coins that
were marked _soon_ were used in code generation and so should be released. If you want
to avoid this, you will have to manually revert each coin to _soon_ status, either with
`support.py set`, or by manually editing `support.json`.

Coins in state _unknown_, i.e., coins that are known in the definitions but not listed
in support files, will be also added. But you will be interactively asked to confirm
each one. Use `-y` or `--add-all` to auto-add all of them.

Use `-n` or `--dry-run` to see changes without writing them to `support.json`. Use
`-v` or `--verbose` to also show ERC20 tokens which are processed silently by default.

Use `-g` or `--git-tag` to automatically tag the current `HEAD` with a version, e.g.,
`trezor2-2.1.0`. This might become default in the future.

XXX this should also commit the changes though, otherwise the tag will apply to the wrong
commit.

#### **Step 3:** review and commit your changes

Use `git diff` to review changes made, commit and push. If you tagged the commit in the
previous step, don't forget to `git push --tags` too.

#### **Step 4:** update submodule in your target repository

Go to `trezor-core` or `trezor-mcu` checkout and update the submodule. Checkout the
appropriate tag if you created it. If you're in `trezor-core`, run `make templates`
to update source files.
