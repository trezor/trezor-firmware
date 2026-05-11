from micropython import const
from ubinascii import unhexlify

from trezor.crypto import base58

from .clear_signing import (
    AddressNameFormatter,
    Atomic,
    BindingContext,
    ContainerPath,
    DisplayFormat,
    FieldDefinition,
    Struct,
    TokenAmountFormatter,
    UnitFormatter,
    parse_address,
    parse_bytes,
    parse_uint24,
    parse_uint160,
    parse_uint256,
)

# https://github.com/LedgerHQ/clear-signing-erc7730-registry/blob/master/ercs/calldata-erc20-tokens.json#L27

APPROVE_DISPLAY_FORMAT = DisplayFormat(
    binding_context=None,
    func_sig=base58.keccak_32(b"approve(address,uint256)"),
    intent="Approve",
    parameter_definitions=[
        Atomic(parse_address),  # _spender
        Atomic(parse_uint256),  # _value
    ],
    field_definitions=[
        FieldDefinition((0,), "Spender", AddressNameFormatter),
        FieldDefinition(
            (1,),
            "Amount",
            TokenAmountFormatter(
                threshold=0x8000000000000000000000000000000000000000000000000000000000000000
            ),
        ),
    ],
)
SC_FUNC_APPROVE_REVOKE_AMOUNT = const(0)

TRANSFER_DISPLAY_FORMAT = DisplayFormat(
    binding_context=None,
    func_sig=base58.keccak_32(b"transfer(address,uint256)"),
    intent="Send",
    parameter_definitions=[
        Atomic(parse_address),  # _to
        Atomic(parse_uint256),  # _value
    ],
    field_definitions=[
        FieldDefinition((0,), "To", AddressNameFormatter),
        FieldDefinition((1,), "Amount", TokenAmountFormatter),
    ],
)

ALL_DISPLAY_FORMATS = [APPROVE_DISPLAY_FORMAT, TRANSFER_DISPLAY_FORMAT]


# https://github.com/LedgerHQ/clear-signing-erc7730-registry/blob/master/registry/1inch/calldata-AggregationRouterV6.json#L9
ONEINCH_ADDRESS = unhexlify("111111125421cA6dc452d289314280a0f8842A65")
ONEINCH_CHAINS = [
    1,
    10,
    56,
    100,
    137,
    146,
    250,
    8217,
    8453,
    42161,
    43114,
    59144,
    1313161554,
]

# https://github.com/LedgerHQ/clear-signing-erc7730-registry/blob/master/registry/uniswap/calldata-UniswapV3Router02.json#L6
UNISWAP_V3_ROUTER_ADDRESS = unhexlify("68b3465833fb72A70ecDF485E0e4C7bD8665Fc45")
UNISWAP_V3_ROUTER_CHAINS = [1]

# https://github.com/LedgerHQ/clear-signing-erc7730-registry/blob/master/registry/uniswap/calldata-UniswapV3Router02.json

UNISWAP_CONTEXT = BindingContext(
    [(chain, UNISWAP_V3_ROUTER_ADDRESS) for chain in UNISWAP_V3_ROUTER_CHAINS],
)

ALL_DISPLAY_FORMATS.extend(
    [
        DisplayFormat(
            binding_context=UNISWAP_CONTEXT,
            func_sig=unhexlify("b858183f"),  # exactInput(tuple params)
            intent="Swap",
            parameter_definitions=[
                Struct(
                    (
                        parse_bytes,  # path
                        parse_address,  # recipient
                        parse_uint256,  # amountIn
                        parse_uint256,  # amountOutMinimum
                    ),
                    is_dynamic=True,
                ),  # params
            ],
            field_definitions=[
                FieldDefinition(
                    (0, 2),  # params.amountIn
                    "Amount to Send",
                    TokenAmountFormatter(
                        token_path=(0, 0, (0, 20)),  # params.path.[0:20]
                    ),
                ),
                FieldDefinition(
                    (0, 3),  # params.amountOutMinimum
                    "Minimum to Receive",
                    TokenAmountFormatter(
                        token_path=(0, 0, (-20,)),  # params.path.[-20:]
                    ),
                ),
                FieldDefinition(
                    (0, 1),  # params.recipient
                    "Beneficiary",
                    AddressNameFormatter,
                ),
            ],
        ),
        DisplayFormat(
            binding_context=UNISWAP_CONTEXT,
            func_sig=unhexlify("04e45aaf"),  # exactInputSingle(tuple params)
            intent="Swap",
            parameter_definitions=[
                Struct(
                    (
                        parse_address,  # tokenIn
                        parse_address,  # tokenOut
                        parse_uint24,  # fee
                        parse_address,  # recipient
                        parse_uint256,  # amountIn
                        parse_uint256,  # amountOutMinimum
                        parse_uint160,  # sqrtPriceLimitX96
                    ),
                    is_dynamic=False,
                ),  # params
            ],
            field_definitions=[
                FieldDefinition(
                    (0, 4),  # amountIn
                    "Send",
                    TokenAmountFormatter(
                        token_path=(0, 0),  # params.tokenIn
                    ),
                ),
                FieldDefinition(
                    (0, 5),  # amountOutMinimum
                    "Minimum to Receive",
                    TokenAmountFormatter(
                        token_path=(0, 1),  # params.tokenOut
                    ),
                ),
                FieldDefinition(
                    (0, 2),  # fee
                    "Uniswap fee",
                    UnitFormatter(decimals=4, base="%", prefix=False),
                ),
                FieldDefinition(
                    (0, 3),  # recipient
                    "Beneficiary",
                    AddressNameFormatter,
                ),
            ],
        ),
        DisplayFormat(
            binding_context=UNISWAP_CONTEXT,
            func_sig=unhexlify("09b81346"),  # exactOutput(tuple params)
            intent="Swap",
            parameter_definitions=[
                Struct(
                    (
                        parse_bytes,  # path
                        parse_address,  # recipient
                        parse_uint256,  # amountOut
                        parse_uint256,  # amountInMaximum
                    ),
                    is_dynamic=True,
                ),  # params
            ],
            field_definitions=[
                FieldDefinition(
                    (0, 3),  # params.amountInMaximum
                    "Maximum Amount In",
                    TokenAmountFormatter(
                        token_path=(0, 0, (-20,)),  # params.path.[-20:]
                    ),
                ),
                FieldDefinition(
                    (0, 2),  # params.amountOut
                    "Amount to Receive",
                    TokenAmountFormatter(
                        token_path=(0, 0, (0, 20)),  # params.path.[0:20]
                    ),
                ),
                FieldDefinition(
                    (0, 1),  # params.recipient
                    "Beneficiary",
                    AddressNameFormatter,
                ),
            ],
        ),
        DisplayFormat(
            binding_context=UNISWAP_CONTEXT,
            func_sig=unhexlify("5023b4df"),  # exactOutputSingle(tuple params)
            intent="Swap",
            parameter_definitions=[
                Struct(
                    (
                        parse_address,  # tokenIn
                        parse_address,  # tokenOut
                        parse_uint24,  # fee
                        parse_address,  # recipient
                        parse_uint256,  # amountOut
                        parse_uint256,  # amountInMaximum
                        parse_uint160,  # sqrtPriceLimitX96
                    ),
                    is_dynamic=False,
                ),  # params
            ],
            field_definitions=[
                FieldDefinition(
                    (0, 5),  # amountInMaximum
                    "Maximum Amount In",
                    TokenAmountFormatter(
                        token_path=(0, 0),  # params.tokenIn
                    ),
                ),
                FieldDefinition(
                    (0, 4),  # amountOut
                    "Amount to Receive",
                    TokenAmountFormatter(
                        token_path=(0, 1),  # params.tokenOut
                    ),
                ),
                FieldDefinition(
                    (0, 2),  # fee
                    "Uniswap fee",
                    UnitFormatter(decimals=4, base="%", prefix=False),
                ),
                FieldDefinition(
                    (0, 3),  # recipient
                    "Beneficiary",
                    AddressNameFormatter,
                ),
            ],
        ),
    ]
)
