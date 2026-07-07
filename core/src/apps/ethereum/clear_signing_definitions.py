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
        Dynamic,
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
                Dynamic(parse_bytes),  # data
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

    # https://github.com/LedgerHQ/clear-signing-erc7730-registry/blob/master/registry/lifi/calldata-LIFIDiamond.json
    LIFI_ADDRESS = b"\x12\x31\xde\xb6\xf5\x74\x9e\xf6\xce\x69\x43\xa2\x75\xa1\xd3\xe7\x48\x6f\x4e\xae"
    # Chains where the LiFi diamond is deployed at the canonical LIFI_ADDRESS.
    LIFI_CHAINS = [
        1,
        10,
        25,
        56,
        100,
        106,
        122,
        137,
        204,
        250,
        252,
        288,
        1284,
        1285,
        5000,
        8453,
        9001,
        34443,
        42161,
        42170,
        42220,
        43114,
        81457,
        534352,
        1313161554,
        1666600000,
    ]
    # Chains where the LiFi diamond is deployed at a non-canonical address.
    LIFI_ALT_DEPLOYMENTS = [
        (
            324,
            b"\x34\x1e\x94\x06\x9f\x53\x23\x4f\xe6\xda\xbe\xf7\x07\xad\x42\x48\x30\x52\x57\x15",
        ),  # zkSync Era
        (
            1088,
            b"\x24\xca\x98\xfb\x69\x72\xf5\xee\x05\xf0\xdb\x00\x59\x5c\x7f\x68\xd9\xfa\xfd\x68",
        ),  # Metis
        (
            59144,
            b"\xde\x1e\x59\x8b\x81\x62\x07\x73\x45\x45\x88\xb8\x5d\x6b\x5d\x4e\xec\x32\x57\x3e",
        ),  # Linea
        (
            167004,
            b"\x3a\x9a\x5d\xba\x8f\xe1\xc4\xda\x98\x18\x7c\xe4\x75\x57\x01\xbc\xa1\x82\xf6\x3b",
        ),
    ]

    LIFI_CONTEXT = BindingContext(
        [(chain, LIFI_ADDRESS) for chain in LIFI_CHAINS] + LIFI_ALT_DEPLOYMENTS,
    )

    LIFI_NATIVE_CURRENCY_ADDRESSES = [
        b"\xee\xee\xee\xee\xee\xee\xee\xee\xee\xee\xee\xee\xee\xee\xee\xee\xee\xee\xee\xee",
        b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00",
    ]

    _FUNC_SIG = b"\x5f\xd9\xae\x2e"
    yield (
        DisplayFormat(
            binding_context=LIFI_CONTEXT,
            func_sig=_FUNC_SIG,
            intent="Swap",
            parameter_definitions=[
                Atomic(parse_bytes),  # _transactionId
                Dynamic(parse_string),  # _integrator
                Dynamic(parse_string),  # _referrer
                Atomic(parse_address),  # _receiver
                Atomic(parse_uint256),  # _minAmountOut
                Array(
                    Tuple(
                        (
                            parse_address,  # callTo
                            parse_address,  # approveTo
                            parse_address,  # sendingAssetId
                            parse_address,  # receivingAssetId
                            parse_uint256,  # fromAmount
                            parse_bytes,  # callData
                            parse_bool,  # requiresDeposit
                        ),
                        is_dynamic=False,
                    )
                ),  # _swapData
            ],
            field_definitions=[
                FieldDefinition(
                    (5, 0, 4),  # _swapData.[0].fromAmount
                    "Amount to Send",
                    TokenAmountFormatter(
                        token_path=(5, 0, 2),  # _swapData.[0].sendingAssetId
                    ),
                ),
                FieldDefinition(
                    (4,),  # _minAmountOut
                    "Minimum to Receive",
                    TokenAmountFormatter(
                        token_path=(5, -1, 3),  # _swapData.[-1].receivingAssetId
                    ),
                ),
                FieldDefinition(
                    (3,),  # _receiver
                    "Recipient",
                    AddressNameFormatter,
                ),
            ],
        )
    )

    _FUNC_SIG = b"\x2c\x57\xe8\x84"
    yield (
        DisplayFormat(
            binding_context=LIFI_CONTEXT,
            func_sig=_FUNC_SIG,
            intent="Swap",
            parameter_definitions=[
                Atomic(parse_bytes),  # _transactionId
                Dynamic(parse_string),  # _integrator
                Dynamic(parse_string),  # _referrer
                Atomic(parse_address),  # _receiver
                Atomic(parse_uint256),  # _minAmountOut
                Array(
                    Tuple(
                        (
                            parse_address,  # callTo
                            parse_address,  # approveTo
                            parse_address,  # sendingAssetId
                            parse_address,  # receivingAssetId
                            parse_uint256,  # fromAmount
                            parse_bytes,  # callData
                            parse_bool,  # requiresDeposit
                        ),
                        is_dynamic=False,
                    )
                ),  # _swapData
            ],
            field_definitions=[
                FieldDefinition(
                    (5, 0, 4),  # _swapData.[0].fromAmount
                    "Amount to Send",
                    TokenAmountFormatter(
                        token_path=(5, 0, 2),  # _swapData.[0].sendingAssetId
                    ),
                ),
                FieldDefinition(
                    (4,),  # _minAmountOut
                    "Minimum Amount to receive",
                    AmountFormatter,
                ),
                FieldDefinition(
                    (3,),  # _receiver
                    "Receiver",
                    AddressNameFormatter,
                ),
            ],
        )
    )

    _FUNC_SIG = b"\x73\x6e\xac\x0b"
    yield (
        DisplayFormat(
            binding_context=LIFI_CONTEXT,
            func_sig=_FUNC_SIG,
            intent="Swap",
            parameter_definitions=[
                Atomic(parse_bytes),  # _transactionId
                Dynamic(parse_string),  # _integrator
                Dynamic(parse_string),  # _referrer
                Atomic(parse_address),  # _receiver
                Atomic(parse_uint256),  # _minAmountOut
                Array(
                    Tuple(
                        (
                            parse_address,  # callTo
                            parse_address,  # approveTo
                            parse_address,  # sendingAssetId
                            parse_address,  # receivingAssetId
                            parse_uint256,  # fromAmount
                            parse_bytes,  # callData
                            parse_bool,  # requiresDeposit
                        ),
                        is_dynamic=False,
                    )
                ),  # _swapData
            ],
            field_definitions=[
                FieldDefinition(
                    ContainerPath.Value,  # @.value
                    "Amount to send",
                    AmountFormatter,
                ),
                FieldDefinition(
                    (4,),  # _minAmountOut
                    "Minimum to Receive",
                    TokenAmountFormatter(
                        token_path=(5, -1, 3),  # _swapData.[-1].receivingAssetId
                    ),
                ),
                FieldDefinition(
                    (3,),  # _receiver
                    "Recipient",
                    AddressNameFormatter,
                ),
            ],
        )
    )

    _FUNC_SIG = b"\x46\x66\xfc\x80"
    yield (
        DisplayFormat(
            binding_context=LIFI_CONTEXT,
            func_sig=_FUNC_SIG,
            intent="Swap",
            parameter_definitions=[
                Atomic(parse_bytes),  # _transactionId
                Dynamic(parse_string),  # _integrator
                Dynamic(parse_string),  # _referrer
                Atomic(parse_address),  # _receiver
                Atomic(parse_uint256),  # _minAmountOut
                Tuple(
                    (
                        parse_address,  # callTo
                        parse_address,  # approveTo
                        parse_address,  # sendingAssetId
                        parse_address,  # receivingAssetId
                        parse_uint256,  # fromAmount
                        parse_bytes,  # callData
                        parse_bool,  # requiresDeposit
                    ),
                    is_dynamic=True,
                ),  # _swapData
            ],
            field_definitions=[
                FieldDefinition(
                    (5, 4),  # _swapData.fromAmount
                    "Amount to Send",
                    TokenAmountFormatter(token_path=(5, 2)),  # _swapData.sendingAssetId
                ),
                FieldDefinition(
                    (4,),  # _minAmountOut
                    "Minimum to Receive",
                    TokenAmountFormatter(
                        token_path=(5, 3)
                    ),  # _swapData.receivingAssetId
                ),
                FieldDefinition(
                    (3,),  # _receiver
                    "Recipient",
                    AddressNameFormatter,
                ),
            ],
        )
    )

    _FUNC_SIG = b"\x73\x32\x14\xa3"
    yield (
        DisplayFormat(
            binding_context=LIFI_CONTEXT,
            func_sig=_FUNC_SIG,
            intent="Swap",
            parameter_definitions=[
                Atomic(parse_bytes),  # _transactionId
                Dynamic(parse_string),  # _integrator
                Dynamic(parse_string),  # _referrer
                Atomic(parse_address),  # _receiver
                Atomic(parse_uint256),  # _minAmountOut
                Tuple(
                    (
                        parse_address,  # callTo
                        parse_address,  # approveTo
                        parse_address,  # sendingAssetId
                        parse_address,  # receivingAssetId
                        parse_uint256,  # fromAmount
                        parse_bytes,  # callData
                        parse_bool,  # requiresDeposit
                    ),
                    is_dynamic=True,
                ),  # _swapData
            ],
            field_definitions=[
                FieldDefinition(
                    (5, 4),  # _swapData.fromAmount
                    "Amount to Send",
                    TokenAmountFormatter(
                        token_path=(5, 2),  # _swapData.sendingAssetId
                    ),
                ),
                FieldDefinition(
                    (4,),  # _minAmountOut
                    "Minimum Amount to receive",
                    AmountFormatter,
                ),
                FieldDefinition(
                    (3,),  # _receiver
                    "Receiver",
                    AddressNameFormatter,
                ),
            ],
        )
    )

    _FUNC_SIG = b"\xaf\x70\x60\xfd"
    yield (
        DisplayFormat(
            binding_context=LIFI_CONTEXT,
            func_sig=_FUNC_SIG,
            intent="Swap",
            parameter_definitions=[
                Atomic(parse_bytes),  # _transactionId
                Dynamic(parse_string),  # _integrator
                Dynamic(parse_string),  # _referrer
                Atomic(parse_address),  # _receiver
                Atomic(parse_uint256),  # _minAmountOut
                Tuple(
                    (
                        parse_address,  # callTo
                        parse_address,  # approveTo
                        parse_address,  # sendingAssetId
                        parse_address,  # receivingAssetId
                        parse_uint256,  # fromAmount
                        parse_bytes,  # callData
                        parse_bool,  # requiresDeposit
                    ),
                    is_dynamic=True,
                ),  # _swapData
            ],
            field_definitions=[
                FieldDefinition(
                    ContainerPath.Value,  # @.value
                    "Amount to send",
                    AmountFormatter,
                ),
                FieldDefinition(
                    (4,),  # _minAmountOut
                    "Minimum to Receive",
                    TokenAmountFormatter(
                        token_path=(5, 3),  # _swapData.receivingAssetId
                    ),
                ),
                FieldDefinition(
                    (3,),  # _receiver
                    "Recipient",
                    AddressNameFormatter,
                ),
            ],
        )
    )

    _FUNC_SIG = b"\x46\x30\xa0\xd8"
    yield (
        DisplayFormat(
            binding_context=LIFI_CONTEXT,
            func_sig=_FUNC_SIG,
            intent="Swap",
            parameter_definitions=[
                Atomic(parse_bytes),  # _transactionId
                Dynamic(parse_string),  # _integrator
                Dynamic(parse_string),  # _referrer
                Atomic(parse_address),  # _receiver
                Atomic(parse_uint256),  # _minAmount
                Array(
                    Tuple(
                        (
                            parse_address,  # callTo
                            parse_address,  # approveTo
                            parse_address,  # sendingAssetId
                            parse_address,  # receivingAssetId
                            parse_uint256,  # fromAmount
                            parse_bytes,  # callData
                            parse_bool,  # requiresDeposit
                        ),
                        is_dynamic=False,
                    )
                ),  # _swapData
            ],
            field_definitions=[
                FieldDefinition(
                    (
                        5,
                        0,
                        4,
                    ),  # _swapData.[0].fromAmount
                    "Amount to Send",
                    TokenAmountFormatter(
                        token_path=(5, 0, 2),  # _swapData.[0].sendingAssetId
                        native_currency_address=LIFI_NATIVE_CURRENCY_ADDRESSES,
                    ),
                ),
                FieldDefinition(
                    (4,),  # _minAmount,
                    "Minimum to Receive",
                    TokenAmountFormatter(
                        token_path=(5, -1, 3),  # # _swapData.[-1].receivingAssetId
                        native_currency_address=LIFI_NATIVE_CURRENCY_ADDRESSES,
                    ),
                ),
                FieldDefinition(
                    (3,),  # receiver
                    "Recipient",
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
                Dynamic(parse_string),  # 8 note
                Dynamic(parse_bytes),  # 9 payload
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
                Dynamic(parse_bytes),  # 1 packedPath (sliced for token addresses)
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
