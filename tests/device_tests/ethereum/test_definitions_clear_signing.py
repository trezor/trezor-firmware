from __future__ import annotations

from binascii import hexlify
from typing import Callable

import pytest

from trezorlib import ethereum, messages
from trezorlib.debuglink import DebugSession as Session
from trezorlib.tools import parse_path

from ... import definitions
from ...input_flows import InputFlowConfirmAllWarnings

pytestmark = [pytest.mark.altcoin, pytest.mark.ethereum, pytest.mark.models("core")]

# Uniswap V3 SwapRouter02 on Ethereum mainnet
UNISWAP_V3_ROUTER2 = "0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45"

# This is not the the actual signature of exactInputSingle
# we use a fake signature because we want to test a function definition
# that the firmware does not know about!
UNISWAP_EXACT_INPUT_SINGLE_SIG_STR = "11111111"
UNISWAP_EXACT_INPUT_SINGLE_SIG = bytes.fromhex(UNISWAP_EXACT_INPUT_SINGLE_SIG_STR)

# `exactInputSingle((address,address,uint24,address,uint256,uint256,uint160))`
# Inspired from https://etherscan.io/tx/0xebe95b6b3222b9eacbf40a02947ebbc83761ee526879d0ba99fd46f54217e5db
# but set `amountOutMinimum` to a non-zero value.
UNISWAP_EXACT_INPUT_SINGLE_CALLDATA = bytes.fromhex(
    UNISWAP_EXACT_INPUT_SINGLE_SIG_STR
    + "000000000000000000000000c02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"  # tokenIn: WETH
    + "000000000000000000000000dac17f958d2ee523a2206206994597c13d831ec7"  # tokenOut: USDT
    + "0000000000000000000000000000000000000000000000000000000000000bb8"  # fee: 3000
    + "00000000000000000000000051117eb63623aee74a39b63bd9efa3a728800dbb"  # recipient
    + "000000000000000000000000000000000000000000000000002386f26fc10000"  # amountIn
    + "0000000000000000000000000000000000000000000000000000000000000010"  # amountOutMinimum
    + "0000000000000000000000000000000000000000000000000000000000000000"  # sqrtPriceLimitX96
)

# Definition for WETH on Ethereum mainnet, returned when the firmware
# requests a token definition for the tokenIn/tokenOut addresses during formatting.
WETH_TOKEN_DEFINITION = {
    "address": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
    "chain_id": 1,
    "symbol": "FAKE WETH",
    "decimals": 18,
    "name": "FAKE Wrapped Ether",
}

# ERC-7730 display format for Uniswap V3 `exactInputSingle`.
# `exactInputSingle` takes one struct parameter with 7 fields.
UNISWAP_EXACT_INPUT_SINGLE_DISPLAY_FORMAT = definitions.make_eth_erc7730_display_format(
    chain_id=1,
    address=UNISWAP_V3_ROUTER2,
    func_sig=UNISWAP_EXACT_INPUT_SINGLE_SIG,
    parameter_definitions=[
        messages.EthereumABIValueInfo(
            tuple=messages.EthereumABITupleInfo(
                fields=[
                    messages.EthereumABIValueInfo(
                        atomic=messages.EthereumABIType.ABI_ADDRESS
                    ),  # tokenIn
                    messages.EthereumABIValueInfo(
                        atomic=messages.EthereumABIType.ABI_ADDRESS
                    ),  # tokenOut
                    messages.EthereumABIValueInfo(
                        atomic=messages.EthereumABIType.ABI_UINT24
                    ),  # fee
                    messages.EthereumABIValueInfo(
                        atomic=messages.EthereumABIType.ABI_ADDRESS
                    ),  # recipient
                    messages.EthereumABIValueInfo(
                        atomic=messages.EthereumABIType.ABI_UINT256
                    ),  # amountIn
                    messages.EthereumABIValueInfo(
                        atomic=messages.EthereumABIType.ABI_UINT256
                    ),  # amountOutMinimum
                    messages.EthereumABIValueInfo(
                        atomic=messages.EthereumABIType.ABI_UINT160
                    ),  # sqrtPriceLimitX96
                ],
                is_dynamic=False,
            )
        )
    ],
    field_definitions=[
        messages.EthereumERC7730FieldInfo(
            path=messages.EthereumERC7730Path(
                path=[0, 4]
            ),  # parameter 0 (the tuple), field 4 (amountIn)
            label="FAKE Amount",
            token_path=messages.EthereumERC7730Path(
                path=[0, 0]
            ),  # parameter 0 (the tuple), field 0 (tokenIn)
            formatter=messages.EthereumERC7730FieldFormatterType.FORMATTER_TOKEN_AMOUNT,
        ),
        messages.EthereumERC7730FieldInfo(
            path=messages.EthereumERC7730Path(
                path=[0, 5]
            ),  # parameter 0 (the tuple), field 5 (amountOutMinimum)
            label="FAKE Minimum to Receive",
            token_path=messages.EthereumERC7730Path(
                path=[0, 1]
            ),  # parameter 0 (the tuple), field 1 (tokenOut)
            formatter=messages.EthereumERC7730FieldFormatterType.FORMATTER_TOKEN_AMOUNT,
        ),
        messages.EthereumERC7730FieldInfo(
            path=messages.EthereumERC7730Path(
                path=[0, 2]
            ),  # parameter 0 (the tuple), field 2 (fee)
            label="FAKE fee",
            formatter=messages.EthereumERC7730FieldFormatterType.FORMATTER_UNIT,
        ),
        messages.EthereumERC7730FieldInfo(
            path=messages.EthereumERC7730Path(
                path=[0, 3]
            ),  # parameter 0 (the tuple), field 3 (recipient)
            label="FAKE recipient",
            decimals=4,
            base="%",
            prefix=False,
            formatter=messages.EthereumERC7730FieldFormatterType.FORMATTER_ADDRESS_NAME,
        ),
    ],
)


def _make_func_def_provider(
    func_def: messages.EthereumERC7730DisplayFormatInfo,
) -> Callable[[messages.EthereumDefinitionRequest], messages.EthereumDefinitionAck]:
    def provider(
        req: messages.EthereumDefinitionRequest,
    ) -> messages.EthereumDefinitionAck:
        if not req.func_sig:
            # No func_sig means the firmware is requesting a token/network definition
            # only (e.g. from `TokenAmountFormatter` during field formatting).

            # Make sure we are returning what was actually requested.
            assert req.chain_id == WETH_TOKEN_DEFINITION["chain_id"]
            assert (
                hexlify(req.token_address).decode("ascii").lower()
                == WETH_TOKEN_DEFINITION["address"][2:].lower()
            )

            return messages.EthereumDefinitionAck(
                definitions=messages.EthereumDefinitions(
                    encoded_network=definitions.encode_eth_network(
                        chain_id=WETH_TOKEN_DEFINITION["chain_id"]
                    ),
                    encoded_tokens=[
                        definitions.encode_eth_token(**WETH_TOKEN_DEFINITION)
                    ],
                ),
            )
        else:  # Function definition was requested.
            return messages.EthereumDefinitionAck(
                definitions=messages.EthereumDefinitions(
                    encoded_erc7730_display_format=definitions.encode_eth_erc7730_display_format(
                        func_def
                    )
                ),
            )

    return provider


SIGN_TX_PARAMS = dict(
    n=parse_path("m/44h/60h/0h/0/1"),
    nonce=0x0,
    gas_price=0x14,
    gas_limit=0x14,
    to=UNISWAP_V3_ROUTER2,
    value=0x0,
    data=UNISWAP_EXACT_INPUT_SINGLE_CALLDATA,
    chain_id=1,
)


def test_definition_request_sent(session: Session) -> None:
    # when clear-signing data is present the firmware requests a function definition
    # mid-flow via EthereumDefinitionRequest; verify it is called with the right fields
    # and that signing completes when we reply with no definition
    definition_requests: list[messages.EthereumDefinitionRequest] = []

    def provider(
        req: messages.EthereumDefinitionRequest,
    ) -> messages.EthereumDefinitionAck:
        definition_requests.append(req)
        return messages.EthereumDefinitionAck(definitions=None, func_definition=None)

    with session.test_ctx as client:
        if not session.debug.legacy_debug:
            client.set_input_flow(InputFlowConfirmAllWarnings(session).get())
        ethereum.sign_tx(session, **SIGN_TX_PARAMS, definition_provider=provider)

    assert len(definition_requests) == 1
    req = definition_requests[0]
    assert req.chain_id == 1
    assert req.token_address == bytes.fromhex(UNISWAP_V3_ROUTER2[2:].lower())
    assert req.func_sig == UNISWAP_EXACT_INPUT_SINGLE_SIG


def test_definition_request_with_func_def(session: Session) -> None:
    # When we reply to EthereumDefinitionRequest with a valid function definition,
    # the firmware performs clear signing using the provided display format.
    with session.test_ctx as client:
        if not session.debug.legacy_debug:
            client.set_input_flow(InputFlowConfirmAllWarnings(session).get())
        ethereum.sign_tx(
            session,
            **SIGN_TX_PARAMS,
            definition_provider=_make_func_def_provider(
                UNISWAP_EXACT_INPUT_SINGLE_DISPLAY_FORMAT
            ),
        )


def test_definition_request_with_invalid_func_def(session: Session) -> None:
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
    bad_func_def = definitions.make_eth_erc7730_display_format(
        chain_id=UNISWAP_EXACT_INPUT_SINGLE_DISPLAY_FORMAT.chain_id,
        address=UNISWAP_EXACT_INPUT_SINGLE_DISPLAY_FORMAT.address,
        func_sig=UNISWAP_EXACT_INPUT_SINGLE_DISPLAY_FORMAT.func_sig,
        intent=UNISWAP_EXACT_INPUT_SINGLE_DISPLAY_FORMAT.intent,
        parameter_definitions=[messages.EthereumABIValueInfo(tuple=bad_tuple)],
        field_definitions=list(
            UNISWAP_EXACT_INPUT_SINGLE_DISPLAY_FORMAT.field_definitions
        ),
    )

    with session.test_ctx as client:
        if not session.debug.legacy_debug:
            client.set_input_flow(InputFlowConfirmAllWarnings(session).get())
        ethereum.sign_tx(
            session,
            **SIGN_TX_PARAMS,
            definition_provider=_make_func_def_provider(bad_func_def),
        )
