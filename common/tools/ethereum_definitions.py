#!/usr/bin/env python3
from __future__ import annotations

import copy
import datetime
import io
import json
import logging
import os
import pathlib
import re
import sys
import zipfile
from binascii import hexlify
from collections import defaultdict
from typing import Any, TextIO, cast
from urllib.parse import urlencode

import click
import ed25519
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from coin_info import Coin, Coins, load_json
from trezorlib import ethereum, protobuf
from trezorlib.merkle_tree import MerkleTree
from trezorlib.messages import (
    EthereumDefinitionType,
    EthereumNetworkInfo,
    EthereumTokenInfo,
)

FORMAT_VERSION_BYTES = b"trzd1"
CURRENT_TIME = datetime.datetime.now(datetime.timezone.utc)
TIMESTAMP_FORMAT = "%d.%m.%Y %X%z"
CURRENT_TIMESTAMP_STR = CURRENT_TIME.strftime(TIMESTAMP_FORMAT)

ETHEREUM_TESTNETS_REGEXES = (".*testnet.*", ".*devnet.*")


if os.environ.get("DEFS_DIR"):
    DEFS_DIR = pathlib.Path(os.environ.get("DEFS_DIR")).resolve()
else:
    DEFS_DIR = pathlib.Path(__file__).resolve().parent.parent / "defs"

LATEST_DEFINITIONS_TIMESTAMP_FILEPATH = (
    DEFS_DIR / "ethereum" / "latest_definitions_timestamp.txt"
)
DEFINITIONS_CACHE_FILEPATH = pathlib.Path("definitions-cache.json")


# ====== utils ======


def setup_logging(verbose: bool):
    log_level = logging.DEBUG if verbose else logging.WARNING
    root = logging.getLogger()
    root.setLevel(log_level)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    root.addHandler(handler)


def hash_dict_on_keys(
    d: dict,
    include_keys: list[str] | None = None,
    exclude_keys: list[str] | None = None,
) -> int:
    """Get the hash of a dict on selected keys.
    Options `include_keys` and `exclude_keys` are exclusive."""
    if include_keys is not None and exclude_keys is not None:
        raise TypeError("Options `include_keys` and `exclude_keys` are exclusive")

    tmp_dict = {}
    for k, v in d.items():
        if include_keys is not None and k in include_keys:
            tmp_dict[k] = v
        elif exclude_keys is not None and k not in exclude_keys:
            tmp_dict[k] = v
        elif include_keys is None and exclude_keys is None:
            tmp_dict[k] = v

    return hash(json.dumps(tmp_dict, sort_keys=True))


class Cache:
    """Generic cache object that caches to json."""

    def __init__(self, cache_filepath: pathlib.Path) -> None:
        if cache_filepath.exists() and not cache_filepath.is_file():
            raise ValueError(
                f'Path for storing cache "{cache_filepath}" exists and is not a file.'
            )
        self.cache_filepath = cache_filepath
        self.cached_data: Any = {}

    def is_expired(self) -> bool:
        mtime = (
            self.cache_filepath.stat().st_mtime if self.cache_filepath.exists() else 0
        )
        return (
            mtime
            <= (
                datetime.datetime.now(datetime.timezone.utc)
                - datetime.timedelta(hours=1)
            ).timestamp()
        )

    def load(self) -> None:
        self.cached_data = load_json(self.cache_filepath)

    def save(self) -> None:
        with open(self.cache_filepath, "w+") as f:
            json.dump(
                obj=self.cached_data, fp=f, ensure_ascii=False, sort_keys=True, indent=1
            )
            f.write("\n")

    def get(self, key: Any, default: Any = None) -> Any:
        return self.cached_data.get(key, default)

    def set(self, key: Any, data: Any) -> None:
        self.cached_data[key] = copy.deepcopy(data)

    def __contains__(self, key):
        return key in self.cached_data


class EthereumDefinitionsCachedDownloader:
    """Class that handles all the downloading and caching of Ethereum definitions."""

    def __init__(self, refresh: bool | None = None) -> None:
        force_refresh = refresh is True
        disable_refresh = refresh is False
        self.running_from_cache = False
        self.cache = Cache(DEFINITIONS_CACHE_FILEPATH)

        if disable_refresh or (not self.cache.is_expired() and not force_refresh):
            logging.info("Loading cached Ethereum definitions data")
            self.cache.load()
            self.running_from_cache = True
        else:
            self._init_requests_session()

    def save_cache(self):
        if not self.running_from_cache:
            self.cache.save()

    def _download_json(self, url: str, **url_params: Any) -> Any:
        params = None
        encoded_params = None
        key = url

        # convert params to lower-case strings (especially for boolean values
        # because for CoinGecko API "True" != "true")
        if url_params:
            params = {key: str(value).lower() for key, value in url_params.items()}
            encoded_params = urlencode(sorted(params.items()))
            key += "?" + encoded_params

        if self.running_from_cache:
            return self.cache.get(key)

        logging.info(f"Fetching data from {url}")

        r = self.session.get(url, params=encoded_params, timeout=60)
        r.raise_for_status()
        data = r.json()
        self.cache.set(key, data)
        return data

    def _init_requests_session(self) -> requests.Session:
        self.session = requests.Session()
        retries = Retry(total=5, status_forcelist=[502, 503, 504])
        self.session.mount("https://", HTTPAdapter(max_retries=retries))

    def get_coingecko_asset_platforms(self) -> Any:
        url = "https://api.coingecko.com/api/v3/asset_platforms"
        return self._download_json(url)

    def get_defillama_chains(self) -> Any:
        url = "https://api.llama.fi/chains"
        return self._download_json(url)

    def get_coingecko_tokens_for_network(self, coingecko_network_id: str) -> Any:
        url = f"https://tokens.coingecko.com/{coingecko_network_id}/all.json"
        data = None
        try:
            data = self._download_json(url)
        except requests.exceptions.HTTPError as err:
            # "Forbidden" is raised by Coingecko if no tokens are available under specified id
            if err.response.status_code != requests.codes.forbidden:
                raise err

        return [] if data is None else data.get("tokens", [])

    def get_coingecko_coins_list(self) -> Any:
        url = "https://api.coingecko.com/api/v3/coins/list"
        return self._download_json(url, include_platform=True)

    def get_coingecko_top100(self) -> Any:
        url = "https://api.coingecko.com/api/v3/coins/markets"
        return self._download_json(
            url,
            vs_currency="usd",
            order="market_cap_desc",
            per_page=100,
            page=1,
            sparkline=False,
        )


def get_testnet_status(*strings: str | None) -> bool:
    if strings is None:
        return False

    for r in ETHEREUM_TESTNETS_REGEXES:
        for s in strings:
            if re.search(r, s.lower(), re.IGNORECASE):
                return True

    return False


def _load_ethereum_networks_from_repo(repo_dir: pathlib.Path) -> list[dict]:
    """Load ethereum networks from submodule."""
    chains_path = repo_dir / "_data" / "chains"
    networks = []
    for chain in sorted(
        chains_path.glob("eip155-*.json"),
        key=lambda x: int(x.stem.replace("eip155-", "")),
    ):
        chain_data = load_json(chain)
        shortcut = chain_data["nativeCurrency"]["symbol"]
        name = chain_data["name"]
        title = chain_data.get("title", "")
        is_testnet = get_testnet_status(name, title)
        if is_testnet:
            slip44 = 1
        else:
            slip44 = chain_data.get("slip44", 60)

        if is_testnet and not shortcut.lower().startswith("t"):
            shortcut = "t" + shortcut

        # strip out bullcrap in network naming
        if "mainnet" in name.lower():
            name = re.sub(r" mainnet.*$", "", name, flags=re.IGNORECASE)

        networks.append(
            dict(
                chain=chain_data["shortName"],
                chain_id=chain_data["chainId"],
                is_testnet=is_testnet,
                slip44=slip44,
                shortcut=shortcut,
                name=name,
            )
        )

    return networks


def _create_cropped_token_dict(
    complex_token: dict, chain_id: int, chain: str
) -> dict | None:
    # simple validation
    if complex_token["address"][:2] != "0x" or int(complex_token["decimals"]) < 0:
        return None
    try:
        bytes.fromhex(complex_token["address"][2:])
    except ValueError:
        return None

    return dict(
        chain=chain,
        chain_id=chain_id,
        name=complex_token["name"],
        decimals=complex_token["decimals"],
        address=str(complex_token["address"]).lower(),
        shortcut=complex_token["symbol"],
    )


def _load_erc20_tokens_from_coingecko(
    downloader: EthereumDefinitionsCachedDownloader, networks: list[dict]
) -> list[dict]:
    tokens: list[dict] = []
    for network in networks:
        if (coingecko_id := network.get("coingecko_id")) is not None:
            all_tokens = downloader.get_coingecko_tokens_for_network(coingecko_id)

            for token in all_tokens:
                t = _create_cropped_token_dict(
                    token, network["chain_id"], network["chain"]
                )
                if t is not None:
                    tokens.append(t)

    return tokens


def _load_erc20_tokens_from_repo(
    repo_dir: pathlib.Path, networks: list[dict]
) -> list[dict]:
    """Load ERC20 tokens from submodule."""
    tokens: list[dict] = []
    for network in networks:
        chain = network["chain"]

        chain_path = repo_dir / "tokens" / chain
        for file in sorted(chain_path.glob("*.json")):
            token: dict = load_json(file)
            t = _create_cropped_token_dict(token, network["chain_id"], network["chain"])
            if t is not None:
                tokens.append(t)

    return tokens


def _set_definition_metadata(
    definition: dict,
    old_definition: dict | None = None,
    keys: str | None = None,
    deleted: bool = False,
) -> None:
    if "metadata" not in definition:
        definition["metadata"] = {}

    if deleted:
        definition["metadata"]["deleted"] = CURRENT_TIMESTAMP_STR
    else:
        definition["metadata"].pop("deleted", None)

    if old_definition is not None and keys is not None:
        for key in keys:
            definition["metadata"]["previous_" + key] = old_definition.get(key)

    # if metadata are empty, delete them
    if len(definition["metadata"]) == 0:
        definition.pop("metadata", None)


def print_definition_change(
    name: str,
    status: str,
    old: dict,
    new: dict | None = None,
    original: dict | None = None,
    prompt: bool = False,
    use_default: bool = True,
) -> bool | None:
    """Print changes made between definitions and ask for prompt if requested. Returns the prompt result if prompted otherwise None."""
    old_deleted_status = get_definition_deleted_status(old)
    old_deleted_status_wrapped = (
        " (" + old_deleted_status + ")" if old_deleted_status else ""
    )

    title = f"{old_deleted_status + ' ' if old_deleted_status else ''}{name} PROBABLY {status}"
    print(f"== {title} ==")
    print(f"OLD{old_deleted_status_wrapped}:")
    print(json.dumps(old, sort_keys=True, indent=None))
    if new is not None:
        print("NEW:")
        print(json.dumps(new, sort_keys=True, indent=None))
        if original is not None:
            original_deleted_status_wrapped = (
                " (" + get_definition_deleted_status(original) + ")"
                if get_definition_deleted_status(original)
                else ""
            )
            print(f"REPLACING{original_deleted_status_wrapped}:")
            print(json.dumps(original, sort_keys=True, indent=None))

    if prompt:
        answer = click.prompt(
            "Confirm change:",
            type=click.Choice(["y", "n"]),
            show_choices=True,
            default="y" if use_default else None,
            show_default=use_default,
        )
        return True if answer == "y" else False
    return None


def print_definitions_collision(
    name: str,
    definitions: list[dict],
    old_definitions: list[dict] | None = None,
) -> int | None:
    """Print colliding definitions and ask which one to keep if requested.
    Returns an index of selected definition from the prompt result (if prompted) or the default value."""
    if old_definitions:
        old_defs_hash_no_metadata = [
            hash_dict_on_keys(d, exclude_keys=["metadata", "coingecko_id"])
            for d in old_definitions
        ]

    default_index = None
    print(f"== COLLISION BETWEEN {name}S ==")
    for idx, definition in enumerate(definitions):
        found = ""
        if (
            old_definitions
            and hash_dict_on_keys(definition, exclude_keys=["metadata", "coingecko_id"])
            in old_defs_hash_no_metadata
        ):
            found = " (found in old definitions)"
            default_index = idx
        print(f"DEFINITION {idx}{found}:")
        print(json.dumps(definition, sort_keys=True, indent=None))

    answer = int(
        click.prompt(
            "Which definition do you want to keep? Please enter a valid integer",
            type=click.Choice([str(n) for n in range(len(definitions))]),
            show_choices=True,
            default=str(default_index) if default_index is not None else None,
            show_default=default_index is not None,
        )
    )
    return answer


def get_definition_deleted_status(definition: dict) -> str:
    return (
        "PREVIOUSLY DELETED"
        if definition.get("metadata", {}).get("deleted") is not None
        else ""
    )


def check_tokens_collisions(tokens: list[dict], old_tokens: list[dict] | None) -> None:
    collisions: defaultdict = defaultdict(list)
    for idx, nd in enumerate(tokens):
        collisions[hash_dict_on_keys(nd, ["chain_id", "address"])].append(idx)

    no_of_collisions = 0
    for _, v in collisions.items():
        if len(v) > 1:
            no_of_collisions += 1

    if no_of_collisions > 0:
        logging.info(f"\nNumber of collisions: {no_of_collisions}")

    # solve collisions
    delete_indexes: list[int] = []
    for _, v in collisions.items():
        if len(v) > 1:
            coliding_networks = [tokens[i] for i in v]
            index = print_definitions_collision("TOKEN", coliding_networks, old_tokens)
            logging.info(f"Keeping the definition with index {index}.")
            v.pop(index)
            delete_indexes.extend(v)

    # delete collisions
    delete_indexes.sort(reverse=True)
    for idx in delete_indexes:
        tokens.pop(idx)


def check_bytes_size(
    actual_size: int, max_size: int, label: str, prompt: bool = True
) -> tuple[bool, bool]:
    """Check the actual size and return tuple - size check result and user response"""
    if actual_size > max_size:
        title = f"Bytes in {label} definition is too long ({actual_size} > {max_size})"
        title += " and will be removed from the results" if not prompt else ""
        print(f"== {title} ==")

        if prompt:
            answer = click.prompt(
                "Do you want to remove this definition? If not, this whole process will stop:",
                type=click.Choice(["y", "n"]),
                show_choices=True,
                default="y",
                show_default=True,
            )
            return False, answer == "y"
        else:
            return False, True

    return True, True


def check_string_size(
    definition: dict, field_name: str, max_size: int, prompt: bool = True
) -> bool:
    """Check encoded size of a string from \"definition[field_name]\" and return result combined with user response."""
    encoded_size = len(definition[field_name].encode())
    if encoded_size > max_size - 1:
        title = f'Size of encoded string field "{field_name}" is too long ({encoded_size} > {max_size - 1})'
        title += " and will be shortened to fit in" if not prompt else ""
        print(f"== {title} ==")
        print(json.dumps(definition, sort_keys=True, indent=None))

        if prompt:
            answer = click.prompt(
                "Do you want to shorten this string? If not, this whole definition will be removed from the results:",
                type=click.Choice(["y", "n"]),
                show_choices=True,
                default="y",
                show_default=True,
            )
            if answer == "n":
                return False

        definition[field_name] = definition[field_name][: max_size - 1]

    return True


def check_networks_fields_sizes(networks: list[dict], interactive: bool) -> None:
    """Check sizes of embeded network fields for Trezor model 1 based on "legacy/firmware/protob/messages-ethereum.options"."""
    # EthereumNetworkInfo.name     max_size:256
    # EthereumNetworkInfo.shortcut max_size:256
    to_remove: list[int] = []
    for idx, network in enumerate(networks):
        if not check_string_size(
            network, "name", 256, interactive
        ) or not check_string_size(network, "shortcut", 256, interactive):
            to_remove.append(idx)

    # delete networks with too big field sizes
    to_remove.sort(reverse=True)
    for idx in to_remove:
        networks.pop(idx)


def check_tokens_fields_sizes(tokens: list[dict], interactive: bool) -> bool:
    """Check sizes of embeded token fields for Trezor model 1 based on "legacy/firmware/protob/messages-ethereum.options"."""
    # EthereumTokenInfo.name    max_size:256
    # EthereumTokenInfo.symbol  max_size:256 (here stored under "shortcut")
    # EthereumTokenInfo.address max_size:20
    to_remove: list[int] = []
    invalid_address_size_found = False
    for idx, token in enumerate(tokens):
        check, action = check_bytes_size(
            len(bytes.fromhex(token["address"][2:])),
            20,
            f"token {token['name']} (chain_id={token['chain_id']}, address={token['address']})",
            interactive,
        )
        if not check:
            if action:
                to_remove.append(idx)
                continue
            else:
                invalid_address_size_found = True

        if not check_string_size(
            token, "name", 256, interactive
        ) or not check_string_size(token, "shortcut", 256, interactive):
            to_remove.append(idx)

    # if we found invalid address size we cannot proceed further
    if invalid_address_size_found:
        return False

    # delete tokens with too big field sizes
    to_remove.sort(reverse=True)
    for idx in to_remove:
        tokens.pop(idx)

    return True


def check_definitions_list(
    old_defs: list[dict],
    new_defs: list[dict],
    main_keys: list[str],
    def_name: str,
    interactive: bool,
    force: bool,
    top100_coingecko_ids: list[str] | None = None,
) -> bool:
    check_ok = True
    # store already processed definitions
    deleted_definitions: list[dict] = []
    modified_definitions: list[dict] = []
    moved_definitions: list[tuple] = []
    resurrected_definitions: list[tuple] = []

    # dicts of new definitions
    defs_hash_no_metadata = {}
    defs_hash_no_main_keys_and_metadata = {}
    defs_hash_only_main_keys = {}
    for nd in new_defs:
        defs_hash_no_metadata[hash_dict_on_keys(nd, exclude_keys=["metadata"])] = nd
        defs_hash_no_main_keys_and_metadata[
            hash_dict_on_keys(nd, exclude_keys=main_keys + ["metadata"])
        ] = nd
        defs_hash_only_main_keys[hash_dict_on_keys(nd, main_keys)] = nd

    # dict of old definitions
    old_defs_hash_only_main_keys = {
        hash_dict_on_keys(d, main_keys): d for d in old_defs
    }

    # mark all resurrected, moved, modified or deleted definitions
    for old_def in old_defs:
        old_def_hash_only_main_keys = hash_dict_on_keys(old_def, main_keys)
        old_def_hash_no_metadata = hash_dict_on_keys(old_def, exclude_keys=["metadata"])
        old_def_hash_no_main_keys_and_metadata = hash_dict_on_keys(
            old_def, exclude_keys=main_keys + ["metadata"]
        )

        was_deleted_status = get_definition_deleted_status(old_def)

        if old_def_hash_no_metadata in defs_hash_no_metadata:
            # same definition found, check if it was not marked as deleted before
            if was_deleted_status:
                resurrected_definitions.append(old_def)
            else:
                # definition is unchanged, copy its metadata
                old_def_metadata = old_def.get("metadata")
                if old_def_metadata:
                    defs_hash_no_metadata[old_def_hash_no_metadata][
                        "metadata"
                    ] = old_def_metadata
        elif (
            old_def_hash_no_main_keys_and_metadata
            in defs_hash_no_main_keys_and_metadata
        ):
            # definition was moved
            # check if there was something before on this "position"
            new_def = defs_hash_no_main_keys_and_metadata[
                old_def_hash_no_main_keys_and_metadata
            ]
            new_def_hash_only_main_keys = hash_dict_on_keys(new_def, main_keys)
            orig_def = old_defs_hash_only_main_keys.get(new_def_hash_only_main_keys)

            # check if the move is valid - "old_def" is not marked as deleted
            # and there was a change in the original definition
            if (
                orig_def is None
                or not was_deleted_status
                or hash_dict_on_keys(orig_def, exclude_keys=["metadata"])
                != hash_dict_on_keys(new_def, exclude_keys=["metadata"])
            ):
                moved_definitions.append((old_def, new_def, orig_def))
            else:
                # invalid move - this was an old move so we have to check if anything else
                # is coming to "old_def" position
                if old_def_hash_only_main_keys in defs_hash_only_main_keys:
                    modified_definitions.append(
                        (old_def, defs_hash_only_main_keys[old_def_hash_only_main_keys])
                    )
                else:
                    # no - so just maintain the "old_def"
                    new_defs.append(old_def)
        elif old_def_hash_only_main_keys in defs_hash_only_main_keys:
            # definition was modified
            modified_definitions.append(
                (old_def, defs_hash_only_main_keys[old_def_hash_only_main_keys])
            )
        else:
            # definition was not found - was it deleted before or just now?
            if not was_deleted_status:
                # definition was deleted now
                deleted_definitions.append(old_def)
            else:
                # no confirmation needed
                new_defs.append(old_def)

    # try to pair moved and modified definitions
    for old_def, new_def, orig_def in moved_definitions:
        # check if there is modified definition, that was modified to "new_def"
        # if yes it was because this "old_def" was moved to "orig_def" position
        if (orig_def, new_def) in modified_definitions:
            modified_definitions.remove((orig_def, new_def))

    def any_in_top_100(*definitions) -> bool:
        if top100_coingecko_ids is None:
            return True
        if definitions is not None:
            for d in definitions:
                if d is not None and d.get("coingecko_id") in top100_coingecko_ids:
                    return True
        return False

    # go through changes and ask for confirmation
    for old_def, new_def, orig_def in moved_definitions:
        accept_change = True
        print_change = any_in_top_100(old_def, new_def, orig_def)
        # if the change contains symbol change "--force" parameter must be used to be able to accept this change
        if (
            orig_def is not None
            and orig_def.get("shortcut") != new_def.get("shortcut")
            and not force
        ):
            logging.error(
                "\nERROR: Symbol change in this definition! To be able to approve this change re-run with `--force` argument."
            )
            accept_change = check_ok = False
            print_change = True

        answer = (
            print_definition_change(
                def_name.upper(),
                "MOVED",
                old_def,
                new_def,
                orig_def,
                prompt=interactive and accept_change,
            )
            if print_change
            else None
        )
        if answer is False or answer is None and not accept_change:
            # revert change - replace "new_def" with "old_def" and "orig_def"
            new_defs.remove(new_def)
            new_defs.append(old_def)
            new_defs.append(orig_def)
        else:
            _set_definition_metadata(new_def, old_def, main_keys)

            # if position of the "old_def" will remain empty leave on its former position a "mark"
            # that it has been deleted
            old_def_remains_empty = True
            for _, nd, _ in moved_definitions:
                if hash_dict_on_keys(old_def, main_keys) == hash_dict_on_keys(
                    nd, main_keys
                ):
                    old_def_remains_empty = False

            if old_def_remains_empty:
                _set_definition_metadata(old_def, deleted=True)
                new_defs.append(old_def)

    for old_def, new_def in modified_definitions:
        accept_change = True
        print_change = any_in_top_100(old_def, new_def)
        # if the change contains symbol change "--force" parameter must be used to be able to accept this change
        if old_def.get("shortcut") != new_def.get("shortcut") and not force:
            logging.error(
                "\nERROR: Symbol change in this definition! To be able to approve this change re-run with `--force` argument."
            )
            accept_change = check_ok = False
            print_change = True

        answer = (
            print_definition_change(
                def_name.upper(),
                "MODIFIED",
                old_def,
                new_def,
                prompt=interactive and accept_change,
            )
            if print_change
            else None
        )
        if answer is False or answer is None and not accept_change:
            # revert change - replace "new_def" with "old_def"
            new_defs.remove(new_def)
            new_defs.append(old_def)

    for definition in deleted_definitions:
        if (
            any_in_top_100(definition)
            and print_definition_change(
                def_name.upper(), "DELETED", definition, prompt=interactive
            )
            is False
        ):
            # revert change - add back the deleted definition
            new_defs.append(definition)
        else:
            _set_definition_metadata(definition, deleted=True)
            new_defs.append(definition)

    for definition in resurrected_definitions:
        if (
            any_in_top_100(definition)
            and print_definition_change(
                def_name.upper(), "RESURRECTED", definition, prompt=interactive
            )
            is not False
        ):
            # clear deleted mark
            _set_definition_metadata(definition)

    return check_ok


def _load_prepared_definitions(
    definitions_file: pathlib.Path,
) -> tuple[datetime.datetime, list[dict], list[dict]]:
    if not definitions_file.is_file():
        click.ClickException(
            f"File {definitions_file} with prepared definitions does not exists or is not a file."
        )

    prepared_definitions_data = load_json(definitions_file)
    try:
        timestamp = datetime.datetime.strptime(
            prepared_definitions_data["timestamp"], TIMESTAMP_FORMAT
        )
        networks_data = prepared_definitions_data["networks"]
        tokens_data = prepared_definitions_data["tokens"]
    except KeyError:
        click.ClickException(
            'File with prepared definitions is not complete. Whole "networks" and/or "tokens" section are missing.'
        )

    networks: Coins = []
    for network_data in networks_data:
        network_data.update(
            chain_id=network_data["chain_id"],
            key=f"eth:{network_data['shortcut']}",
        )
        networks.append(cast(Coin, network_data))

    tokens: Coins = []

    for token in tokens_data:
        token.update(
            chain_id=token["chain_id"],
            address=token["address"].lower(),
            address_bytes=bytes.fromhex(token["address"][2:]),
            symbol=token["shortcut"],
            key=f"erc20:{token['chain']}:{token['shortcut']}",
        )
        tokens.append(cast(Coin, token))

    return timestamp, networks, tokens


def load_raw_builtin_ethereum_networks() -> list[dict]:
    """Load ethereum networks from `ethereum/networks.json`"""
    return load_json("ethereum", "networks.json")


def load_raw_builtin_erc20_tokens() -> list[dict]:
    """Load ERC20 tokens from `ethereum/tokens.json`."""
    tokens_data = load_json("ethereum", "tokens.json")
    all_tokens: list[dict] = []

    for chain_id_and_chain, tokens in tokens_data.items():
        chain_id, chain = chain_id_and_chain.split(";", maxsplit=1)
        for token in tokens:
            token.update(
                chain=chain,
                chain_id=int(chain_id),
            )
            all_tokens.append(token)

    return all_tokens


def check_builtin_defs(networks: list[dict], tokens: list[dict]) -> bool:
    check_ok = True

    builtin_networks_hashes_to_dict = {
        hash_dict_on_keys(
            cast(dict, network), exclude_keys=["metadata", "coingecko_id"]
        ): cast(dict, network)
        for network in load_raw_builtin_ethereum_networks()
    }
    builtin_tokens_hashes_to_dict = {
        hash_dict_on_keys(
            cast(dict, token), exclude_keys=["metadata", "coingecko_id"]
        ): cast(dict, token)
        for token in load_raw_builtin_erc20_tokens()
    }

    networks_hashes = [
        hash_dict_on_keys(network, exclude_keys=["metadata", "coingecko_id"])
        for network in networks
    ]
    tokens_hashes = [
        hash_dict_on_keys(token, exclude_keys=["metadata", "coingecko_id"])
        for token in tokens
    ]

    for hash, definition in builtin_networks_hashes_to_dict.items():
        if hash not in networks_hashes:
            check_ok = False
            print("== BUILT-IN NETWORK DEFINITION OUTDATED ==")
            print(json.dumps(definition, sort_keys=True, indent=None))

    for hash, definition in builtin_tokens_hashes_to_dict.items():
        if hash not in tokens_hashes:
            check_ok = False
            print("== BUILT-IN TOKEN DEFINITION OUTDATED ==")
            print(json.dumps(definition, sort_keys=True, indent=None))

    return check_ok


# ====== definitions tools ======


def eth_info_from_dict(
    coin: Coin, msg_type: EthereumNetworkInfo | EthereumTokenInfo
) -> EthereumNetworkInfo | EthereumTokenInfo:
    attributes: dict[str, Any] = {}
    for field in msg_type.FIELDS.values():
        val = coin.get(field.name)

        if field.name in ("chain_id", "slip44"):
            attributes[field.name] = int(val)
        elif msg_type == EthereumTokenInfo and field.name == "address":
            attributes[field.name] = coin.get("address_bytes")
        else:
            attributes[field.name] = val

    proto = msg_type(**attributes)

    return proto


def serialize_eth_info(
    info: EthereumNetworkInfo | EthereumTokenInfo,
    data_type_num: EthereumDefinitionType,
    timestamp: datetime.datetime,
) -> bytes:
    ser = FORMAT_VERSION_BYTES
    ser += data_type_num.to_bytes(1, "big")
    ser += int(timestamp.timestamp()).to_bytes(4, "big")

    buf = io.BytesIO()
    protobuf.dump_message(buf, info)
    msg = buf.getvalue()
    # write the length of encoded protobuf message
    ser += len(msg).to_bytes(2, "big")
    ser += msg

    return ser


def get_timestamp_from_definition(definition: bytes) -> int:
    return int.from_bytes(definition[6:10], "big")


# ====== click command handlers ======


@click.group()
def cli() -> None:
    """Script for handling Ethereum definitions (networks and tokens)."""


@cli.command()
@click.option(
    "-r/-R",
    "--refresh/--no-refresh",
    default=None,
    help="Force refresh or no-refresh data. By default tries to load cached data.",
)
@click.option(
    "-i",
    "--interactive",
    is_flag=True,
    help="Ask about every change. Without this option script will automatically accept all changes to the definitions "
    "(except those in symbols, see `--force` option).",
)
@click.option(
    "-f",
    "--force",
    is_flag=True,
    help="Changes to symbols in definitions could be accepted.",
)
@click.option(
    "-s",
    "--show-all",
    is_flag=True,
    help="Show the differences of all definitions. By default only changes to top 100 definitions (by Coingecko market cap ranking) are shown.",
)
@click.option(
    "-d",
    "--deffile",
    type=click.Path(resolve_path=True, dir_okay=False, path_type=pathlib.Path),
    default="./definitions-latest.json",
    help="File where the definitions will be saved in json format. If file already exists, it is used to check "
    'the changes in definitions. Default is "./definitions-latest.json".',
)
@click.option(
    "-n",
    "--networks-dir",
    type=click.Path(
        exists=True, file_okay=False, resolve_path=True, path_type=pathlib.Path
    ),
    default=DEFS_DIR / "ethereum" / "chains",
    help="Directory pointing at cloned networks definition repo (https://github.com/ethereum-lists/chains). "
    "Defaults to `$(DEFS_DIR)/ethereum/chains` if env variable `DEFS_DIR` is set, otherwise to "
    '`"this script location"/../defs/ethereum/chains`',
)
@click.option(
    "-t",
    "--tokens-dir",
    type=click.Path(
        exists=True, file_okay=False, resolve_path=True, path_type=pathlib.Path
    ),
    default=DEFS_DIR / "ethereum" / "tokens",
    help="Directory pointing at cloned networks definition repo (https://github.com/ethereum-lists/tokens). "
    "Defaults to `$(DEFS_DIR)/ethereum/tokens` if env variable `DEFS_DIR` is set, otherwise to "
    '`"this script location"/../defs/ethereum/tokens`',
)
@click.option("-v", "--verbose", is_flag=True, help="Display more info")
def prepare_definitions(
    refresh: bool | None,
    interactive: bool,
    force: bool,
    show_all: bool,
    deffile: pathlib.Path,
    networks_dir: pathlib.Path,
    tokens_dir: pathlib.Path,
    verbose: bool,
) -> None:
    """Prepare Ethereum definitions."""
    setup_logging(verbose)

    # init Ethereum definitions downloader
    downloader = EthereumDefinitionsCachedDownloader(refresh)

    networks = _load_ethereum_networks_from_repo(networks_dir)

    # coingecko API
    cg_platforms = downloader.get_coingecko_asset_platforms()
    cg_platforms_by_chain_id: dict[int, Any] = {}
    for chain in cg_platforms:
        # We want only informations about chains, that have both chain id and coingecko id,
        # otherwise we could not link local and coingecko networks.
        if chain["chain_identifier"] is not None and chain["id"] is not None:
            cg_platforms_by_chain_id[chain["chain_identifier"]] = chain["id"]

    # defillama API
    dl_chains = downloader.get_defillama_chains()
    dl_chains_by_chain_id: dict[int, Any] = {}
    for chain in dl_chains:
        # We want only informations about chains, that have both chain id and coingecko id,
        # otherwise we could not link local and coingecko networks.
        if chain["chainId"] is not None and chain["gecko_id"] is not None:
            dl_chains_by_chain_id[chain["chainId"]] = chain["gecko_id"]

    # We will try to get as many "coingecko_id"s as possible to be able to use them afterwards
    # to load tokens from coingecko. We won't use coingecko networks, because we don't know which
    # ones are EVM based.
    coingecko_id_to_chain_id = {}
    for network in networks:
        if network.get("coingecko_id") is None:
            # first try to assign coingecko_id to local networks from coingecko via chain_id
            if network["chain_id"] in cg_platforms_by_chain_id:
                network["coingecko_id"] = cg_platforms_by_chain_id[network["chain_id"]]
            # or try to assign coingecko_id to local networks from defillama via chain_id
            elif network["chain_id"] in dl_chains_by_chain_id:
                network["coingecko_id"] = dl_chains_by_chain_id[network["chain_id"]]

        # if we found "coingecko_id" add it to the map - used later to map tokens with coingecko ids
        if network.get("coingecko_id") is not None:
            coingecko_id_to_chain_id[network["coingecko_id"]] = network["chain_id"]

    # get tokens
    cg_tokens = _load_erc20_tokens_from_coingecko(downloader, networks)
    repo_tokens = _load_erc20_tokens_from_repo(tokens_dir, networks)

    # get data used in further processing now to be able to save cache before we do any
    # token collision process and others
    # get CoinGecko coin list
    cg_coin_list = downloader.get_coingecko_coins_list()
    # get top 100 coins
    cg_top100 = downloader.get_coingecko_top100()
    # save cache
    downloader.save_cache()

    # merge tokens
    tokens: list[dict] = []
    cg_tokens_chain_id_and_address = []
    for t in cg_tokens:
        if t not in tokens:
            # add only unique tokens
            tokens.append(t)
            cg_tokens_chain_id_and_address.append((t["chain_id"], t["address"]))
    for t in repo_tokens:
        if (
            t not in tokens
            and (t["chain_id"], t["address"]) not in cg_tokens_chain_id_and_address
        ):
            # add only unique tokens and prefer CoinGecko in case of collision of chain id and token address
            tokens.append(t)

    old_defs = None
    if deffile.exists():
        # load old definitions
        old_defs = load_json(deffile)

    # check field sizes here - shortened strings can introduce new collisions
    check_networks_fields_sizes(networks, interactive)
    if not check_tokens_fields_sizes(tokens, interactive):
        return

    check_tokens_collisions(
        tokens, old_defs["tokens"] if old_defs is not None else None
    )

    # map coingecko ids to tokens
    tokens_by_chain_id_and_address = {(t["chain_id"], t["address"]): t for t in tokens}
    for coin in cg_coin_list:
        for platform_name, address in coin.get("platforms", {}).items():
            key = (coingecko_id_to_chain_id.get(platform_name), address)
            if key in tokens_by_chain_id_and_address:
                tokens_by_chain_id_and_address[key]["coingecko_id"] = coin["id"]

    # get top 100 ids
    cg_top100_ids = [d["id"] for d in cg_top100]

    # check changes in definitions
    save_results = True
    if old_defs is not None:
        # check networks and tokens
        save_results &= check_definitions_list(
            old_defs["networks"],
            networks,
            ["chain_id"],
            "network",
            interactive,
            force,
            cg_top100_ids if not show_all else None,
        )
        save_results &= check_definitions_list(
            old_defs["tokens"],
            tokens,
            ["chain_id", "address"],
            "token",
            interactive,
            force,
            cg_top100_ids if not show_all else None,
        )

    if save_results:
        # check built-in definitions against generated ones
        if not check_builtin_defs(networks, tokens):
            logging.warning("Built-in definitions differ from the generated ones.")

        # sort networks and tokens
        networks.sort(key=lambda x: x["chain_id"])
        tokens.sort(key=lambda x: (x["chain_id"], x["address"]))

        # save results
        with open(deffile, "w") as f:
            json.dump(
                obj=dict(
                    timestamp=CURRENT_TIMESTAMP_STR, networks=networks, tokens=tokens
                ),
                fp=f,
                ensure_ascii=False,
                sort_keys=True,
                indent=1,
            )
            f.write("\n")
    else:
        logging.error("Error occured - results not saved.")


@cli.command()
@click.option(
    "-d",
    "--deffile",
    type=click.Path(resolve_path=True, dir_okay=False, path_type=pathlib.Path),
    default="./definitions-latest.json",
    help='File where the prepared definitions are saved in json format. Defaults to "./definitions-latest.json".',
)
@click.option(
    "-o",
    "--outfile",
    type=click.Path(
        resolve_path=True, dir_okay=False, writable=True, path_type=pathlib.Path
    ),
    default="./definitions-latest.zip",
    help='File where the generated definitions will be saved in zip format. Any existing file will be overwritten! Defaults to "./definitions-latest.zip".',
)
@click.option(
    "-k",
    "--publickey",
    type=click.File(mode="r"),
    help="File with public key (text, hex formated) used to check the signed Merkle tree root hash. Must be used with `--signedroot` option.",
)
@click.option(
    "-s",
    "--signedroot",
    help="Signed Merkle tree root hash to be added (text, hex formated).",
)
@click.option("-v", "--verbose", is_flag=True, help="Display more info.")
@click.option(
    "-p",
    "--include-proof",
    is_flag=True,
    help="Include Merkle tree proofs into binary blobs.",
)
def sign_definitions(
    deffile: pathlib.Path,
    outfile: pathlib.Path,
    publickey: TextIO,
    signedroot: str,
    verbose: bool,
    include_proof: bool,
) -> None:
    """Generate signed Ethereum definitions for python-trezor and others.
    If ran without `--publickey` and/or `--signedroot` it prints the computed Merkle tree root hash.
    If ran with `--publickey` and `--signedroot` it checks the signed root with generated one and saves the definitions.
    """
    setup_logging(verbose)

    if (publickey is None) != (signedroot is None):
        raise click.ClickException(
            "Options `--publickey` and `--signedroot` must be used together."
        )

    # load prepared definitions
    timestamp, networks, tokens = _load_prepared_definitions(deffile)

    # serialize definitions
    for network in networks:
        ser = serialize_eth_info(
            eth_info_from_dict(network, EthereumNetworkInfo),
            EthereumDefinitionType.NETWORK,
            timestamp,
        )
        network["serialized"] = ser
    for token in tokens:
        ser = serialize_eth_info(
            eth_info_from_dict(token, EthereumTokenInfo),
            EthereumDefinitionType.TOKEN,
            timestamp,
        )
        token["serialized"] = ser

    # sort encoded definitions
    sorted_defs = [network["serialized"] for network in networks] + [
        token["serialized"] for token in tokens
    ]
    sorted_defs.sort()

    # build Merkle tree
    mt = MerkleTree(sorted_defs)

    # print or check tree root hash
    if publickey is None:
        print(f"Merkle tree root hash: {hexlify(mt.get_root_hash())}")
        return

    verify_key = ed25519.VerifyingKey(
        ed25519.from_ascii(publickey.readline(), encoding="hex")
    )
    try:
        verify_key.verify(signedroot, mt.get_root_hash(), encoding="hex")
    except ed25519.BadSignatureError:
        raise click.ClickException(
            f"Provided `--signedroot` value is not valid for computed Merkle tree root hash ({hexlify(mt.get_root_hash())})."
        )

    def save_definition(
        path: pathlib.PurePath, keys: list[str], data: bytes, zip_file: zipfile.ZipFile
    ):
        complete_path = path / ("_".join(keys) + ".dat")

        try:
            if zip_file.getinfo(str(complete_path)):
                logging.warning(
                    f'Definition "{complete_path}" already generated - attempt to generate another definition.'
                )
        except KeyError:
            pass

        zip_file.writestr(str(complete_path), data)

    def generate_token_def(
        token: Coin, base_path: pathlib.PurePath, zip_file: zipfile.ZipFile
    ):
        if token["address"] is not None and token["chain_id"] is not None:
            # save token definition
            save_definition(
                base_path / "by_chain_id" / str(token["chain_id"]),
                ["token", token["address"][2:].lower()],
                token["serialized"],
                zip_file,
            )

    def generate_network_def(
        network: Coin, base_path: pathlib.PurePath, zip_file: zipfile.ZipFile
    ):
        if network["chain_id"] is None:
            return

        # create path for networks identified by chain and slip44 ids
        network_dir = base_path / "by_chain_id" / str(network["chain_id"])
        slip44_dir = base_path / "by_slip44" / str(network["slip44"])
        # save network definition
        save_definition(network_dir, ["network"], network["serialized"], zip_file)

        # for slip44 == 60 save only Ethereum and for slip44 == 1 save only Goerli
        if network["slip44"] not in (60, 1) or network["chain_id"] in (1, 420):
            save_definition(slip44_dir, ["network"], network["serialized"], zip_file)

    def add_proof_to_def(definition: dict) -> None:
        proof = proofs_dict[definition["serialized"]]
        # append number of hashes in proof
        definition["serialized"] += len(proof).to_bytes(1, "big")
        # append proof itself
        for p in proof:
            definition["serialized"] += p

    # add proofs (if requested) and signed tree root hash, check serialized size of the definitions and add it to a zip
    signed_root_bytes = bytes.fromhex(signedroot)

    # update definitions
    proofs_dict = mt.get_proofs()

    base_path = pathlib.PurePath("definitions-latest")
    with zipfile.ZipFile(outfile, mode="w") as zip_file:
        for network in networks:
            if include_proof:
                add_proof_to_def(network)
            # append signed tree root hash
            network["serialized"] += signed_root_bytes

            network_serialized_length = len(network["serialized"])
            if not include_proof:
                # consider size of the proofs that will be added later by user before sending to the device
                network_serialized_length += mt.get_tree_height() * 32

            check, _ = check_bytes_size(
                network_serialized_length,
                1024,
                f"network {network['name']} (chain_id={network['chain_id']})",
                False,
            )
            if check:
                generate_network_def(network, base_path, zip_file)

        for token in tokens:
            if include_proof:
                add_proof_to_def(token)
            # append signed tree root hash
            token["serialized"] += signed_root_bytes

            token_serialized_length = len(token["serialized"])
            if not include_proof:
                # consider size of the proofs that will be added later by user before sending to the device
                token_serialized_length += mt.get_tree_height() * 32

            check, _ = check_bytes_size(
                token_serialized_length,
                1024,
                f"token {token['name']} (chain_id={token['chain_id']}, address={token['address']})",
                False,
            )
            if check:
                generate_token_def(token, base_path, zip_file)


@cli.command()
@click.option(
    "-t",
    "--timestamp",
    type=int,
    help="Unix timestamp to use.",
)
@click.option("-v", "--verbose", is_flag=True, help="Display more info.")
def update_timestamp(
    timestamp: int,
    verbose: bool,
) -> None:
    """Updates the latest definitions timestamp stored in `DEFS_DIR/ethereum/latest_definitions_timestamp.txt`
    to the entered one or to the one, that can be obtained from parsing an online available definitions.
    This timestamp is then injected via "mako" files into FW code.
    """
    setup_logging(verbose)

    if timestamp is None:
        zip_bytes = ethereum.download_from_url(
            ethereum.DEFS_BASE_URL + ethereum.DEFS_ZIP_FILENAME
        )

        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            timestamp = get_timestamp_from_definition(zf.read(zf.namelist().pop()))

    with open(LATEST_DEFINITIONS_TIMESTAMP_FILEPATH, "w") as f:
        logging.info(
            f"Setting the timestamp to '{timestamp}' ('{datetime.datetime.fromtimestamp(timestamp)}')."
        )
        f.write(str(timestamp) + "\n")


if __name__ == "__main__":
    cli()
