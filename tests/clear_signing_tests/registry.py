# This file is part of the Trezor project.
#
# Copyright (C) SatoshiLabs and contributors
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

"""Test cases of the ERC-7730 clear-signing registry, for the nightly clear-signing tests.

The cases come from the `registry/<entity>/testsv2/calldata-*.tests.json` files of
https://github.com/ethereum/clear-signing-erc7730-registry, at the commit that the last
unsigned dev deploy of trezor/definitions used. The network, display formats and tokens
come from that deploy: a local copy of its `eth/chain-id/<id>/...` tree (CI), or its URL
(only reachable from the internal network).

This module does not depend on pytest, so that `nightly.py summarize` can load
the same cases.
"""

from __future__ import annotations

import json
import re
import typing as t
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import requests

from trezorlib.definitions import FilesystemSource, Source, UrlSource

if t.TYPE_CHECKING:
    from trezorlib.debuglink import LayoutContent
    from trezorlib.testing.common import BRGeneratorType

REGISTRY_ENV = "TREZOR_CLEAR_SIGNING_REGISTRY"
DEFINITIONS_ENV = "TREZOR_CLEAR_SIGNING_DEFINITIONS"
DEV_DEFINITIONS_URL = "https://dev.firmware.sldev.cz/unsigned/v2/definitions/"

RESULTS_DIR = Path(__file__).resolve().parent / "results"

# Only mainnet for now.
CHAIN_IDS = (1,)

# Calldata longer than this is never clear-signed: see `_MAX_DATA_STORED` in
# core/src/apps/ethereum/sign_tx.py.
MAX_CLEAR_SIGNED_DATA = 6144

# The blind-signing fallback always starts with this ButtonRequest, on every layout:
# see `DataChunkConfirmer` in core/src/apps/ethereum/helpers.py.
BLIND_SIGNING_BR_NAME = "confirm_data"

TEST_FILES_GLOB = "registry/*/testsv2/calldata-*.tests.json"


# --- RLP -------------------------------------------------------------------------

RlpItem = bytes | list["RlpItem"]


def rlp_decode(data: bytes) -> RlpItem:
    item, end = _rlp_item(data, 0)
    if end != len(data):
        raise ValueError("trailing data after the RLP item")
    return item


def _rlp_payload(data: bytes, pos: int, offset: int) -> tuple[int, int]:
    """Return the start and the length of the payload of the item at `pos`."""
    prefix = data[pos]
    if prefix <= offset + 55:
        start, length = pos + 1, prefix - offset
    else:
        length_of_length = prefix - offset - 55
        start = pos + 1 + length_of_length
        if start > len(data):
            raise ValueError("truncated RLP")
        length = int.from_bytes(data[pos + 1 : start], "big")
    if start + length > len(data):
        raise ValueError("truncated RLP")
    return start, length


def _rlp_item(data: bytes, pos: int) -> tuple[RlpItem, int]:
    if pos >= len(data):
        raise ValueError("truncated RLP")
    prefix = data[pos]
    if prefix < 0x80:
        return data[pos : pos + 1], pos + 1
    if prefix < 0xC0:
        start, length = _rlp_payload(data, pos, 0x80)
        return data[start : start + length], start + length
    start, length = _rlp_payload(data, pos, 0xC0)
    end = start + length
    items: list[RlpItem] = []
    pos = start
    while pos < end:
        item, pos = _rlp_item(data, pos)
        items.append(item)
    if pos != end:
        raise ValueError("RLP list length mismatch")
    return items, end


def _rlp_bytes(item: RlpItem) -> bytes:
    if not isinstance(item, bytes):
        raise ValueError("expected an RLP string, got a list")
    return item


def _rlp_list(item: RlpItem) -> list[RlpItem]:
    if not isinstance(item, list):
        raise ValueError("expected an RLP list, got a string")
    return item


def _rlp_int(item: RlpItem) -> int:
    return int.from_bytes(_rlp_bytes(item), "big")


# --- Transactions ----------------------------------------------------------------


class UnsupportedTransaction(ValueError):
    def __init__(self, reason: str, chain_id: int | None = None) -> None:
        super().__init__(reason)
        self.chain_id = chain_id


@dataclass(frozen=True)
class Transaction:
    tx_type: int  # 0 (legacy, EIP-155) or 2 (EIP-1559)
    chain_id: int
    nonce: int
    gas_limit: int
    to: str  # 0x-prefixed, lowercase
    value: int
    data: bytes
    gas_price: int = 0  # legacy only
    max_gas_fee: int = 0  # EIP-1559 only
    max_priority_fee: int = 0  # EIP-1559 only
    access_list: tuple[tuple[str, tuple[bytes, ...]], ...] = ()


def _address(item: RlpItem, chain_id: int) -> str:
    address = _rlp_bytes(item)
    if not address:
        raise UnsupportedTransaction("contract creation", chain_id)
    if len(address) != 20:
        raise ValueError(f"invalid address length {len(address)}")
    return "0x" + address.hex()


def decode_raw_tx(raw_tx: str) -> Transaction:
    """Decode an unsigned or signed legacy (EIP-155) or EIP-1559 transaction.

    Raises `UnsupportedTransaction` (with the chain ID, if known) for transactions
    that cannot be signed by this test, and `ValueError` for malformed ones.
    """
    raw = bytes.fromhex(raw_tx.removeprefix("0x"))
    if not raw:
        raise ValueError("empty rawTx")

    if raw[0] >= 0xC0:
        fields = _rlp_list(rlp_decode(raw))
        if len(fields) == 6:
            raise UnsupportedTransaction("legacy transaction without chain ID")
        if len(fields) != 9:
            raise ValueError(f"legacy transaction with {len(fields)} fields")
        v, r, s = (_rlp_int(f) for f in fields[6:9])
        if r == 0 and s == 0:
            chain_id = v  # unsigned EIP-155
        elif v >= 35:
            chain_id = (v - 35) // 2
        else:
            raise UnsupportedTransaction("legacy transaction without chain ID")
        nonce, gas_price, gas_limit, to, value, data = fields[:6]
        return Transaction(
            tx_type=0,
            chain_id=chain_id,
            nonce=_rlp_int(nonce),
            gas_price=_rlp_int(gas_price),
            gas_limit=_rlp_int(gas_limit),
            to=_address(to, chain_id),
            value=_rlp_int(value),
            data=_rlp_bytes(data),
        )

    tx_type = raw[0]
    if tx_type > 0x7F:
        raise ValueError(f"invalid transaction type {tx_type:#x}")
    fields = _rlp_list(rlp_decode(raw[1:]))
    if not fields:
        raise ValueError("empty typed transaction")
    chain_id = _rlp_int(fields[0])
    if tx_type != 2:
        raise UnsupportedTransaction(f"transaction type {tx_type}", chain_id)
    if len(fields) not in (9, 12):
        raise ValueError(f"EIP-1559 transaction with {len(fields)} fields")
    _, nonce, max_priority_fee, max_gas_fee, gas_limit, to, value, data = fields[:8]
    access_list = []
    for entry in _rlp_list(fields[8]):
        address, storage_keys = _rlp_list(entry)
        access_list.append(
            (
                _address(address, chain_id),
                tuple(_rlp_bytes(key) for key in _rlp_list(storage_keys)),
            )
        )
    return Transaction(
        tx_type=2,
        chain_id=chain_id,
        nonce=_rlp_int(nonce),
        max_priority_fee=_rlp_int(max_priority_fee),
        max_gas_fee=_rlp_int(max_gas_fee),
        gas_limit=_rlp_int(gas_limit),
        to=_address(to, chain_id),
        value=_rlp_int(value),
        data=_rlp_bytes(data),
        access_list=tuple(access_list),
    )


# --- Definitions -----------------------------------------------------------------


class _DevUrlSource(UrlSource):
    """The dev bucket answers 403, not 404, for objects that do not exist."""

    def fetch_path(self, *components: str) -> bytes | None:
        try:
            return super().fetch_path(*components)
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code in (401, 403):
                return None
            raise


def definitions_source(location: str) -> Source:
    """A local copy of a definitions deploy, or the URL of one."""
    if location.startswith(("https://", "http://")):
        return _DevUrlSource(location.rstrip("/") + "/")
    return FilesystemSource(Path(location))


# --- Registry cases --------------------------------------------------------------


@dataclass(frozen=True)
class RegistryCase:
    test_id: str
    entity: str
    descriptor: str  # e.g. "calldata-AggregationRouterV6"
    test_file: str  # relative to the registry root
    description: str
    sender: str  # the `from` of the case
    expected: dict[str, t.Any]
    tx: Transaction | None
    skip_reason: str | None


def _slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_")


def _skip_reason(tx: Transaction, source: Source) -> str | None:
    if len(tx.data) < 4:
        return "calldata has no function selector"
    if len(tx.data) > MAX_CLEAR_SIGNED_DATA:
        return (
            f"calldata longer than {MAX_CLEAR_SIGNED_DATA} bytes is never clear-signed"
        )
    if source.get_eth_display_format(tx.chain_id, tx.to, tx.data[:4]) is None:
        return "no display format in the dev definitions"
    return None


def load_cases(registry_root: Path, source: Source) -> list[RegistryCase]:
    """Load the mainnet calldata test cases, in a stable order.

    A case that cannot run gets a `skip_reason`. Cases on other chains are left out.
    """
    cases: list[RegistryCase] = []
    seen_ids: set[str] = set()

    def add(case_id: str, **kwargs: t.Any) -> None:
        test_id = case_id
        n = 2
        while test_id in seen_ids:
            test_id = f"{case_id}_{n}"
            n += 1
        seen_ids.add(test_id)
        cases.append(RegistryCase(test_id=test_id, **kwargs))

    for test_file in sorted(registry_root.glob(TEST_FILES_GLOB)):
        entity = test_file.parent.parent.name
        descriptor = test_file.name.removesuffix(".tests.json")
        file_id = f"{_slug(entity)}__{_slug(descriptor.removeprefix('calldata-'))}"
        relative_path = test_file.relative_to(registry_root).as_posix()
        common = dict(entity=entity, descriptor=descriptor, test_file=relative_path)

        try:
            tests = json.loads(test_file.read_text())["tests"]
        except (ValueError, KeyError) as e:
            add(
                f"{file_id}__invalid",
                description="",
                sender="",
                expected={},
                tx=None,
                skip_reason=f"cannot read the test file: {e}",
                **common,
            )
            continue

        for test in tests:
            description = test.get("description", "")
            case = dict(
                description=description,
                sender=test.get("from", ""),
                expected=test.get("expected", {}),
                **common,
            )
            case_id = f"{file_id}__{_slug(description)}"
            try:
                tx = decode_raw_tx(test["rawTx"])
            except UnsupportedTransaction as e:
                if e.chain_id is not None and e.chain_id not in CHAIN_IDS:
                    continue
                add(case_id, tx=None, skip_reason=f"unsupported: {e}", **case)
                continue
            except (ValueError, KeyError) as e:
                add(case_id, tx=None, skip_reason=f"cannot decode rawTx: {e}", **case)
                continue
            if tx.chain_id not in CHAIN_IDS:
                continue
            add(case_id, tx=tx, skip_reason=_skip_reason(tx, source), **case)

    return cases


# --- Running a case --------------------------------------------------------------


@dataclass
class FlowRecorder:
    """Record the ButtonRequest names and the text of every page of a signing flow."""

    br_names: list[str] = field(default_factory=list)
    pages: list[str] = field(default_factory=list)

    def on_page(self, layout: LayoutContent) -> None:
        self.pages.append(layout.text_content())

    def wrap(
        self, input_flow: Callable[[], BRGeneratorType]
    ) -> Callable[[], BRGeneratorType]:
        def wrapped() -> BRGeneratorType:
            inner = input_flow()
            next(inner)
            while True:
                br = yield
                self.br_names.append(br.name or "")
                try:
                    inner.send(br)
                except StopIteration:
                    return

        return wrapped

    @property
    def clear_signed(self) -> bool:
        return BLIND_SIGNING_BR_NAME not in self.br_names


def _normalize(text: str) -> str:
    return re.sub(r"\s+", "", text).lower()


def find_missing_texts(
    expected: dict[str, t.Any], sender: str, device_address: str, pages: list[str]
) -> list[str]:
    """Return the expected texts (intent, owner, labels, values) that no page shows.

    This is informational: the firmware formats some values differently than the
    registry expects. Whitespace and case are ignored, and a value equal to the `from`
    of the case also matches the address of the device, which signs instead.
    """
    shown = _normalize("\n".join(pages))
    missing: list[str] = []

    def check(kind: str, *alternatives: str) -> None:
        if not any(_normalize(text) in shown for text in alternatives):
            missing.append(f"{kind}: {alternatives[0]}")

    def walk(block: dict[str, t.Any]) -> None:
        for kind in ("intent", "owner"):
            if isinstance(block.get(kind), str):
                check(kind, block[kind])
        for entry in block.get("fields", []):
            label, value = entry.get("label"), entry.get("value")
            if isinstance(label, str):
                check("label", label)
            if isinstance(value, dict):
                walk(value)
            elif isinstance(value, str):
                if sender and value.lower() == sender.lower():
                    check("value", value, device_address)
                else:
                    check("value", value)

    walk(expected)
    return missing


def write_result(model: str, case: RegistryCase, result: dict[str, t.Any]) -> None:
    path = RESULTS_DIR / model / f"{case.test_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2) + "\n")


def read_results(results_dir: Path) -> dict[str, dict[str, dict[str, t.Any]]]:
    """Read the results written by `write_result`: {model: {test_id: result}}."""
    results: dict[str, dict[str, dict[str, t.Any]]] = {}
    for path in sorted(results_dir.glob("*/*.json")):
        results.setdefault(path.parent.name, {})[path.stem] = json.loads(
            path.read_text()
        )
    return results
