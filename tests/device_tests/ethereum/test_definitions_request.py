from __future__ import annotations

from binascii import hexlify
from typing import Callable

import pytest

from trezorlib import ethereum, messages
from trezorlib.debuglink import DebugSession as Session
from trezorlib.tools import parse_path

from ... import definitions
from ...input_flows import InputFlowConfirmAllWarnings
from .test_definitions import (
    FUNC_SIG_FAKE,
    UNISWAP_EXACT_INPUT_SINGLE_DISPLAY_FORMAT,
    UNISWAP_EXACT_INPUT_SINGLE_DISPLAY_FORMAT_LABELS,
    UNISWAP_V3_ROUTER2,
    UNISWAP_WETH_WETH2_CALLDATA,
    WETH2_TOKEN_DEFINITION,
    WETH_TOKEN_DEFINITION,
    get_clear_signing_sign_tx_eip1559_params,
    get_clear_signing_sign_tx_params,
    make_label_checker,
)

pytestmark = [pytest.mark.altcoin, pytest.mark.ethereum, pytest.mark.models("core")]


def _make_display_format_definition_provider(
    display_format_requests: list,
    token_requests: list,
    display_format_info: messages.EthereumDisplayFormatInfo,
    token_definitions: dict[str, dict] | None = None,
) -> Callable[[messages.EthereumDefinitionRequest], messages.EthereumDefinitionAck]:
    if token_definitions is None:
        token_definitions = {
            WETH_TOKEN_DEFINITION["address"][2:].lower(): WETH_TOKEN_DEFINITION
        }

    def provider(
        req: messages.EthereumDefinitionRequest,
    ) -> messages.EthereumDefinitionAck:
        if not req.func_sig:
            # No func_sig means the firmware is requesting a token/network definition
            # only (e.g. from `TokenAmountFormatter` during field formatting).
            token_requests.append(req)
            addr = hexlify(req.token_address).decode("ascii").lower()
            token_def = token_definitions.get(addr)
            assert token_def is not None, f"Unexpected token request for {addr}"
            assert req.chain_id == token_def["chain_id"]

            return messages.EthereumDefinitionAck(
                definitions=messages.EthereumDefinitions(
                    encoded_network=definitions.encode_eth_network(
                        chain_id=token_def["chain_id"]
                    ),
                    encoded_token=definitions.encode_eth_token(**token_def),
                ),
            )
        else:  # Display format was requested.
            display_format_requests.append(req)
            return messages.EthereumDefinitionAck(
                definitions=messages.EthereumDefinitions(
                    encoded_display_format=definitions.encode_eth_display_format(
                        display_format_info
                    )
                ),
            )

    return provider


def test_definition_request_sent(session: Session) -> None:
    # When clear signing data is present the firmware requests a display format
    # mid-flow via EthereumDefinitionRequest (if the host signaled that it supports that).
    # Verify it is called with the right fields and that signing completes
    # without clear signing when we reply with no definition.

    def provider(
        req: messages.EthereumDefinitionRequest,
    ) -> messages.EthereumDefinitionAck:
        definition_requests.append(req)
        return messages.EthereumDefinitionAck(definitions=None)

    for sign_tx, param_getter in [
        (ethereum.sign_tx, get_clear_signing_sign_tx_params),
        (ethereum.sign_tx_eip1559, get_clear_signing_sign_tx_eip1559_params),
    ]:
        on_page, assert_all_seen = make_label_checker(
            expected=set(),
            absent=UNISWAP_EXACT_INPUT_SINGLE_DISPLAY_FORMAT_LABELS
            | {"WETH", "USDT", "UNKN"},
        )

        definition_requests: list[messages.EthereumDefinitionRequest] = []
        with session.test_ctx as client:
            if not session.debug.legacy_debug:
                client.set_input_flow(
                    InputFlowConfirmAllWarnings(session, on_page=on_page).get()
                )
            sign_tx(
                session,
                **param_getter(supports_definition_request=True),
                definition_provider=provider,
            )

        assert len(definition_requests) == 1
        req = definition_requests[0]
        assert req.chain_id == 1
        assert req.token_address == bytes.fromhex(UNISWAP_V3_ROUTER2[2:].lower())
        assert req.func_sig == FUNC_SIG_FAKE

        assert_all_seen()


def test_definition_request_not_sent(session: Session) -> None:
    # When clear signing data is present the firmware does not request a display format
    # mid-flow via EthereumDefinitionRequest if the host did not signal that it supports that.

    def provider(
        req: messages.EthereumDefinitionRequest,
    ) -> messages.EthereumDefinitionAck:
        definition_requests.append(req)
        return messages.EthereumDefinitionAck(definitions=None)

    for sign_tx, param_getter in [
        (ethereum.sign_tx, get_clear_signing_sign_tx_params),
        (ethereum.sign_tx_eip1559, get_clear_signing_sign_tx_eip1559_params),
    ]:
        on_page, assert_all_seen = make_label_checker(
            expected=set(),
            absent=UNISWAP_EXACT_INPUT_SINGLE_DISPLAY_FORMAT_LABELS
            | {"WETH", "USDT", "UNKN"},
        )

        definition_requests: list[messages.EthereumDefinitionRequest] = []
        with session.test_ctx as client:
            if not session.debug.legacy_debug:
                client.set_input_flow(
                    InputFlowConfirmAllWarnings(session, on_page=on_page).get()
                )
            sign_tx(
                session,
                **param_getter(supports_definition_request=False),
                definition_provider=provider,
            )

        assert len(definition_requests) == 0

        assert_all_seen()


def test_definition_request_with_display_format(session: Session) -> None:
    # When we reply to EthereumDefinitionRequest with a valid display format,
    # the firmware performs clear signing using the provided display format.

    for sign_tx, param_getter in [
        (ethereum.sign_tx, get_clear_signing_sign_tx_params),
        (ethereum.sign_tx_eip1559, get_clear_signing_sign_tx_eip1559_params),
    ]:
        on_page, assert_all_seen = make_label_checker(
            expected=UNISWAP_EXACT_INPUT_SINGLE_DISPLAY_FORMAT_LABELS
            | {"FAKE WETH", "USDT"},
            absent={"UNKN"},
        )

        display_format_requests: list[messages.EthereumDefinitionRequest] = []
        token_requests: list[messages.EthereumDefinitionRequest] = []
        with session.test_ctx as client:
            if not session.debug.legacy_debug:
                client.set_input_flow(
                    InputFlowConfirmAllWarnings(session, on_page=on_page).get()
                )
            sign_tx(
                session,
                **param_getter(supports_definition_request=True),
                definition_provider=_make_display_format_definition_provider(
                    display_format_requests,
                    token_requests,
                    UNISWAP_EXACT_INPUT_SINGLE_DISPLAY_FORMAT,
                ),
            )
        assert_all_seen()
        assert len(display_format_requests) == 1
        assert len(token_requests) == 1  # WETH requested, built in USDT not requested


def test_definition_request_with_invalid_display_format(session: Session) -> None:
    # A definition whose tuple claims an extra field causes the firmware to fail parsing it
    # and reverting to blind signing.

    assert (
        UNISWAP_EXACT_INPUT_SINGLE_DISPLAY_FORMAT.parameter_definitions[0].tuple
        is not None
    )
    bad_tuple = messages.EthereumABITupleInfo(
        fields=[
            *UNISWAP_EXACT_INPUT_SINGLE_DISPLAY_FORMAT.parameter_definitions[
                0
            ].tuple.fields,
            # extra field — causes OutOfBounds during clear signing
            messages.EthereumABIValueInfo(atomic=messages.EthereumABIType.ABI_UINT256),
        ],
        is_dynamic=False,
    )
    bad_display_format = definitions.make_eth_display_format(
        chain_id=UNISWAP_EXACT_INPUT_SINGLE_DISPLAY_FORMAT.chain_id,
        address=UNISWAP_EXACT_INPUT_SINGLE_DISPLAY_FORMAT.address,
        func_sig=UNISWAP_EXACT_INPUT_SINGLE_DISPLAY_FORMAT.func_sig,
        intent=UNISWAP_EXACT_INPUT_SINGLE_DISPLAY_FORMAT.intent,
        parameter_definitions=[messages.EthereumABIValueInfo(tuple=bad_tuple)],
        field_definitions=list(
            UNISWAP_EXACT_INPUT_SINGLE_DISPLAY_FORMAT.field_definitions
        ),
    )

    for sign_tx, param_getter in [
        (ethereum.sign_tx, get_clear_signing_sign_tx_params),
        (ethereum.sign_tx_eip1559, get_clear_signing_sign_tx_eip1559_params),
    ]:
        on_page, assert_all_seen = make_label_checker(
            absent=UNISWAP_EXACT_INPUT_SINGLE_DISPLAY_FORMAT_LABELS
            | {"UNKN", "WETH", "USDT"},
        )

        display_format_requests: list[messages.EthereumDefinitionRequest] = []
        token_requests: list[messages.EthereumDefinitionRequest] = []
        with session.test_ctx as client:
            if not session.debug.legacy_debug:
                client.set_input_flow(
                    InputFlowConfirmAllWarnings(session, on_page=on_page).get()
                )
            sign_tx(
                session,
                **param_getter(supports_definition_request=True),
                definition_provider=_make_display_format_definition_provider(
                    display_format_requests, token_requests, bad_display_format
                ),
            )

        assert len(display_format_requests) == 1
        assert len(token_requests) == 0
        assert_all_seen()


def test_definition_request_two_tokens(session: Session) -> None:
    # When the calldata references two non-builtin tokens (WETH and WETH2),
    # the firmware sends a separate token definition request for each.
    token_defs = {
        WETH_TOKEN_DEFINITION["address"][2:].lower(): WETH_TOKEN_DEFINITION,
        WETH2_TOKEN_DEFINITION["address"][2:].lower(): WETH2_TOKEN_DEFINITION,
    }
    for sign_tx, param_getter in [
        (ethereum.sign_tx, get_clear_signing_sign_tx_params),
        (ethereum.sign_tx_eip1559, get_clear_signing_sign_tx_eip1559_params),
    ]:
        on_page, assert_all_seen = make_label_checker(
            expected=UNISWAP_EXACT_INPUT_SINGLE_DISPLAY_FORMAT_LABELS
            | {"FAKE WETH", "FAKE WETH2"},
            absent={"UNKN"},
        )
        display_format_requests: list[messages.EthereumDefinitionRequest] = []
        token_requests: list[messages.EthereumDefinitionRequest] = []
        with session.test_ctx as client:
            if not session.debug.legacy_debug:
                client.set_input_flow(
                    InputFlowConfirmAllWarnings(session, on_page=on_page).get()
                )
            sign_tx(
                session,
                **param_getter(
                    data=UNISWAP_WETH_WETH2_CALLDATA,
                    supports_definition_request=True,
                ),
                definition_provider=_make_display_format_definition_provider(
                    display_format_requests,
                    token_requests,
                    UNISWAP_EXACT_INPUT_SINGLE_DISPLAY_FORMAT,
                    token_definitions=token_defs,
                ),
            )
        assert_all_seen()
        assert len(display_format_requests) == 1
        assert len(token_requests) == 2


# --- Test descriptor (debug-only built-ins) token-definition handling ---
#
# The "Trezor Test" descriptors are *built-in* display formats, so the firmware
# does NOT request a display format for them. Of the four, two carry non-built-in
# tokenAmount tokens that each trigger a TOKEN definition request mid-flow
# (EthereumDefinitionRequest with no func_sig):
#   * TREZOR_TEST_TOKEN_DESCRIPTOR (7e577e02): the token_path token and the
#     const_token_address.
#   * TREZOR_TEST_PATHS_DESCRIPTOR (7e577e04): the two bytes-slice tokens and a
#     nested-struct token; the native-currency token (negative-index struct) is
#     NOT requested.
# The two tests below sign both descriptors and cover the non-responsive and
# responsive replies. The calldata is deliberately DIFFERENT from the
# non-interactive signing fixtures (sign_tx_clear_signing.json) so the scenarios
# are distinct.

TEST_DESCRIPTOR_ADDRESS = "0xdddddddddddddddddddddddddddddddddddddddd"
TEST_DESCRIPTOR_CHAIN_ID = 1
# Non-built-in token addresses the descriptors ask the host to resolve.
TEST_DESCRIPTOR_TOKENS = {
    "2222222222222222222222222222222222222222",  # token_path token
    "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",  # const_token_address
    "4444444444444444444444444444444444444444",  # packedPath[0:20] slice
    "5555555555555555555555555555555555555555",  # packedPath[-20:] slice
    "6666666666666666666666666666666666666666",  # swapData[0].sendingAssetId
}
# The native-currency sentinel (swapData[-1].receivingAssetId): never requested.
TEST_DESCRIPTOR_NATIVE = "0000000000000000000000000000000000000000"
# Token descriptor: token_path token 0x22.., constTokenAmount -> const 0xee..
TEST_TOKEN_CALLDATA = bytes.fromhex(
    "7e577e02"
    "0000000000000000000000002222222222222222222222222222222222222222"
    "00000000000000000000000000000000000000000000000000000000003d0900"
    "00000000000000000000000000000000000000000000000000000000004c4b40"
)
# Paths descriptor: packedPath 0x44..||0x55.., swapData
# [(0x66,0x77,6.0),(0x88,native,1.5 ETH)] - native sentinel is never requested.
# swapData is `(address,address,uint256)[]`. The struct has no dynamic fields,
# so it is a STATIC type: per the ABI spec its elements are encoded in place
# right after the element count (stride 96), with no offset heads.
TEST_PATHS_CALLDATA = bytes.fromhex(
    "7e577e04"
    "00000000000000000000000000000000000000000000000000000000001e8480"  # amount = 2000000
    "0000000000000000000000000000000000000000000000000000000000000060"  # offset of packedPath body
    "00000000000000000000000000000000000000000000000000000000000000c0"  # offset of swapData body
    "0000000000000000000000000000000000000000000000000000000000000028"  # packedPath byte length = 40
    "4444444444444444444444444444444444444444555555555555555555555555"  # packedPath data...
    "5555555555555555000000000000000000000000000000000000000000000000"  # ...and zero padding
    "0000000000000000000000000000000000000000000000000000000000000002"  # swapData element count = 2
    "0000000000000000000000006666666666666666666666666666666666666666"  # [0].sendingAssetId
    "0000000000000000000000007777777777777777777777777777777777777777"  # [0].receivingAssetId
    "00000000000000000000000000000000000000000000000000000000005b8d80"  # [0].fromAmount = 6000000
    "0000000000000000000000008888888888888888888888888888888888888888"  # [1].sendingAssetId
    "0000000000000000000000000000000000000000000000000000000000000000"  # [1].receivingAssetId (native)
    "00000000000000000000000000000000000000000000000014d1120d7b160000"  # [1].fromAmount = 1.5 ETH
)
# Both token-bearing descriptors, signed in turn by each token-request test.
TEST_DESCRIPTOR_CALLDATAS = (TEST_TOKEN_CALLDATA, TEST_PATHS_CALLDATA)


def _test_descriptor_sign_tx(
    session: Session,
    provider: Callable[
        [messages.EthereumDefinitionRequest], messages.EthereumDefinitionAck
    ],
    calldata: bytes,
    on_page: Callable | None = None,
) -> None:
    with session.test_ctx as client:
        if not session.debug.legacy_debug and on_page is not None:
            client.set_input_flow(
                InputFlowConfirmAllWarnings(session, on_page=on_page).get()
            )
        elif not session.debug.legacy_debug:
            client.set_input_flow(InputFlowConfirmAllWarnings(session).get())
        ethereum.sign_tx(
            session,
            n=parse_path("m/44'/60'/0'/0/0"),
            nonce=0,
            gas_price=20_000_000_000,
            gas_limit=100_000,
            to=TEST_DESCRIPTOR_ADDRESS,
            value=0,
            chain_id=TEST_DESCRIPTOR_CHAIN_ID,
            data=calldata,
            definitions=messages.EthereumDefinitions(
                encoded_network=definitions.encode_eth_network(
                    chain_id=TEST_DESCRIPTOR_CHAIN_ID, slip44=60
                )
            ),
            supports_definition_request=True,
            definition_provider=provider,
        )


def test_descriptor_token_request_non_responsive(session: Session) -> None:
    # Reply with no definition: the non-built-in tokens stay unknown and render
    # "UNKN", signing still completes, and the device asked for each of those
    # token addresses on the right chain (but not the native-currency sentinel).
    token_requests: list[messages.EthereumDefinitionRequest] = []

    def provider(
        req: messages.EthereumDefinitionRequest,
    ) -> messages.EthereumDefinitionAck:
        if not req.func_sig:
            token_requests.append(req)
        return messages.EthereumDefinitionAck(definitions=None)

    on_page, assert_all_seen = make_label_checker(
        expected={"UNKN"}, absent={"FAKE TOK"}
    )
    for calldata in TEST_DESCRIPTOR_CALLDATAS:
        _test_descriptor_sign_tx(session, provider, calldata, on_page=on_page)
    assert_all_seen()

    requested = {
        hexlify(r.token_address).decode("ascii").lower() for r in token_requests
    }
    assert TEST_DESCRIPTOR_TOKENS <= requested
    assert TEST_DESCRIPTOR_NATIVE not in requested
    for r in token_requests:
        assert r.chain_id == TEST_DESCRIPTOR_CHAIN_ID


def test_descriptor_token_request_responsive(session: Session) -> None:
    # Resolve every requested token from a provided (fake) definition; the symbol
    # is then rendered for each token field and "UNKN" never appears.
    def provider(
        req: messages.EthereumDefinitionRequest,
    ) -> messages.EthereumDefinitionAck:
        # descriptor is built-in, so only token (no-func_sig) requests are expected
        assert not req.func_sig
        addr = hexlify(req.token_address).decode("ascii").lower()
        return messages.EthereumDefinitionAck(
            definitions=messages.EthereumDefinitions(
                encoded_network=definitions.encode_eth_network(
                    chain_id=TEST_DESCRIPTOR_CHAIN_ID
                ),
                encoded_token=definitions.encode_eth_token(
                    address="0x" + addr,
                    chain_id=TEST_DESCRIPTOR_CHAIN_ID,
                    symbol="FAKE TOK",
                    decimals=18,
                    name="FAKE Token",
                ),
            )
        )

    on_page, assert_all_seen = make_label_checker(
        expected={"FAKE TOK"}, absent={"UNKN"}
    )
    for calldata in TEST_DESCRIPTOR_CALLDATAS:
        _test_descriptor_sign_tx(session, provider, calldata, on_page=on_page)
    assert_all_seen()
