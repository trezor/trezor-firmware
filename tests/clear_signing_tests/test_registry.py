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

"""Nightly clear-signing tests: ERC-7730 registry cases against the dev definitions.

See docs/tests/clear-signing-tests.md. Run with `make -C core test_emu_clear_signing_ui`.
"""

from __future__ import annotations

import os
import typing as t
from pathlib import Path

import pytest

from trezorlib import ethereum, messages
from trezorlib.debuglink import DebugSession as Session
from trezorlib.tools import parse_path

from ..input_flows import InputFlowConfirmAllWarnings
from .registry import (
    DEFINITIONS_ENV,
    REGISTRY_ENV,
    FlowRecorder,
    RegistryCase,
    definitions_source,
    find_missing_texts,
    load_cases,
    write_result,
)

pytestmark = [
    pytest.mark.altcoin,
    pytest.mark.ethereum,
    pytest.mark.models("core"),
]

_REGISTRY = os.environ.get(REGISTRY_ENV)
_DEFINITIONS = os.environ.get(DEFINITIONS_ENV)
if not _REGISTRY or not _DEFINITIONS:
    pytest.skip(
        f"set {REGISTRY_ENV} and {DEFINITIONS_ENV} to run the clear-signing tests",
        allow_module_level=True,
    )

SOURCE = definitions_source(_DEFINITIONS)
CASES = load_cases(Path(_REGISTRY), SOURCE)
PATH = parse_path("m/44h/60h/0h/0/0")


@pytest.mark.parametrize(
    "case",
    [
        pytest.param(
            case,
            id=case.test_id,
            marks=[pytest.mark.skip(reason=case.skip_reason)]
            if case.skip_reason
            else [],
        )
        for case in CASES
    ],
)
def test_registry_case(session: Session, case: RegistryCase) -> None:
    tx = case.tx
    assert tx is not None

    model = session.test_ctx.model
    assert model is not None
    result: dict[str, t.Any] = {
        "test_id": case.test_id,
        "entity": case.entity,
        "descriptor": case.descriptor,
        "test_file": case.test_file,
        "description": case.description,
        "to": tx.to,
        "selector": tx.data[:4].hex(),
    }
    recorder = FlowRecorder()
    definitions = messages.EthereumDefinitions(
        # Mainnet is not built into the tested models.
        encoded_network=SOURCE.get_eth_network(tx.chain_id)
    )

    try:
        device_address = ethereum.get_address(
            session, PATH, encoded_network=definitions.encoded_network
        )
        with session.test_ctx as client:
            client.set_input_flow(
                recorder.wrap(
                    InputFlowConfirmAllWarnings(session, on_page=recorder.on_page).get()
                )
            )
            if tx.tx_type == 2:
                ethereum.sign_tx_eip1559(
                    session,
                    PATH,
                    nonce=tx.nonce,
                    gas_limit=tx.gas_limit,
                    to=tx.to,
                    value=tx.value,
                    data=tx.data,
                    chain_id=tx.chain_id,
                    max_gas_fee=tx.max_gas_fee,
                    max_priority_fee=tx.max_priority_fee,
                    access_list=[
                        messages.EthereumAccessList(
                            address=address, storage_keys=list(keys)
                        )
                        for address, keys in tx.access_list
                    ],
                    definitions=definitions,
                    supports_definition_request=True,
                    definition_source=SOURCE,
                )
            else:
                ethereum.sign_tx(
                    session,
                    PATH,
                    nonce=tx.nonce,
                    gas_price=tx.gas_price,
                    gas_limit=tx.gas_limit,
                    to=tx.to,
                    value=tx.value,
                    data=tx.data,
                    chain_id=tx.chain_id,
                    definitions=definitions,
                    supports_definition_request=True,
                    definition_source=SOURCE,
                )
    except Exception as e:
        result["status"] = "error"
        result["message"] = f"{type(e).__name__}: {e}"
        raise
    else:
        result["status"] = "clear_signed" if recorder.clear_signed else "blind"
        result["missing"] = find_missing_texts(
            case.expected, case.sender, device_address, recorder.pages
        )
    finally:
        result["br_names"] = recorder.br_names
        result["pages"] = recorder.pages
        write_result(model.internal_name, case, result)

    # Only errors fail the test. Blind signing is a result like clear signing: its
    # screens are compared with those of the last run, so a case that changes from one
    # to the other fails on its screens. Differences from the registry's `expected`
    # are only reported in the summary.
