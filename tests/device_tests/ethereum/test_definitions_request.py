from __future__ import annotations

from binascii import hexlify
from typing import Callable

import pytest

from trezorlib import ethereum, messages
from trezorlib.debuglink import DebugSession as Session

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
