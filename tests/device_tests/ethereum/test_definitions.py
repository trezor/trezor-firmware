from __future__ import annotations

from typing import Any, Callable

import pytest

from trezorlib import ethereum, messages
from trezorlib.debuglink import DebugSession as Session
from trezorlib.debuglink import LayoutContent
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import parse_path

from ... import definitions
from ...input_flows import InputFlowConfirmAllWarnings
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


def test_builtin(session: Session) -> None:
    # Ethereum (SLIP-44 60, chain_id 1) will sign without any definitions provided
    ethereum.sign_tx(session, **DEFAULT_TX_PARAMS)


def test_chain_id_allowed(session: Session) -> None:
    # Any chain id is allowed as long as the SLIP44 stays the same
    params = DEFAULT_TX_PARAMS.copy()
    params.update(chain_id=222222)
    ethereum.sign_tx(session, **params)


def test_slip44_disallowed(session: Session) -> None:
    # SLIP44 is not allowed without a valid network definition
    params = DEFAULT_TX_PARAMS.copy()
    params.update(n=parse_path("m/44h/66666h/0h/0/0"))
    with pytest.raises(TrezorFailure, match="Forbidden key path"):
        ethereum.sign_tx(session, **params)


def test_slip44_external(session: Session) -> None:
    # to use a non-default SLIP44, a valid network definition must be provided
    network = definitions.encode_eth_network(chain_id=66666, slip44=66666)
    params = DEFAULT_TX_PARAMS.copy()
    params.update(n=parse_path("m/44h/66666h/0h/0/0"), chain_id=66666)
    ethereum.sign_tx(
        session, **params, definitions=definitions.make_eth_defs(network, None)
    )


def test_slip44_cross_sign(session: Session) -> None:
    # any non-Ethereum mainnet network can use Ethereum derivation paths
    network = definitions.encode_eth_network(chain_id=999, slip44=1)
    params = DEFAULT_TX_PARAMS.copy()
    params.update(n=parse_path("m/44h/60h/0h/0/0"), chain_id=999)
    ethereum.sign_tx(
        session, **params, definitions=definitions.make_eth_defs(network, None)
    )


def test_slip44_external_disallowed(session: Session) -> None:
    # network definition does not allow a different SLIP44
    network = definitions.encode_eth_network(chain_id=66666, slip44=66666)
    params = DEFAULT_TX_PARAMS.copy()
    params.update(n=parse_path("m/44h/55555h/0h/0/0"), chain_id=66666)
    with pytest.raises(TrezorFailure, match="Forbidden key path"):
        ethereum.sign_tx(
            session, **params, definitions=definitions.make_eth_defs(network, None)
        )


def test_chain_id_mismatch(session: Session) -> None:
    # network definition for a different chain id will be rejected
    network = definitions.encode_eth_network(chain_id=66666, slip44=60)
    params = DEFAULT_TX_PARAMS.copy()
    params.update(chain_id=55555)
    with pytest.raises(TrezorFailure, match="Network definition mismatch"):
        ethereum.sign_tx(
            session, **params, definitions=definitions.make_eth_defs(network, None)
        )


def test_definition_does_not_override_builtin(session: Session) -> None:
    # The builtin definition for Ethereum (SLIP44 60, chain_id 1) will be used
    # even if a valid definition with a different SLIP44 is provided
    network = definitions.encode_eth_network(chain_id=1, slip44=66666)
    params = DEFAULT_TX_PARAMS.copy()
    params.update(n=parse_path("m/44h/66666h/0h/0/0"), chain_id=1)
    with pytest.raises(TrezorFailure, match="Forbidden key path"):
        ethereum.sign_tx(
            session, **params, definitions=definitions.make_eth_defs(network, None)
        )

    # TODO: test that the builtin definition will not show different symbol


# TODO: figure out how to test acceptance of a token definition
# all tokens are currently accepted, we would need to check the screenshots


def test_builtin_token(session: Session) -> None:
    # The builtin definition for USDT (ERC20) will be used even if not provided
    params = DEFAULT_ERC20_PARAMS.copy()
    params.update(to=ERC20_BUILTIN_TOKEN)
    ethereum.sign_tx(session, **params)
    # TODO check that USDT symbol is shown


# TODO: test_builtin_token_not_overriden (builtin definition is used even if a custom one is provided)


def test_external_token(session: Session) -> None:
    # A valid token definition must be provided to use a non-builtin token
    token = definitions.encode_eth_token(
        address=ERC20_FAKE_ADDRESS, chain_id=1, decimals=8
    )
    params = DEFAULT_ERC20_PARAMS.copy()
    params.update(to=ERC20_FAKE_ADDRESS)
    ethereum.sign_tx(
        session, **params, definitions=definitions.make_eth_defs(None, token)
    )
    # TODO check that FakeTok symbol is shown


def test_external_chain_without_token(session: Session) -> None:
    with session.test_ctx as client:
        if not session.debug.legacy_debug:
            client.set_input_flow(InputFlowConfirmAllWarnings(session).get())
        # when using an external chains, unknown tokens are allowed
        network = definitions.encode_eth_network(chain_id=66666, slip44=60)
        params = DEFAULT_ERC20_PARAMS.copy()
        params.update(to=ERC20_BUILTIN_TOKEN, chain_id=66666)
        ethereum.sign_tx(
            session, **params, definitions=definitions.make_eth_defs(network, None)
        )
        # TODO check that UNKN token is used, FAKE network


def test_external_chain_token_ok(session: Session) -> None:
    # when providing an external chain and matching token, everything works
    network = definitions.encode_eth_network(chain_id=66666, slip44=60)
    token = definitions.encode_eth_token(
        address=ERC20_FAKE_ADDRESS, chain_id=66666, decimals=8
    )
    params = DEFAULT_ERC20_PARAMS.copy()
    params.update(to=ERC20_FAKE_ADDRESS, chain_id=66666)
    ethereum.sign_tx(
        session, **params, definitions=definitions.make_eth_defs(network, token)
    )
    # TODO check that FakeTok is used, FAKE network


def test_external_chain_token_mismatch(session: Session) -> None:
    with session.test_ctx as client:
        if not session.debug.legacy_debug:
            client.set_input_flow(InputFlowConfirmAllWarnings(session).get())
        # when providing external defs, we explicitly allow, but not use, tokens
        # from other chains
        network = definitions.encode_eth_network(chain_id=66666, slip44=60)
        token = definitions.encode_eth_token(
            address=ERC20_FAKE_ADDRESS, chain_id=55555, decimals=8
        )
        params = DEFAULT_ERC20_PARAMS.copy()
        params.update(to=ERC20_FAKE_ADDRESS, chain_id=66666)
        ethereum.sign_tx(
            session, **params, definitions=definitions.make_eth_defs(network, token)
        )
        # TODO check that UNKN is used for token, FAKE for network


def _call_getaddress(session: Session, slip44: int, network: bytes | None) -> None:
    ethereum.get_address(
        session,
        parse_path(f"m/44h/{slip44}h/0h"),
        show_display=False,
        encoded_network=network,
    )


def _call_signmessage(session: Session, slip44: int, network: bytes | None) -> None:
    ethereum.sign_message(
        session,
        parse_path(f"m/44h/{slip44}h/0h"),
        b"hello",
        encoded_network=network,
    )


def _call_sign_typed_data(session: Session, slip44: int, network: bytes | None) -> None:
    ethereum.sign_typed_data(
        session,
        parse_path(f"m/44h/{slip44}h/0h/0/0"),
        TYPED_DATA,
        metamask_v4_compat=True,
        definitions=definitions.make_eth_defs(network, None),
    )


def _call_sign_typed_data_hash(
    session: Session, slip44: int, network: bytes | None
) -> None:
    ethereum.sign_typed_data_hash(
        session,
        parse_path(f"m/44h/{slip44}h/0h/0/0"),
        b"\x00" * 32,
        b"\xff" * 32,
        encoded_network=network,
    )


MethodType = Callable[["Session", int, "bytes | None"], None]


METHODS = (
    _call_getaddress,
    _call_signmessage,
    pytest.param(_call_sign_typed_data, marks=pytest.mark.models("core")),
    pytest.param(_call_sign_typed_data_hash, marks=pytest.mark.models("legacy")),
)


@pytest.mark.parametrize("method", METHODS)
def test_method_builtin(session: Session, method: MethodType) -> None:
    # calling a method with a builtin slip44 will work
    method(session, 60, None)


@pytest.mark.parametrize("method", METHODS)
def test_method_def_missing(session: Session, method: MethodType) -> None:
    # calling a method with a slip44 that has no definition will fail
    with pytest.raises(TrezorFailure, match="Forbidden key path"):
        method(session, 66666, None)


@pytest.mark.parametrize("method", METHODS)
def test_method_external(session: Session, method: MethodType) -> None:
    # calling a method with a slip44 that has an external definition will work
    network = definitions.encode_eth_network(slip44=66666)
    method(session, 66666, network)


@pytest.mark.parametrize("method", METHODS)
def test_method_external_mismatch(session: Session, method: MethodType) -> None:
    # calling a method with a slip44 that has an external definition that does not match
    # the slip44 will fail
    network = definitions.encode_eth_network(slip44=77777)
    with pytest.raises(TrezorFailure, match="Network definition mismatch"):
        method(session, 66666, network)


# ERC-7730 clear signing tests
# These require core models and a transaction that triggers the clear signing path.

# Uniswap V3 SwapRouter02 on Ethereum mainnet
UNISWAP_V3_ROUTER2 = "0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45"

FUNC_SIG_FAKE_STR = "11111111"
FUNC_SIG_FAKE = bytes.fromhex(FUNC_SIG_FAKE_STR)

# `exactInputSingle((address,address,uint24,address,uint256,uint256,uint160))`
# Inspired from https://etherscan.io/tx/0xebe95b6b3222b9eacbf40a02947ebbc83761ee526879d0ba99fd46f54217e5db
# but set `amountOutMinimum` to a non-zero value and using another func_sig.
UNISWAP_EXACT_INPUT_SINGLE_CALLDATA = bytes.fromhex(
    FUNC_SIG_FAKE_STR
    + "000000000000000000000000c02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"  # tokenIn: WETH
    + "000000000000000000000000dac17f958d2ee523a2206206994597c13d831ec7"  # tokenOut: USDT
    + "0000000000000000000000000000000000000000000000000000000000000bb8"  # fee: 3000
    + "00000000000000000000000051117eb63623aee74a39b63bd9efa3a728800dbb"  # recipient
    + "000000000000000000000000000000000000000000000000002386f26fc10000"  # amountIn
    + "0000000000000000000000000000000000000000000000000000000000000010"  # amountOutMinimum
    + "0000000000000000000000000000000000000000000000000000000000000000"  # sqrtPriceLimitX96
)

# WETH on Ethereum mainnet needed by TokenAmountFormatter to display amounts.
WETH_TOKEN_DEFINITION = {
    "address": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
    "chain_id": 1,
    "symbol": "FAKE WETH",
    "decimals": 18,
    "name": "FAKE Wrapped Ether",
}

# USDT on Ethereum mainnet (tokenOut in the Uniswap WETH/USDT swap calldata).
USDT_TOKEN_DEFINITION = {
    "address": "0xdac17f958d2ee523a2206206994597c13d831ec7",
    "chain_id": 1,
    "symbol": "FAKE USDT",
    "decimals": 6,
    "name": "FAKE Tether USD",
}

# Fake second WETH variant (tokenOut in the Uniswap WETH/WETH2 swap calldata).
WETH2_TOKEN_DEFINITION = {
    "address": "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
    "chain_id": 1,
    "symbol": "FAKE WETH2",
    "decimals": 18,
    "name": "FAKE Wrapped Ether 2",
}

UNISWAP_WETH_WETH2_CALLDATA = bytes.fromhex(
    FUNC_SIG_FAKE_STR
    + "000000000000000000000000c02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"  # tokenIn: WETH
    + "000000000000000000000000aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"  # tokenOut: WETH2
    + "0000000000000000000000000000000000000000000000000000000000000bb8"  # fee: 3000
    + "00000000000000000000000051117eb63623aee74a39b63bd9efa3a728800dbb"  # recipient
    + "000000000000000000000000000000000000000000000000002386f26fc10000"  # amountIn
    + "0000000000000000000000000000000000000000000000000000000000000010"  # amountOutMinimum
    + "0000000000000000000000000000000000000000000000000000000000000000"  # sqrtPriceLimitX96
)


def get_clear_signing_sign_tx_params(
    data: bytes = UNISWAP_EXACT_INPUT_SINGLE_CALLDATA,
) -> dict:
    return dict(
        n=parse_path("m/44h/60h/0h/0/1"),
        nonce=0x0,
        gas_price=0x14,
        gas_limit=0x14,
        to=UNISWAP_V3_ROUTER2,
        value=0x0,
        data=data,
        chain_id=1,
    )


# ERC-7730 display format for Uniswap V3 `exactInputSingle`.
# `exactInputSingle` takes one struct parameter with 7 fields.
UNISWAP_EXACT_INPUT_SINGLE_DISPLAY_FORMAT = definitions.make_eth_erc7730_display_format(
    chain_id=1,
    address=UNISWAP_V3_ROUTER2,
    func_sig=FUNC_SIG_FAKE,
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
            path=messages.EthereumERC7730Path(path=[0, 4]),
            label="FAKE Amount",
            token_path=messages.EthereumERC7730Path(path=[0, 0]),
            formatter=messages.EthereumERC7730FieldFormatterType.FORMATTER_TOKEN_AMOUNT,
        ),
        messages.EthereumERC7730FieldInfo(
            path=messages.EthereumERC7730Path(path=[0, 5]),
            label="FAKE Minimum to Receive",
            token_path=messages.EthereumERC7730Path(path=[0, 1]),
            formatter=messages.EthereumERC7730FieldFormatterType.FORMATTER_TOKEN_AMOUNT,
        ),
        messages.EthereumERC7730FieldInfo(
            path=messages.EthereumERC7730Path(path=[0, 2]),
            label="FAKE fee",
            formatter=messages.EthereumERC7730FieldFormatterType.FORMATTER_UNIT,
        ),
        messages.EthereumERC7730FieldInfo(
            path=messages.EthereumERC7730Path(path=[0, 3]),
            label="FAKE recipient",
            decimals=4,
            base="%",
            prefix=False,
            formatter=messages.EthereumERC7730FieldFormatterType.FORMATTER_ADDRESS_NAME,
        ),
    ],
)

UNISWAP_EXACT_INPUT_SINGLE_DISPLAY_FORMAT_LABELS = {
    f.label for f in UNISWAP_EXACT_INPUT_SINGLE_DISPLAY_FORMAT.field_definitions
}


def _sign_tx_with_display_format(
    session: Session,
    display_format: messages.EthereumDisplayFormatInfo,
    token: dict | None = None,
    sign_tx_params: dict | None = None,
    on_page: Callable[[LayoutContent], None] | None = None,
) -> None:
    if sign_tx_params is None:
        sign_tx_params = get_clear_signing_sign_tx_params()
    with session.test_ctx as client:
        if not session.debug.legacy_debug:
            client.set_input_flow(
                InputFlowConfirmAllWarnings(session, on_page=on_page).get()
            )
        ethereum.sign_tx(
            session,
            **sign_tx_params,
            definitions=messages.EthereumDefinitions(
                encoded_display_format=definitions.encode_eth_display_format(
                    display_format
                ),
                encoded_token=(
                    definitions.encode_eth_token(**token) if token is not None else None
                ),
            ),
        )


def _make_label_checker(
    expected: set[str] | None = None,
    absent: set[str] | None = None,
) -> tuple[Callable, Callable[[], None]]:
    seen: set[str] = set()
    seen_absent: set[str] = set()

    def on_page(layout: Any) -> None:
        text = layout.text_content()
        if expected:
            seen.update(label for label in expected if label in text)
        if absent:
            seen_absent.update(label for label in absent if label in text)

    on_page.seen = seen  # type: ignore[attr-defined]

    def assert_all_seen() -> None:
        assert seen == (expected or set())
        if absent:
            assert not seen_absent, f"Expected absent but found: {seen_absent}"

    return on_page, assert_all_seen


@pytest.mark.models("core")
def test_clear_signing_with_definition_and_token(session: Session) -> None:
    # With WETH provided, TokenAmountFormatter can resolve the token symbol.
    on_page, assert_all_seen = _make_label_checker(
        expected=UNISWAP_EXACT_INPUT_SINGLE_DISPLAY_FORMAT_LABELS | {"FAKE WETH"},
        absent={"UNKN"},
    )
    _sign_tx_with_display_format(
        session,
        UNISWAP_EXACT_INPUT_SINGLE_DISPLAY_FORMAT,
        token=WETH_TOKEN_DEFINITION,
        on_page=on_page,
    )
    assert_all_seen()


@pytest.mark.models("core")
def test_clear_signing_builtin_token_no_override(session: Session) -> None:
    # With USDT (tokenOut) provided as encoded_token.
    # Note however that we still render it as "USDT" (built in token)
    # rather than "FAKE USDT"!
    on_page, assert_all_seen = _make_label_checker(
        expected=UNISWAP_EXACT_INPUT_SINGLE_DISPLAY_FORMAT_LABELS | {"UNKN"},
        absent={"FAKE USDT"},
    )
    _sign_tx_with_display_format(
        session,
        UNISWAP_EXACT_INPUT_SINGLE_DISPLAY_FORMAT,
        token=USDT_TOKEN_DEFINITION,
        on_page=on_page,
    )
    assert_all_seen()


@pytest.mark.models("core")
def test_clear_signing_without_token(session: Session) -> None:
    # Without token definitions, amounts are shown as UNKNOWN tokens.
    on_page, assert_all_seen = _make_label_checker(
        expected=(UNISWAP_EXACT_INPUT_SINGLE_DISPLAY_FORMAT_LABELS | {"UNKN"}),
        absent={"WETH", "USDT"},
    )
    _sign_tx_with_display_format(
        session,
        UNISWAP_EXACT_INPUT_SINGLE_DISPLAY_FORMAT,
        sign_tx_params=get_clear_signing_sign_tx_params(UNISWAP_WETH_WETH2_CALLDATA),
        on_page=on_page,
    )
    assert_all_seen()


@pytest.mark.models("core")
def test_clear_signing_with_definition_without_token(session: Session) -> None:
    # Without a token definition, amounts are shown as UNKNOWN token
    # (but builtin USDT is resolved).
    on_page, assert_all_seen = _make_label_checker(
        expected=(UNISWAP_EXACT_INPUT_SINGLE_DISPLAY_FORMAT_LABELS | {"UNKN", "USDT"}),
        absent={"WETH"},
    )
    _sign_tx_with_display_format(
        session,
        UNISWAP_EXACT_INPUT_SINGLE_DISPLAY_FORMAT,
        on_page=on_page,
    )
    assert_all_seen()


@pytest.mark.models("core")
def test_clear_signing_with_mismatched_definition(session: Session) -> None:
    # A definition whose tuple claims an extra field causes the firmware to fail
    # parsing the calldata and fall back to blind signing.
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
    bad_display_format = definitions.make_eth_erc7730_display_format(
        chain_id=UNISWAP_EXACT_INPUT_SINGLE_DISPLAY_FORMAT.chain_id,
        address=UNISWAP_EXACT_INPUT_SINGLE_DISPLAY_FORMAT.address,
        func_sig=UNISWAP_EXACT_INPUT_SINGLE_DISPLAY_FORMAT.func_sig,
        intent=UNISWAP_EXACT_INPUT_SINGLE_DISPLAY_FORMAT.intent,
        parameter_definitions=[messages.EthereumABIValueInfo(tuple=bad_tuple)],
        field_definitions=list(
            UNISWAP_EXACT_INPUT_SINGLE_DISPLAY_FORMAT.field_definitions
        ),
    )
    on_page, assert_all_seen = _make_label_checker(
        absent=(
            UNISWAP_EXACT_INPUT_SINGLE_DISPLAY_FORMAT_LABELS | {"UNKN", "WETH", "USDT"}
        )
    )
    _sign_tx_with_display_format(session, bad_display_format, on_page=on_page)
    assert_all_seen()
