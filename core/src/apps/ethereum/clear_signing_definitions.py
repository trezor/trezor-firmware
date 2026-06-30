from micropython import const
from ubinascii import unhexlify

from .clear_signing import (
    AddressNameFormatter,
    AmountFormatter,
    Array,
    Atomic,
    BindingContext,
    ContainerPath,
    DateFormatter,
    DisplayFormat,
    Dynamic,
    FieldDefinition,
    RawFormatter,
    TokenAmountFormatter,
    Tuple,
    UnitFormatter,
    parse_address,
    parse_bool,
    parse_bytes,
    parse_bytes32,
    parse_string,
    parse_uint24,
    parse_uint160,
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
SC_FUNC_APPROVE_REVOKE_AMOUNT = const(0)

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

if __debug__:
    from trezor.crypto import base58

    assert APPROVE_DISPLAY_FORMAT.func_sig == base58.keccak_32(
        b"approve(address,uint256)"
    )
    assert TRANSFER_DISPLAY_FORMAT.func_sig == base58.keccak_32(
        b"transfer(address,uint256)"
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

# $.metadata.constants.addressAsEth and addressAsNull from common-AggregationRouterV6.json
ONEINCH_NATIVE_CURRENCY_ADDRESSES = [
    unhexlify("EeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"),
    unhexlify("0000000000000000000000000000000000000000"),
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

_FUNC_SIG = unhexlify("07ed2379")
if __debug__:
    assert _FUNC_SIG == base58.keccak_32(
        b"swap(address,(address,address,address,address,uint256,uint256,uint256),bytes)"
    )
ALL_DISPLAY_FORMATS.append(
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

_FUNC_SIG = unhexlify("83800a8e")
if __debug__:
    assert _FUNC_SIG == base58.keccak_32(b"unoswap(uint256,uint256,uint256,uint256)")
ALL_DISPLAY_FORMATS.append(
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

_FUNC_SIG = unhexlify("e2c95c82")
if __debug__:
    assert _FUNC_SIG == base58.keccak_32(
        b"unoswapTo(uint256,uint256,uint256,uint256,uint256)"
    )
ALL_DISPLAY_FORMATS.append(
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

_FUNC_SIG = unhexlify("8770ba91")
if __debug__:
    assert _FUNC_SIG == base58.keccak_32(
        b"unoswap2(uint256,uint256,uint256,uint256,uint256)"
    )
ALL_DISPLAY_FORMATS.append(
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

_FUNC_SIG = unhexlify("19367472")
if __debug__:
    assert _FUNC_SIG == base58.keccak_32(
        b"unoswap3(uint256,uint256,uint256,uint256,uint256,uint256)"
    )
ALL_DISPLAY_FORMATS.append(
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

_FUNC_SIG = unhexlify("ea76dddf")
if __debug__:
    assert _FUNC_SIG == base58.keccak_32(
        b"unoswapTo2(uint256,uint256,uint256,uint256,uint256,uint256)"
    )
ALL_DISPLAY_FORMATS.append(
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

_FUNC_SIG = unhexlify("f7a70056")
if __debug__:
    assert _FUNC_SIG == base58.keccak_32(
        b"unoswapTo3(uint256,uint256,uint256,uint256,uint256,uint256,uint256)"
    )
ALL_DISPLAY_FORMATS.append(
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

_FUNC_SIG = unhexlify("a76dfc3b")
if __debug__:
    assert _FUNC_SIG == base58.keccak_32(b"ethUnoswap(uint256,uint256)")
ALL_DISPLAY_FORMATS.append(
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

_FUNC_SIG = unhexlify("89af926a")
if __debug__:
    assert _FUNC_SIG == base58.keccak_32(b"ethUnoswap2(uint256,uint256,uint256)")
ALL_DISPLAY_FORMATS.append(
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

_FUNC_SIG = unhexlify("188ac35d")
if __debug__:
    assert _FUNC_SIG == base58.keccak_32(
        b"ethUnoswap3(uint256,uint256,uint256,uint256)"
    )
ALL_DISPLAY_FORMATS.append(
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

_FUNC_SIG = unhexlify("175accdc")
if __debug__:
    assert _FUNC_SIG == base58.keccak_32(b"ethUnoswapTo(uint256,uint256,uint256)")
ALL_DISPLAY_FORMATS.append(
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

_FUNC_SIG = unhexlify("0f449d71")
if __debug__:
    assert _FUNC_SIG == base58.keccak_32(
        b"ethUnoswapTo2(uint256,uint256,uint256,uint256)"
    )
ALL_DISPLAY_FORMATS.append(
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

_FUNC_SIG = unhexlify("493189f0")
if __debug__:
    assert _FUNC_SIG == base58.keccak_32(
        b"ethUnoswapTo3(uint256,uint256,uint256,uint256,uint256)"
    )
ALL_DISPLAY_FORMATS.append(
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
LIFI_ADDRESS = unhexlify("1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE")
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
    (324, unhexlify("341e94069f53234fe6dabef707ad424830525715")),  # zkSync Era
    (1088, unhexlify("24ca98fb6972f5ee05f0db00595c7f68d9fafd68")),  # Metis
    (59144, unhexlify("de1e598b81620773454588b85d6b5d4eec32573e")),  # Linea
    (167004, unhexlify("3a9a5dba8fe1c4da98187ce4755701bca182f63b")),
]

LIFI_CONTEXT = BindingContext(
    [(chain, LIFI_ADDRESS) for chain in LIFI_CHAINS] + LIFI_ALT_DEPLOYMENTS,
)

LIFI_NATIVE_CURRENCY_ADDRESSES = [
    unhexlify("EeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"),
    unhexlify("0000000000000000000000000000000000000000"),
]

_FUNC_SIG = unhexlify("5fd9ae2e")
if __debug__:
    assert _FUNC_SIG == base58.keccak_32(
        b"swapTokensMultipleV3ERC20ToERC20(bytes32,string,string,address,uint256,(address,address,address,address,uint256,bytes,bool)[])"
    )
ALL_DISPLAY_FORMATS.append(
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

_FUNC_SIG = unhexlify("2c57e884")
if __debug__:
    assert _FUNC_SIG == base58.keccak_32(
        b"swapTokensMultipleV3ERC20ToNative(bytes32,string,string,address,uint256,(address,address,address,address,uint256,bytes,bool)[])"
    )
ALL_DISPLAY_FORMATS.append(
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

_FUNC_SIG = unhexlify("736eac0b")
if __debug__:
    assert _FUNC_SIG == base58.keccak_32(
        b"swapTokensMultipleV3NativeToERC20(bytes32,string,string,address,uint256,(address,address,address,address,uint256,bytes,bool)[])"
    )
ALL_DISPLAY_FORMATS.append(
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

_FUNC_SIG = unhexlify("4666fc80")
if __debug__:
    assert _FUNC_SIG == base58.keccak_32(
        b"swapTokensSingleV3ERC20ToERC20(bytes32,string,string,address,uint256,(address,address,address,address,uint256,bytes,bool))"
    )
ALL_DISPLAY_FORMATS.append(
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
                TokenAmountFormatter(token_path=(5, 3)),  # _swapData.receivingAssetId
            ),
            FieldDefinition(
                (3,),  # _receiver
                "Recipient",
                AddressNameFormatter,
            ),
        ],
    )
)

_FUNC_SIG = unhexlify("733214a3")
if __debug__:
    assert _FUNC_SIG == base58.keccak_32(
        b"swapTokensSingleV3ERC20ToNative(bytes32,string,string,address,uint256,(address,address,address,address,uint256,bytes,bool))"
    )
ALL_DISPLAY_FORMATS.append(
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

_FUNC_SIG = unhexlify("af7060fd")
if __debug__:
    assert _FUNC_SIG == base58.keccak_32(
        b"swapTokensSingleV3NativeToERC20(bytes32,string,string,address,uint256,(address,address,address,address,uint256,bytes,bool))"
    )
ALL_DISPLAY_FORMATS.append(
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

_FUNC_SIG = unhexlify("4630a0d8")
if __debug__:
    assert _FUNC_SIG == base58.keccak_32(
        b"swapTokensGeneric(bytes32,string,string,address,uint256,(address,address,address,address,uint256,bytes,bool)[])"
    )
ALL_DISPLAY_FORMATS.append(
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
    ),
)

# https://github.com/LedgerHQ/clear-signing-erc7730-registry/blob/master/registry/uniswap/calldata-UniswapV3Router02.json#L6
UNISWAP_V3_ROUTER_ADDRESS = unhexlify("68b3465833fb72A70ecDF485E0e4C7bD8665Fc45")
UNISWAP_V3_ROUTER_CHAINS = [1]

# https://github.com/LedgerHQ/clear-signing-erc7730-registry/blob/master/registry/uniswap/calldata-UniswapV3Router02.json

UNISWAP_CONTEXT = BindingContext(
    [(chain, UNISWAP_V3_ROUTER_ADDRESS) for chain in UNISWAP_V3_ROUTER_CHAINS],
)

_FUNC_SIG = unhexlify("b858183f")
if __debug__:
    assert _FUNC_SIG == base58.keccak_32(b"exactInput((bytes,address,uint256,uint256))")
ALL_DISPLAY_FORMATS.append(
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

_FUNC_SIG = unhexlify("04e45aaf")
if __debug__:
    assert _FUNC_SIG == base58.keccak_32(
        b"exactInputSingle((address,address,uint24,address,uint256,uint256,uint160))"
    )
ALL_DISPLAY_FORMATS.append(
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

_FUNC_SIG = unhexlify("09b81346")
if __debug__:
    assert _FUNC_SIG == base58.keccak_32(
        b"exactOutput((bytes,address,uint256,uint256))"
    )
ALL_DISPLAY_FORMATS.append(
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

_FUNC_SIG = unhexlify("5023b4df")
if __debug__:
    assert _FUNC_SIG == base58.keccak_32(
        b"exactOutputSingle((address,address,uint24,address,uint256,uint256,uint160))"
    )
ALL_DISPLAY_FORMATS.append(
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
    ),
)


if __debug__:
    # One contract to test it all would have been easier. But Caesar has a paragraph limit.
    #   * TREZOR_TEST_SCALARS_DESCRIPTOR  - scalar/atomic formatters
    #   * TREZOR_TEST_TOKEN_DESCRIPTOR    - token-amount resolution (path + const)
    #   * TREZOR_TEST_ARRAYS_DESCRIPTOR   - multi-value arrays
    #   * TREZOR_TEST_PATHS_DESCRIPTOR    - composite path styles (slices + nested)
    TREZOR_TEST_CHAIN_ID = 1
    TREZOR_TEST_ADDRESS = unhexlify("dddddddddddddddddddddddddddddddddddddddd")
    TREZOR_TEST_CONST_TOKEN = unhexlify("eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee")
    TREZOR_TEST_NATIVE = unhexlify("0000000000000000000000000000000000000000")

    TREZOR_TEST_CONTEXT = BindingContext([(TREZOR_TEST_CHAIN_ID, TREZOR_TEST_ADDRESS)])

    # --- 1) scalar / atomic formatters ---
    TREZOR_TEST_SCALARS_DESCRIPTOR = DisplayFormat(
        binding_context=TREZOR_TEST_CONTEXT,
        func_sig=unhexlify("7e577e01"),  # synthetic selector (dummy contract)
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
    TREZOR_TEST_TOKEN_DESCRIPTOR = DisplayFormat(
        binding_context=TREZOR_TEST_CONTEXT,
        func_sig=unhexlify("7e577e02"),  # synthetic selector (dummy contract)
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
    TREZOR_TEST_ARRAYS_DESCRIPTOR = DisplayFormat(
        binding_context=TREZOR_TEST_CONTEXT,
        func_sig=unhexlify("7e577e03"),  # synthetic selector (dummy contract)
        intent="Trezor Test Arrays. DO NOT USE",
        parameter_definitions=[
            Array(Atomic(parse_uint256)),  # 0 amounts (multi-value array)
            Array(Atomic(parse_uint256)),  # 1 tokenAmounts (multi-value tokenAmount)
            Array(Atomic(parse_uint256)),  # 2 dates (multi-value date)
        ],
        field_definitions=[
            FieldDefinition((0,), "Amounts (array)", RawFormatter),  # multi-value raw
            # multi-value tokenAmount sharing one constant token
            FieldDefinition(
                (1,),
                "Token Amounts (array)",
                TokenAmountFormatter(const_token_address=TREZOR_TEST_CONST_TOKEN),
            ),
            FieldDefinition((2,), "Dates (array)", DateFormatter),  # multi-value date
        ],
    )

    # --- 4) composite path styles: bytes slicing + nested array-of-structs ---
    TREZOR_TEST_PATHS_DESCRIPTOR = DisplayFormat(
        binding_context=TREZOR_TEST_CONTEXT,
        func_sig=unhexlify("7e577e04"),  # synthetic selector (dummy contract)
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

    ALL_DISPLAY_FORMATS.extend(
        [
            TREZOR_TEST_SCALARS_DESCRIPTOR,
            TREZOR_TEST_TOKEN_DESCRIPTOR,
            TREZOR_TEST_ARRAYS_DESCRIPTOR,
            TREZOR_TEST_PATHS_DESCRIPTOR,
        ]
    )
