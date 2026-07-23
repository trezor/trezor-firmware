from typing import Generator

from .clear_signing import (
    AddressNameFormatter,
    Atomic,
    ContainerPath,
    DisplayFormat,
    FieldDefinition,
    TokenAmountFormatter,
    parse_address,
    parse_uint256,
)

# https://github.com/LedgerHQ/clear-signing-erc7730-registry/blob/master/ercs/calldata-erc20-tokens.json#L27

APPROVE_DISPLAY_FORMAT = DisplayFormat(
    binding_context=None,
    func_sig=b"\x09\x5e\xa7\xb3",  # approve(address,uint256)
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
                token_path=ContainerPath.To,
                threshold=0x8000000000000000000000000000000000000000000000000000000000000000,
            ),
        ),
    ],
)

TRANSFER_DISPLAY_FORMAT = DisplayFormat(
    binding_context=None,
    func_sig=b"\xa9\x05\x9c\xbb",  # transfer(address,uint256)
    intent="Send",
    parameter_definitions=[
        Atomic(parse_address),  # _to
        Atomic(parse_uint256),  # _value
    ],
    field_definitions=[
        FieldDefinition((0,), "To", AddressNameFormatter),
        FieldDefinition(
            (1,), "Amount", TokenAmountFormatter(token_path=ContainerPath.To)
        ),
    ],
)


def all_display_formats() -> Generator[DisplayFormat, None, None]:

    from .clear_signing import (
        AmountFormatter,
        Array,
        BindingContext,
        DateFormatter,
        DynamicLeaf,
        RawFormatter,
        Tuple,
        UnitFormatter,
        parse_bool,
        parse_bytes,
        parse_bytes32,
        parse_string,
        parse_uint24,
        parse_uint160,
    )

    yield APPROVE_DISPLAY_FORMAT
    yield TRANSFER_DISPLAY_FORMAT

    # https://github.com/LedgerHQ/clear-signing-erc7730-registry/blob/master/registry/1inch/calldata-AggregationRouterV6.json#L9
    ONEINCH_ADDRESS = b"\x11\x11\x11\x12\x54\x21\xca\x6d\xc4\x52\xd2\x89\x31\x42\x80\xa0\xf8\x84\x2a\x65"
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

    # $.metadata.constants.addressAsEth and addressAsNull from common-AggregationRouterV6.json
    ONEINCH_NATIVE_CURRENCY_ADDRESSES = [
        b"\xee\xee\xee\xee\xee\xee\xee\xee\xee\xee\xee\xee\xee\xee\xee\xee\xee\xee\xee\xee",
        b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00",
    ]

    ONEINCH_CONTEXT = BindingContext(
        [(chain, ONEINCH_ADDRESS) for chain in ONEINCH_CHAINS],
    )

    # Rationale for the omitted "Minimum to Receive" (minReturn) field in the
    # unoswap / unoswapTo / ethUnoswap* definitions below:
    # Unlike `swap` (whose `desc` struct carries both srcToken and dstToken), these
    # functions encode only the source token; the destination token is implied by
    # the pool routing packed into the `dex` argument(s) and cannot be recovered
    # from the calldata. The ERC-7730 registry therefore gives their minReturn no
    # tokenPath, so we have no decimals/symbol to format it as a token amount and
    # omit the field rather than display a bare, tokenless integer. (`swap` keeps
    # its minReturnAmount because its dstToken is available.)

    _FUNC_SIG = b"\x07\xed\x23\x79"
    yield (
        DisplayFormat(
            binding_context=ONEINCH_CONTEXT,
            func_sig=_FUNC_SIG,
            intent="Swap",
            parameter_definitions=[
                Atomic(parse_address),  # executor
                Tuple(
                    (
                        parse_address,  # srcToken
                        parse_address,  # dstToken
                        parse_address,  # srcReceiver
                        parse_address,  # dstReceiver
                        parse_uint256,  # amount
                        parse_uint256,  # minReturnAmount
                        parse_uint256,  # flags
                    ),
                    is_dynamic=False,
                ),  # desc
                DynamicLeaf(parse_bytes),  # data
            ],
            field_definitions=[
                FieldDefinition(
                    (1, 4),  # desc.amount
                    "Amount to Send",
                    TokenAmountFormatter(
                        token_path=(1, 0),  # desc.srcToken
                        native_currency_address=ONEINCH_NATIVE_CURRENCY_ADDRESSES,
                    ),
                ),
                FieldDefinition(
                    (1, 5),  # desc.minReturnAmount
                    "Minimum to Receive",
                    TokenAmountFormatter(
                        token_path=(1, 1),  # desc.dstToken
                        native_currency_address=ONEINCH_NATIVE_CURRENCY_ADDRESSES,
                    ),
                ),
                FieldDefinition(
                    (1, 3), "Beneficiary", AddressNameFormatter  # desc.dstReceiver
                ),
            ],
        )
    )

    _FUNC_SIG = b"\x83\x80\x0a\x8e"
    yield (
        DisplayFormat(
            binding_context=ONEINCH_CONTEXT,
            func_sig=_FUNC_SIG,
            intent="Swap",
            parameter_definitions=[
                Atomic(parse_bytes32),  # token
                Atomic(parse_uint256),  # amount
                Atomic(parse_uint256),  # minReturn
                Atomic(parse_bytes32),  # dex
            ],
            field_definitions=[
                FieldDefinition(
                    (1,),  # amount
                    "Amount to Send",
                    TokenAmountFormatter(
                        token_path=(0, (-20,)),  # token.[-20:]
                        native_currency_address=ONEINCH_NATIVE_CURRENCY_ADDRESSES,
                    ),
                ),
                FieldDefinition(
                    ContainerPath.From,  # @.from
                    "Beneficiary",
                    AddressNameFormatter,
                ),
                FieldDefinition(
                    (3, (-20,)),  # dex.[-20:]
                    "Last Pool",
                    AddressNameFormatter,
                ),
            ],
        )
    )

    _FUNC_SIG = b"\xe2\xc9\x5c\x82"
    yield (
        DisplayFormat(
            binding_context=ONEINCH_CONTEXT,
            func_sig=_FUNC_SIG,
            intent="Swap",
            parameter_definitions=[
                Atomic(parse_bytes32),  # to
                Atomic(parse_bytes32),  # token
                Atomic(parse_uint256),  # amount
                Atomic(parse_uint256),  # minReturn
                Atomic(parse_bytes32),  # dex
            ],
            field_definitions=[
                FieldDefinition(
                    (2,),  # amount
                    "Amount to Send",
                    TokenAmountFormatter(
                        token_path=(1, (-20,)),  # token.[-20:]
                        native_currency_address=ONEINCH_NATIVE_CURRENCY_ADDRESSES,
                    ),
                ),
                FieldDefinition(
                    (0, (-20,)),  # to.[-20:]
                    "Beneficiary",
                    AddressNameFormatter,
                ),
                FieldDefinition(
                    (4, (-20,)),  # dex.[-20:]
                    "Last Pool",
                    AddressNameFormatter,
                ),
            ],
        )
    )

    _FUNC_SIG = b"\x87\x70\xba\x91"
    yield (
        DisplayFormat(
            binding_context=ONEINCH_CONTEXT,
            func_sig=_FUNC_SIG,
            intent="Swap",
            parameter_definitions=[
                Atomic(parse_bytes32),  # token
                Atomic(parse_uint256),  # amount
                Atomic(parse_uint256),  # minReturn
                Atomic(parse_uint256),  # dex
                Atomic(parse_bytes32),  # dex2
            ],
            field_definitions=[
                FieldDefinition(
                    (1,),  # amount
                    "Amount to Send",
                    TokenAmountFormatter(
                        token_path=(0, (-20,)),  # token.[-20:]
                        native_currency_address=ONEINCH_NATIVE_CURRENCY_ADDRESSES,
                    ),
                ),
                FieldDefinition(
                    ContainerPath.From,  # @.from
                    "Beneficiary",
                    AddressNameFormatter,
                ),
                FieldDefinition(
                    (4, (-20,)),  # dex2.[-20:]
                    "Last Pool",
                    AddressNameFormatter,
                ),
            ],
        )
    )

    _FUNC_SIG = b"\x19\x36\x74\x72"
    yield (
        DisplayFormat(
            binding_context=ONEINCH_CONTEXT,
            func_sig=_FUNC_SIG,
            intent="Swap",
            parameter_definitions=[
                Atomic(parse_bytes32),  # token
                Atomic(parse_uint256),  # amount
                Atomic(parse_uint256),  # minReturn
                Atomic(parse_uint256),  # dex
                Atomic(parse_uint256),  # dex2
                Atomic(parse_bytes32),  # dex3
            ],
            field_definitions=[
                FieldDefinition(
                    (1,),  # amount
                    "Amount to Send",
                    TokenAmountFormatter(
                        token_path=(0, (-20,)),  # token.[-20:]
                        native_currency_address=ONEINCH_NATIVE_CURRENCY_ADDRESSES,
                    ),
                ),
                FieldDefinition(
                    ContainerPath.From,  # @.from
                    "Beneficiary",
                    AddressNameFormatter,
                ),
                FieldDefinition(
                    (5, (-20,)),  # dex3.[-20:]
                    "Last Pool",
                    AddressNameFormatter,
                ),
            ],
        )
    )

    _FUNC_SIG = b"\xea\x76\xdd\xdf"
    yield (
        DisplayFormat(
            binding_context=ONEINCH_CONTEXT,
            func_sig=_FUNC_SIG,
            intent="Swap",
            parameter_definitions=[
                Atomic(parse_bytes32),  # to
                Atomic(parse_bytes32),  # token
                Atomic(parse_uint256),  # amount
                Atomic(parse_uint256),  # minReturn
                Atomic(parse_uint256),  # dex
                Atomic(parse_bytes32),  # dex2
            ],
            field_definitions=[
                FieldDefinition(
                    (2,),  # amount
                    "Amount to Send",
                    TokenAmountFormatter(
                        token_path=(1, (-20,)),  # token.[-20:]
                        native_currency_address=ONEINCH_NATIVE_CURRENCY_ADDRESSES,
                    ),
                ),
                FieldDefinition(
                    (0, (-20,)),  # to.[-20:]
                    "Beneficiary",
                    AddressNameFormatter,
                ),
                FieldDefinition(
                    (5, (-20,)),  # dex2.[-20:]
                    "Last Pool",
                    AddressNameFormatter,
                ),
            ],
        )
    )

    _FUNC_SIG = b"\xf7\xa7\x00\x56"
    yield (
        DisplayFormat(
            binding_context=ONEINCH_CONTEXT,
            func_sig=_FUNC_SIG,
            intent="Swap",
            parameter_definitions=[
                Atomic(parse_bytes32),  # to
                Atomic(parse_bytes32),  # token
                Atomic(parse_uint256),  # amount
                Atomic(parse_uint256),  # minReturn
                Atomic(parse_uint256),  # dex
                Atomic(parse_uint256),  # dex2
                Atomic(parse_bytes32),  # dex3
            ],
            field_definitions=[
                FieldDefinition(
                    (2,),  # amount
                    "Amount to Send",
                    TokenAmountFormatter(
                        token_path=(1, (-20,)),  # token.[-20:]
                        native_currency_address=ONEINCH_NATIVE_CURRENCY_ADDRESSES,
                    ),
                ),
                FieldDefinition(
                    (0, (-20,)),  # to.[-20:]
                    "Beneficiary",
                    AddressNameFormatter,
                ),
                FieldDefinition(
                    (6, (-20,)),  # dex3.[-20:]
                    "Last Pool",
                    AddressNameFormatter,
                ),
            ],
        )
    )

    _FUNC_SIG = b"\xa7\x6d\xfc\x3b"
    yield (
        DisplayFormat(
            binding_context=ONEINCH_CONTEXT,
            func_sig=_FUNC_SIG,
            intent="Swap",
            parameter_definitions=[
                Atomic(parse_uint256),  # minReturn
                Atomic(parse_bytes32),  # dex
            ],
            field_definitions=[
                FieldDefinition(
                    ContainerPath.Value,  # @.value
                    "Amount to Send",
                    AmountFormatter,
                ),
                FieldDefinition(
                    ContainerPath.From,  # @.from
                    "Beneficiary",
                    AddressNameFormatter,
                ),
                FieldDefinition(
                    (1, (-20,)),  # dex.[-20:]
                    "Last Pool",
                    AddressNameFormatter,
                ),
            ],
        )
    )

    _FUNC_SIG = b"\x89\xaf\x92\x6a"
    yield (
        DisplayFormat(
            binding_context=ONEINCH_CONTEXT,
            func_sig=_FUNC_SIG,
            intent="Swap",
            parameter_definitions=[
                Atomic(parse_uint256),  # minReturn
                Atomic(parse_uint256),  # dex
                Atomic(parse_bytes32),  # dex2
            ],
            field_definitions=[
                FieldDefinition(
                    ContainerPath.Value,  # @.value
                    "Amount to Send",
                    AmountFormatter,
                ),
                FieldDefinition(
                    ContainerPath.From,  # @.from
                    "Beneficiary",
                    AddressNameFormatter,
                ),
                FieldDefinition(
                    (2, (-20,)),  # dex2.[-20:]
                    "Last Pool",
                    AddressNameFormatter,
                ),
            ],
        )
    )

    _FUNC_SIG = b"\x18\x8a\xc3\x5d"
    yield (
        DisplayFormat(
            binding_context=ONEINCH_CONTEXT,
            func_sig=_FUNC_SIG,
            intent="Swap",
            parameter_definitions=[
                Atomic(parse_uint256),  # minReturn
                Atomic(parse_uint256),  # dex
                Atomic(parse_uint256),  # dex2
                Atomic(parse_bytes32),  # dex3
            ],
            field_definitions=[
                FieldDefinition(
                    ContainerPath.Value,  # @.value
                    "Amount to Send",
                    AmountFormatter,
                ),
                FieldDefinition(
                    ContainerPath.From,  # @.from
                    "Beneficiary",
                    AddressNameFormatter,
                ),
                FieldDefinition(
                    (3, (-20,)),  # dex3.[-20:]
                    "Last Pool",
                    AddressNameFormatter,
                ),
            ],
        )
    )

    _FUNC_SIG = b"\x17\x5a\xcc\xdc"
    yield (
        DisplayFormat(
            binding_context=ONEINCH_CONTEXT,
            func_sig=_FUNC_SIG,
            intent="Swap",
            parameter_definitions=[
                Atomic(parse_bytes32),  # to
                Atomic(parse_uint256),  # minReturn
                Atomic(parse_bytes32),  # dex
            ],
            field_definitions=[
                FieldDefinition(
                    ContainerPath.Value,  # @.value
                    "Amount to Send",
                    AmountFormatter,
                ),
                FieldDefinition(
                    (0, (-20,)),  # to.[-20:]
                    "Beneficiary",
                    AddressNameFormatter,
                ),
                FieldDefinition(
                    (2, (-20,)),  # dex.[-20:]
                    "Last Pool",
                    AddressNameFormatter,
                ),
            ],
        )
    )

    _FUNC_SIG = b"\x0f\x44\x9d\x71"
    yield (
        DisplayFormat(
            binding_context=ONEINCH_CONTEXT,
            func_sig=_FUNC_SIG,
            intent="Swap",
            parameter_definitions=[
                Atomic(parse_bytes32),  # to
                Atomic(parse_uint256),  # minReturn
                Atomic(parse_uint256),  # dex
                Atomic(parse_bytes32),  # dex2
            ],
            field_definitions=[
                FieldDefinition(
                    ContainerPath.Value,  # @.value
                    "Amount to Send",
                    AmountFormatter,
                ),
                FieldDefinition(
                    (0, (-20,)),  # to.[-20:]
                    "Beneficiary",
                    AddressNameFormatter,
                ),
                FieldDefinition(
                    (3, (-20,)),  # dex2.[-20:]
                    "Last Pool",
                    AddressNameFormatter,
                ),
            ],
        )
    )

    _FUNC_SIG = b"\x49\x31\x89\xf0"
    yield (
        DisplayFormat(
            binding_context=ONEINCH_CONTEXT,
            func_sig=_FUNC_SIG,
            intent="Swap",
            parameter_definitions=[
                Atomic(parse_bytes32),  # to
                Atomic(parse_uint256),  # minReturn
                Atomic(parse_uint256),  # dex
                Atomic(parse_uint256),  # dex2
                Atomic(parse_bytes32),  # dex3
            ],
            field_definitions=[
                FieldDefinition(
                    ContainerPath.Value,  # @.value
                    "Amount to Send",
                    AmountFormatter,
                ),
                FieldDefinition(
                    (0, (-20,)),  # to.[-20:]
                    "Beneficiary",
                    AddressNameFormatter,
                ),
                FieldDefinition(
                    (4, (-20,)),  # dex3.[-20:]
                    "Last Pool",
                    AddressNameFormatter,
                ),
            ],
        )
    )

    # https://github.com/LedgerHQ/clear-signing-erc7730-registry/blob/master/registry/uniswap/calldata-UniswapV3Router02.json#L6
    UNISWAP_V3_ROUTER_ADDRESS = b"\x68\xb3\x46\x58\x33\xfb\x72\xa7\x0e\xcd\xf4\x85\xe0\xe4\xc7\xbd\x86\x65\xfc\x45"
    UNISWAP_V3_ROUTER_CHAINS = [1]

    # https://github.com/LedgerHQ/clear-signing-erc7730-registry/blob/master/registry/uniswap/calldata-UniswapV3Router02.json

    UNISWAP_CONTEXT = BindingContext(
        [(chain, UNISWAP_V3_ROUTER_ADDRESS) for chain in UNISWAP_V3_ROUTER_CHAINS],
    )

    _FUNC_SIG = b"\xb8\x58\x18\x3f"
    yield (
        DisplayFormat(
            binding_context=UNISWAP_CONTEXT,
            func_sig=_FUNC_SIG,
            intent="Swap",
            parameter_definitions=[
                Tuple(
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
        )
    )

    _FUNC_SIG = b"\x04\xe4\x5a\xaf"
    yield (
        DisplayFormat(
            binding_context=UNISWAP_CONTEXT,
            func_sig=_FUNC_SIG,
            intent="Swap",
            parameter_definitions=[
                Tuple(
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
        )
    )

    _FUNC_SIG = b"\x09\xb8\x13\x46"
    yield (
        DisplayFormat(
            binding_context=UNISWAP_CONTEXT,
            func_sig=_FUNC_SIG,
            intent="Swap",
            parameter_definitions=[
                Tuple(
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
        )
    )

    _FUNC_SIG = b"\x50\x23\xb4\xdf"
    yield (
        DisplayFormat(
            binding_context=UNISWAP_CONTEXT,
            func_sig=_FUNC_SIG,
            intent="Swap",
            parameter_definitions=[
                Tuple(
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
        )
    )

    # Canonical WETH (Wrapped Ether) contracts holding the chain's native currency.
    # Wrapping is 1:1 and reversible, so the amounts are rendered with the native
    # currency formatter: deposit() wraps the transaction value into WETH and
    # withdraw(wad) unwraps the same amount of WETH back to the native currency.
    # https://github.com/trezor/trezor-firmware/issues/7252
    WETH_DEPLOYMENTS = [
        # https://etherscan.io/address/0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2
        (
            1,
            b"\xc0\x2a\xaa\x39\xb2\x23\xfe\x8d\x0a\x0e\x5c\x4f\x27\xea\xd9\x08\x3c\x75\x6c\xc2",
        ),
        # https://optimistic.etherscan.io/address/0x4200000000000000000000000000000000000006
        (
            10,
            b"\x42\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x06",
        ),
        # https://arbiscan.io/address/0x82aF49447D8a07e3bd95BD0d56f35241523fBab1
        (
            42161,
            b"\x82\xaf\x49\x44\x7d\x8a\x07\xe3\xbd\x95\xbd\x0d\x56\xf3\x52\x41\x52\x3f\xba\xb1",
        ),
        # https://basescan.org/address/0x4200000000000000000000000000000000000006
        (
            8453,
            b"\x42\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x06",
        ),
        # https://sepolia.etherscan.io/address/0x7b79995e5f793A07Bc00c21412e50Ecae098E7f9
        (
            11155111,
            b"\x7b\x79\x99\x5e\x5f\x79\x3a\x07\xbc\x00\xc2\x14\x12\xe5\x0e\xca\xe0\x98\xe7\xf9",
        ),
        # https://holesky.etherscan.io/address/0x94373a4919B3240D86eA41593D5eBa789FEF3848
        (
            17000,
            b"\x94\x37\x3a\x49\x19\xb3\x24\x0d\x86\xea\x41\x59\x3d\x5e\xba\x78\x9f\xef\x38\x48",
        ),
    ]

    WETH_CONTEXT = BindingContext(WETH_DEPLOYMENTS)

    yield DisplayFormat(
        binding_context=WETH_CONTEXT,
        func_sig=b"\xd0\xe3\x0d\xb0",  # deposit()
        intent="Wrap ETH to WETH",
        parameter_definitions=[],  # no arguments, the amount is the tx value
        field_definitions=[
            FieldDefinition(
                ContainerPath.Value,  # @.value
                "Amount",
                AmountFormatter,
            ),
        ],
    )

    yield DisplayFormat(
        binding_context=WETH_CONTEXT,
        func_sig=b"\x2e\x1a\x7d\x4d",  # withdraw(uint256)
        intent="Unwrap WETH to ETH",
        parameter_definitions=[
            Atomic(parse_uint256),  # wad
        ],
        field_definitions=[
            FieldDefinition(
                (0,),  # wad
                "Amount",
                AmountFormatter,
            ),
        ],
    )

    if __debug__:

        # One contract to test it all would have been easier. But Caesar has a paragraph limit.
        #   * TREZOR_TEST_SCALARS_DESCRIPTOR  - scalar/atomic formatters
        #   * TREZOR_TEST_TOKEN_DESCRIPTOR    - token-amount resolution (path + const)
        #   * TREZOR_TEST_ARRAYS_DESCRIPTOR   - multi-value arrays
        #   * TREZOR_TEST_PATHS_DESCRIPTOR    - composite path styles (slices + nested)
        TREZOR_TEST_CHAIN_ID = 1
        TREZOR_TEST_ADDRESS = b"\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd"
        TREZOR_TEST_CONST_TOKEN = b"\xee\xee\xee\xee\xee\xee\xee\xee\xee\xee\xee\xee\xee\xee\xee\xee\xee\xee\xee\xee"
        TREZOR_TEST_NATIVE = b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"

        TREZOR_TEST_CONTEXT = BindingContext(
            [(TREZOR_TEST_CHAIN_ID, TREZOR_TEST_ADDRESS)]
        )

        # --- 1) scalar / atomic formatters ---
        yield DisplayFormat(
            binding_context=TREZOR_TEST_CONTEXT,
            func_sig=b"\x7e\x57\x7e\x01",  # synthetic selector (dummy contract)
            intent="Trezor Test Scalars. DO NOT USE",
            parameter_definitions=[
                Atomic(parse_address),  # 0 recipient
                Atomic(parse_uint256),  # 1 nativeAmount
                Atomic(parse_uint256),  # 2 rawInt
                Atomic(parse_uint256),  # 3 unitValue
                Atomic(parse_uint256),  # 4 timestamp
                Atomic(parse_bytes32),  # 5 hashBytes32
                Atomic(parse_bool),  # 6 flagBool
                Atomic(parse_uint160),  # 7 sizedUint
                DynamicLeaf(parse_string),  # 8 note
                DynamicLeaf(parse_bytes),  # 9 payload
            ],
            field_definitions=[
                FieldDefinition((0,), "Recipient", AddressNameFormatter),
                FieldDefinition((1,), "Native Amount", AmountFormatter),
                FieldDefinition((2,), "Raw Integer", RawFormatter),
                FieldDefinition(
                    (3,),
                    "Unit Value",
                    UnitFormatter(decimals=2, base=" UNIT", prefix=False),
                ),
                FieldDefinition((4,), "Date", DateFormatter),
                FieldDefinition((5,), "Raw Bytes32", RawFormatter),  # parse_bytes32
                FieldDefinition((6,), "Raw Bool", RawFormatter),  # parse_bool
                FieldDefinition((7,), "Raw Uint160", RawFormatter),  # parse_uint160
                FieldDefinition((8,), "Raw String", RawFormatter),  # string passthrough
                FieldDefinition((9,), "Raw Bytes", RawFormatter),  # bytes -> hex
            ],
        )

        # --- 2) token-amount resolution: via token_path and via constant address ---
        yield DisplayFormat(
            binding_context=TREZOR_TEST_CONTEXT,
            func_sig=b"\x7e\x57\x7e\x02",  # synthetic selector (dummy contract)
            intent="Trezor Test Token. DO NOT USE",
            parameter_definitions=[
                Atomic(parse_address),  # 0 token (target of token_path below)
                Atomic(parse_uint256),  # 1 tokenAmount
                Atomic(parse_uint256),  # 2 constTokenAmount
            ],
            field_definitions=[
                FieldDefinition(
                    (1,), "Token (via path)", TokenAmountFormatter(token_path=(0,))
                ),
                FieldDefinition(
                    (2,),
                    "Token (via constant)",
                    TokenAmountFormatter(const_token_address=TREZOR_TEST_CONST_TOKEN),
                ),
            ],
        )

        # --- 3) multi-value arrays ---
        yield DisplayFormat(
            binding_context=TREZOR_TEST_CONTEXT,
            func_sig=b"\x7e\x57\x7e\x03",  # synthetic selector (dummy contract)
            intent="Trezor Test Arrays. DO NOT USE",
            parameter_definitions=[
                Array(Atomic(parse_uint256)),  # 0 amounts (multi-value array)
                Array(
                    Atomic(parse_uint256)
                ),  # 1 tokenAmounts (multi-value tokenAmount)
                Array(Atomic(parse_uint256)),  # 2 dates (multi-value date)
            ],
            field_definitions=[
                FieldDefinition(
                    (0,), "Amounts (array)", RawFormatter
                ),  # multi-value raw
                # multi-value tokenAmount sharing one constant token
                FieldDefinition(
                    (1,),
                    "Token Amounts (array)",
                    TokenAmountFormatter(const_token_address=TREZOR_TEST_CONST_TOKEN),
                ),
                FieldDefinition(
                    (2,), "Dates (array)", DateFormatter
                ),  # multi-value date
            ],
        )

        # --- 4) composite path styles: bytes slicing + nested array-of-structs ---
        yield DisplayFormat(
            binding_context=TREZOR_TEST_CONTEXT,
            func_sig=b"\x7e\x57\x7e\x04",  # synthetic selector (dummy contract)
            intent="Trezor Test Paths. DO NOT USE",
            parameter_definitions=[
                Atomic(parse_uint256),  # 0 amount (reused by both slice fields)
                DynamicLeaf(parse_bytes),  # 1 packedPath (sliced for token addresses)
                Array(  # 2 swapData: (sendingAssetId, receivingAssetId, fromAmount)[]
                    Tuple(
                        (parse_address, parse_address, parse_uint256),
                        is_dynamic=False,
                    )
                ),
            ],
            field_definitions=[
                # token_path slicing a packed bytes blob: packedPath[0:20] / [-20:]
                FieldDefinition(
                    (0,),
                    "Token (path[0:20] slice)",
                    TokenAmountFormatter(token_path=(1, (0, 20))),
                ),
                FieldDefinition(
                    (0,),
                    "Token (path[-20:] slice)",
                    TokenAmountFormatter(token_path=(1, (-20,))),
                ),
                # nested array-of-structs: swapData[0].fromAmount, token sendingAssetId
                FieldDefinition(
                    (2, 0, 2),
                    "Token (nested swap[0])",
                    TokenAmountFormatter(token_path=(2, 0, 0)),
                ),
                # negative index + native currency: swapData[-1].fromAmount, token
                # swapData[-1].receivingAssetId (the native sentinel -> renders native)
                FieldDefinition(
                    (2, -1, 2),
                    "Token (neg index swap[-1], native)",
                    TokenAmountFormatter(
                        token_path=(2, -1, 1),
                        native_currency_address=[TREZOR_TEST_NATIVE],
                    ),
                ),
            ],
        )
