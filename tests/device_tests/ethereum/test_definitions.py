from __future__ import annotations

from typing import Callable

import pytest

from trezorlib import ethereum
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import parse_path

from ...input_flows import InputFlowConfirmAllWarnings
from . import common
from .test_sign_typed_data import DATA as TYPED_DATA

pytestmark = [pytest.mark.altcoin, pytest.mark.ethereum]

ERC20_OPERATION = "a9059cbb000000000000000000000000574bbb36871ba6b78e27f4b4dcfb76ea0091880b0000000000000000000000000000000000000000000000000000000000000123"
ERC20_BUILTIN_TOKEN = "0xdac17f958d2ee523a2206206994597c13d831ec7"  # USDT
ERC20_FAKE_ADDRESS = "0xdddddddddddddddddddddddddddddddddddddddd"

DEFAULT_TX_PARAMS = {
    "nonce": 0x0,
    "gas_price": 0x4A817C800,
    "gas_limit": 0x5208,
    "value": 0x2540BE400,
    "to": "0x1d1c328764a41bda0492b66baa30c4a339ff85ef",
    "chain_id": 1,
    "n": parse_path("m/44h/60h/0h/0/0"),
}

DEFAULT_ERC20_PARAMS = {
    "nonce": 0x0,
    "gas_price": 0x4A817C800,
    "gas_limit": 0x5208,
    "value": 0x0,
    "chain_id": 1,
    "n": parse_path("m/44h/60h/0h/0/0"),
    "data": bytes.fromhex(ERC20_OPERATION),
}


def test_builtin(client: Client) -> None:
    # Ethereum (SLIP-44 60, chain_id 1) will sign without any definitions provided
    ethereum.sign_tx(client, **DEFAULT_TX_PARAMS)


def test_chain_id_allowed(client: Client) -> None:
    # Any chain id is allowed as long as the SLIP44 stays the same
    params = DEFAULT_TX_PARAMS.copy()
    params.update(chain_id=222222)
    ethereum.sign_tx(client, **params)


def test_slip44_disallowed(client: Client) -> None:
    # SLIP44 is not allowed without a valid network definition
    params = DEFAULT_TX_PARAMS.copy()
    params.update(n=parse_path("m/44h/66666h/0h/0/0"))
    with pytest.raises(TrezorFailure, match="Forbidden key path"):
        ethereum.sign_tx(client, **params)


def test_slip44_external(client: Client) -> None:
    # to use a non-default SLIP44, a valid network definition must be provided
    network = common.encode_network(chain_id=66666, slip44=66666)
    params = DEFAULT_TX_PARAMS.copy()
    params.update(n=parse_path("m/44h/66666h/0h/0/0"), chain_id=66666)
    ethereum.sign_tx(client, **params, definitions=common.make_defs(network, None))


def test_slip44_external_disallowed(client: Client) -> None:
    # network definition does not allow a different SLIP44
    network = common.encode_network(chain_id=66666, slip44=66666)
    params = DEFAULT_TX_PARAMS.copy()
    params.update(n=parse_path("m/44h/55555h/0h/0/0"), chain_id=66666)
    with pytest.raises(TrezorFailure, match="Forbidden key path"):
        ethereum.sign_tx(client, **params, definitions=common.make_defs(network, None))


def test_chain_id_mismatch(client: Client) -> None:
    # network definition for a different chain id will be rejected
    network = common.encode_network(chain_id=66666, slip44=60)
    params = DEFAULT_TX_PARAMS.copy()
    params.update(chain_id=55555)
    with pytest.raises(TrezorFailure, match="Network definition mismatch"):
        ethereum.sign_tx(client, **params, definitions=common.make_defs(network, None))


def test_definition_does_not_override_builtin(client: Client) -> None:
    # The builtin definition for Ethereum (SLIP44 60, chain_id 1) will be used
    # even if a valid definition with a different SLIP44 is provided
    network = common.encode_network(chain_id=1, slip44=66666)
    params = DEFAULT_TX_PARAMS.copy()
    params.update(n=parse_path("m/44h/66666h/0h/0/0"), chain_id=1)
    with pytest.raises(TrezorFailure, match="Forbidden key path"):
        ethereum.sign_tx(client, **params, definitions=common.make_defs(network, None))

    # TODO: test that the builtin definition will not show different symbol


# TODO: figure out how to test acceptance of a token definition
# all tokens are currently accepted, we would need to check the screenshots


def test_builtin_token(client: Client) -> None:
    # The builtin definition for USDT (ERC20) will be used even if not provided
    params = DEFAULT_ERC20_PARAMS.copy()
    params.update(to=ERC20_BUILTIN_TOKEN)
    ethereum.sign_tx(client, **params)
    # TODO check that USDT symbol is shown


# TODO: test_builtin_token_not_overriden (builtin definition is used even if a custom one is provided)


def test_external_token(client: Client) -> None:
    # A valid token definition must be provided to use a non-builtin token
    token = common.encode_token(address=ERC20_FAKE_ADDRESS, chain_id=1, decimals=8)
    params = DEFAULT_ERC20_PARAMS.copy()
    params.update(to=ERC20_FAKE_ADDRESS)
    ethereum.sign_tx(client, **params, definitions=common.make_defs(None, token))
    # TODO check that FakeTok symbol is shown


def test_external_chain_without_token(client: Client) -> None:
    with client:
        if not client.debug.legacy_debug:
            client.set_input_flow(InputFlowConfirmAllWarnings(client).get())
        # when using an external chains, unknown tokens are allowed
        network = common.encode_network(chain_id=66666, slip44=60)
        params = DEFAULT_ERC20_PARAMS.copy()
        params.update(to=ERC20_BUILTIN_TOKEN, chain_id=66666)
        ethereum.sign_tx(client, **params, definitions=common.make_defs(network, None))
        # TODO check that UNKN token is used, FAKE network


def test_external_chain_token_ok(client: Client) -> None:
    # when providing an external chain and matching token, everything works
    network = common.encode_network(chain_id=66666, slip44=60)
    token = common.encode_token(address=ERC20_FAKE_ADDRESS, chain_id=66666, decimals=8)
    params = DEFAULT_ERC20_PARAMS.copy()
    params.update(to=ERC20_FAKE_ADDRESS, chain_id=66666)
    ethereum.sign_tx(client, **params, definitions=common.make_defs(network, token))
    # TODO check that FakeTok is used, FAKE network


def test_external_chain_token_mismatch(client: Client) -> None:
    with client:
        if not client.debug.legacy_debug:
            client.set_input_flow(InputFlowConfirmAllWarnings(client).get())
        # when providing external defs, we explicitly allow, but not use, tokens
        # from other chains
        network = common.encode_network(chain_id=66666, slip44=60)
        token = common.encode_token(
            address=ERC20_FAKE_ADDRESS, chain_id=55555, decimals=8
        )
        params = DEFAULT_ERC20_PARAMS.copy()
        params.update(to=ERC20_FAKE_ADDRESS, chain_id=66666)
        ethereum.sign_tx(client, **params, definitions=common.make_defs(network, token))
        # TODO check that UNKN is used for token, FAKE for network


def _call_getaddress(client: Client, slip44: int, network: bytes | None) -> None:
    ethereum.get_address(
        client,
        parse_path(f"m/44h/{slip44}h/0h"),
        show_display=False,
        encoded_network=network,
    )


def _call_signmessage(client: Client, slip44: int, network: bytes | None) -> None:
    ethereum.sign_message(
        client,
        parse_path(f"m/44h/{slip44}h/0h"),
        b"hello",
        encoded_network=network,
    )


def _call_sign_typed_data(client: Client, slip44: int, network: bytes | None) -> None:
    ethereum.sign_typed_data(
        client,
        parse_path(f"m/44h/{slip44}h/0h/0/0"),
        TYPED_DATA,
        metamask_v4_compat=True,
        definitions=common.make_defs(network, None),
    )


def _call_sign_typed_data_hash(
    client: Client, slip44: int, network: bytes | None
) -> None:
    ethereum.sign_typed_data_hash(
        client,
        parse_path(f"m/44h/{slip44}h/0h/0/0"),
        b"\x00" * 32,
        b"\xff" * 32,
        encoded_network=network,
    )


MethodType = Callable[[Client, int, "bytes | None"], None]


METHODS = (
    _call_getaddress,
    _call_signmessage,
    pytest.param(_call_sign_typed_data, marks=pytest.mark.models("core")),
    pytest.param(_call_sign_typed_data_hash, marks=pytest.mark.models("legacy")),
)


@pytest.mark.parametrize("method", METHODS)
def test_method_builtin(client: Client, method: MethodType) -> None:
    # calling a method with a builtin slip44 will work
    method(client, 60, None)


@pytest.mark.parametrize("method", METHODS)
def test_method_def_missing(client: Client, method: MethodType) -> None:
    # calling a method with a slip44 that has no definition will fail
    with pytest.raises(TrezorFailure, match="Forbidden key path"):
        method(client, 66666, None)


@pytest.mark.parametrize("method", METHODS)
def test_method_external(client: Client, method: MethodType) -> None:
    # calling a method with a slip44 that has an external definition will work
    network = common.encode_network(slip44=66666)
    method(client, 66666, network)


@pytest.mark.parametrize("method", METHODS)
def test_method_external_mismatch(client: Client, method: MethodType) -> None:
    # calling a method with a slip44 that has an external definition that does not match
    # the slip44 will fail
    network = common.encode_network(slip44=77777)
    with pytest.raises(TrezorFailure, match="Network definition mismatch"):
        method(client, 66666, network)
