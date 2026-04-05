from ubinascii import unhexlify

from trezor.crypto import base58

from apps.ethereum.clear_signing import (
    AddressNameFormatter,
    AmountFormatter,
    Array,
    Atomic,
    BindingContext,
    ContainerPath,
    DisplayFormat,
    Dynamic,
    FieldDefinition,
    Struct,
    TokenAmountFormatter,
    UnitFormatter,
    TODOFormatter,
    parse_address,
    parse_bool,
    parse_bytes,
    parse_string,
    parse_uint8,
    parse_uint16,
    parse_uint24,
    parse_uint160,
    parse_uint256)

BINDING_CONTEXT = BindingContext([(1, unhexlify('6a000f20005980200259b80c5102003040001068')), (10, unhexlify('6a000f20005980200259b80c5102003040001068')), (56, unhexlify('6a000f20005980200259b80c5102003040001068')), (137, unhexlify('6a000f20005980200259b80c5102003040001068')), (8453, unhexlify('6a000f20005980200259b80c5102003040001068')), (42161, unhexlify('6a000f20005980200259b80c5102003040001068')), (43114, unhexlify('6a000f20005980200259b80c5102003040001068'))])

DISPLAY_FORMATS = [
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("e3ead59e"),  # swapExactAmountIn(address,(address,address,uint256,uint256,uint256,bytes32,address),uint256,bytes,bytes)
        intent="Swap",
        parameter_definitions=[
            Atomic(parse_address), # executor
            Struct(
            (
                parse_address,  # srcToken,
                parse_address,  # destToken,
                parse_uint256,  # fromAmount,
                parse_uint256,  # toAmount,
                parse_uint256,  # quotedAmount,
                parse_bytes,  # metadata,
                parse_address,  # beneficiary
            ),
            is_dynamic=False,
        ), # swapData
            Atomic(parse_uint256), # partnerAndFee
            Dynamic(parse_bytes), # permit
            Dynamic(parse_bytes), # executorData
        ],
        field_definitions=[
        # WARNING: nested fields not supported
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("7f457675"),  # swapExactAmountOut(address,(address,address,uint256,uint256,uint256,bytes32,address),uint256,bytes,bytes)
        intent="Swap",
        parameter_definitions=[
            Atomic(parse_address), # executor
            Struct(
            (
                parse_address,  # srcToken,
                parse_address,  # destToken,
                parse_uint256,  # fromAmount,
                parse_uint256,  # toAmount,
                parse_uint256,  # quotedAmount,
                parse_bytes,  # metadata,
                parse_address,  # beneficiary
            ),
            is_dynamic=False,
        ), # swapData
            Atomic(parse_uint256), # partnerAndFee
            Dynamic(parse_bytes), # permit
            Dynamic(parse_bytes), # executorData
        ],
        field_definitions=[
        # WARNING: nested fields not supported
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("e8bb3b6c"),  # swapExactAmountInOnUniswapV2((address,address,uint256,uint256,uint256,bytes32,address,bytes),uint256,bytes)
        intent="Swap",
        parameter_definitions=[
            Struct(
            (
                parse_address,  # srcToken,
                parse_address,  # destToken,
                parse_uint256,  # fromAmount,
                parse_uint256,  # toAmount,
                parse_uint256,  # quotedAmount,
                parse_bytes,  # metadata,
                parse_address,  # beneficiary,
                parse_bytes,  # pools
            ),
            is_dynamic=True,
        ), # uniData
            Atomic(parse_uint256), # partnerAndFee
            Dynamic(parse_bytes), # permit
        ],
        field_definitions=[
        # WARNING: nested fields not supported
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("876a02f6"),  # swapExactAmountInOnUniswapV3((address,address,uint256,uint256,uint256,bytes32,address,bytes),uint256,bytes)
        intent="Swap",
        parameter_definitions=[
            Struct(
            (
                parse_address,  # srcToken,
                parse_address,  # destToken,
                parse_uint256,  # fromAmount,
                parse_uint256,  # toAmount,
                parse_uint256,  # quotedAmount,
                parse_bytes,  # metadata,
                parse_address,  # beneficiary,
                parse_bytes,  # pools
            ),
            is_dynamic=True,
        ), # uniData
            Atomic(parse_uint256), # partnerAndFee
            Dynamic(parse_bytes), # permit
        ],
        field_definitions=[
        # WARNING: nested fields not supported
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("a76f4eb6"),  # swapExactAmountOutOnUniswapV2((address,address,uint256,uint256,uint256,bytes32,address,bytes),uint256,bytes)
        intent="Swap",
        parameter_definitions=[
            Struct(
            (
                parse_address,  # srcToken,
                parse_address,  # destToken,
                parse_uint256,  # fromAmount,
                parse_uint256,  # toAmount,
                parse_uint256,  # quotedAmount,
                parse_bytes,  # metadata,
                parse_address,  # beneficiary,
                parse_bytes,  # pools
            ),
            is_dynamic=True,
        ), # uniData
            Atomic(parse_uint256), # partnerAndFee
            Dynamic(parse_bytes), # permit
        ],
        field_definitions=[
        # WARNING: nested fields not supported
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("5e94e28d"),  # swapExactAmountOutOnUniswapV3((address,address,uint256,uint256,uint256,bytes32,address,bytes),uint256,bytes)
        intent="Swap",
        parameter_definitions=[
            Struct(
            (
                parse_address,  # srcToken,
                parse_address,  # destToken,
                parse_uint256,  # fromAmount,
                parse_uint256,  # toAmount,
                parse_uint256,  # quotedAmount,
                parse_bytes,  # metadata,
                parse_address,  # beneficiary,
                parse_bytes,  # pools
            ),
            is_dynamic=True,
        ), # uniData
            Atomic(parse_uint256), # partnerAndFee
            Dynamic(parse_bytes), # permit
        ],
        field_definitions=[
        # WARNING: nested fields not supported
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("1a01c532"),  # swapExactAmountInOnCurveV1((uint256,uint256,address,address,uint256,uint256,uint256,bytes32,address),uint256,bytes)
        intent="Swap",
        parameter_definitions=[
            Struct(
            (
                parse_uint256,  # curveData,
                parse_uint256,  # curveAssets,
                parse_address,  # srcToken,
                parse_address,  # destToken,
                parse_uint256,  # fromAmount,
                parse_uint256,  # toAmount,
                parse_uint256,  # quotedAmount,
                parse_bytes,  # metadata,
                parse_address,  # beneficiary
            ),
            is_dynamic=False,
        ), # curveV1Data
            Atomic(parse_uint256), # partnerAndFee
            Dynamic(parse_bytes), # permit
        ],
        field_definitions=[
        # WARNING: nested fields not supported
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("e37ed256"),  # swapExactAmountInOnCurveV2((uint256,uint256,uint256,address,address,address,uint256,uint256,uint256,bytes32,address),uint256,bytes)
        intent="Swap",
        parameter_definitions=[
            Struct(
            (
                parse_uint256,  # curveData,
                parse_uint256,  # i,
                parse_uint256,  # j,
                parse_address,  # poolAddress,
                parse_address,  # srcToken,
                parse_address,  # destToken,
                parse_uint256,  # fromAmount,
                parse_uint256,  # toAmount,
                parse_uint256,  # quotedAmount,
                parse_bytes,  # metadata,
                parse_address,  # beneficiary
            ),
            is_dynamic=False,
        ), # curveV2Data
            Atomic(parse_uint256), # partnerAndFee
            Dynamic(parse_bytes), # permit
        ],
        field_definitions=[
        # WARNING: nested fields not supported
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("d85ca173"),  # swapExactAmountInOnBalancerV2((uint256,uint256,uint256,bytes32,uint256),uint256,bytes,bytes)
        intent="Swap",
        parameter_definitions=[
            Struct(
            (
                parse_uint256,  # fromAmount,
                parse_uint256,  # toAmount,
                parse_uint256,  # quotedAmount,
                parse_bytes,  # metadata,
                parse_uint256,  # beneficiaryAndApproveFlag
            ),
            is_dynamic=False,
        ), # balancerData
            Atomic(parse_uint256), # partnerAndFee
            Dynamic(parse_bytes), # permit
            Dynamic(parse_bytes), # data
        ],
        field_definitions=[
        # WARNING: $ref $.display.definitions.balancerSelector not expanded
        # WARNING: $ref $.display.definitions.sendAmount not expanded
        # WARNING: $ref $.display.definitions.minReceiveAmount not expanded
        # WARNING: $ref $.display.definitions.beneficiary not expanded
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("d6ed22e6"),  # swapExactAmountOutOnBalancerV2((uint256,uint256,uint256,bytes32,uint256),uint256,bytes,bytes)
        intent="Swap",
        parameter_definitions=[
            Struct(
            (
                parse_uint256,  # fromAmount,
                parse_uint256,  # toAmount,
                parse_uint256,  # quotedAmount,
                parse_bytes,  # metadata,
                parse_uint256,  # beneficiaryAndApproveFlag
            ),
            is_dynamic=False,
        ), # balancerData
            Atomic(parse_uint256), # partnerAndFee
            Dynamic(parse_bytes), # permit
            Dynamic(parse_bytes), # data
        ],
        field_definitions=[
        # WARNING: $ref $.display.definitions.balancerSelector not expanded
        # WARNING: $ref $.display.definitions.maxSendAmount not expanded
        # WARNING: $ref $.display.definitions.receiveAmount not expanded
        # WARNING: $ref $.display.definitions.beneficiary not expanded
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("da35bb0d"),  # swapOnAugustusRFQTryBatchFill((uint256,uint256,uint8,bytes32,address),((uint256,uint128,address,address,address,address,uint256,uint256),bytes,uint256,bytes,bytes)[],bytes)
        intent="Swap",
        parameter_definitions=[
            Struct(
            (
                parse_uint256,  # fromAmount,
                parse_uint256,  # toAmount,
                parse_uint8,  # wrapApproveDirection,
                parse_bytes,  # metadata,
                parse_address,  # beneficiary
            ),
            is_dynamic=False,
        ), # data
            Array(Struct(
            (
                Struct(
            (
                parse_uint256,  # nonceAndMeta,
                parse_uint128,  # expiry,
                parse_address,  # makerAsset,
                parse_address,  # takerAsset,
                parse_address,  # maker,
                parse_address,  # taker,
                parse_uint256,  # makerAmount,
                parse_uint256,  # takerAmount
            ),
            is_dynamic=False,
        ),  # order,
                parse_bytes,  # signature,
                parse_uint256,  # takerTokenFillAmount,
                parse_bytes,  # permitTakerAsset,
                parse_bytes,  # permitMakerAsset
            ),
            is_dynamic=False,
        )), # orders
            Dynamic(parse_bytes), # permit
        ],
        field_definitions=[
        # WARNING: $ref $.display.definitions.sendAmount not expanded
        # WARNING: $ref $.display.definitions.minReceiveAmount not expanded
        # WARNING: $ref $.display.definitions.beneficiary not expanded
        ],
    ),
]
