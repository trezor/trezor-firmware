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
    TODOFormatter,
    TokenAmountFormatter,
    UnitFormatter,
    parse_address,
    parse_bool,
    parse_bytes,
    parse_string,
    parse_uint8,
    parse_uint16,
    parse_uint24,
    parse_uint128,
    parse_uint160,
    parse_uint256,
)

BINDING_CONTEXT = BindingContext(
    [
        (1, unhexlify("1231deb6f5749ef6ce6943a275a1d3e7486f4eae")),
        (137, unhexlify("1231deb6f5749ef6ce6943a275a1d3e7486f4eae")),
        (42161, unhexlify("1231deb6f5749ef6ce6943a275a1d3e7486f4eae")),
        (10, unhexlify("1231deb6f5749ef6ce6943a275a1d3e7486f4eae")),
        (56, unhexlify("1231deb6f5749ef6ce6943a275a1d3e7486f4eae")),
        (43114, unhexlify("1231deb6f5749ef6ce6943a275a1d3e7486f4eae")),
        (100, unhexlify("1231deb6f5749ef6ce6943a275a1d3e7486f4eae")),
        (250, unhexlify("1231deb6f5749ef6ce6943a275a1d3e7486f4eae")),
        (324, unhexlify("341e94069f53234fe6dabef707ad424830525715")),
        (8453, unhexlify("1231deb6f5749ef6ce6943a275a1d3e7486f4eae")),
        (59144, unhexlify("de1e598b81620773454588b85d6b5d4eec32573e")),
        (5000, unhexlify("1231deb6f5749ef6ce6943a275a1d3e7486f4eae")),
        (534352, unhexlify("1231deb6f5749ef6ce6943a275a1d3e7486f4eae")),
        (42220, unhexlify("1231deb6f5749ef6ce6943a275a1d3e7486f4eae")),
        (1284, unhexlify("1231deb6f5749ef6ce6943a275a1d3e7486f4eae")),
        (1285, unhexlify("1231deb6f5749ef6ce6943a275a1d3e7486f4eae")),
        (1313161554, unhexlify("1231deb6f5749ef6ce6943a275a1d3e7486f4eae")),
        (1088, unhexlify("24ca98fb6972f5ee05f0db00595c7f68d9fafd68")),
        (25, unhexlify("1231deb6f5749ef6ce6943a275a1d3e7486f4eae")),
        (1666600000, unhexlify("1231deb6f5749ef6ce6943a275a1d3e7486f4eae")),
        (122, unhexlify("1231deb6f5749ef6ce6943a275a1d3e7486f4eae")),
        (288, unhexlify("1231deb6f5749ef6ce6943a275a1d3e7486f4eae")),
        (106, unhexlify("1231deb6f5749ef6ce6943a275a1d3e7486f4eae")),
        (9001, unhexlify("1231deb6f5749ef6ce6943a275a1d3e7486f4eae")),
        (42170, unhexlify("1231deb6f5749ef6ce6943a275a1d3e7486f4eae")),
        (167004, unhexlify("3a9a5dba8fe1c4da98187ce4755701bca182f63b")),
        (204, unhexlify("1231deb6f5749ef6ce6943a275a1d3e7486f4eae")),
        (81457, unhexlify("1231deb6f5749ef6ce6943a275a1d3e7486f4eae")),
        (252, unhexlify("1231deb6f5749ef6ce6943a275a1d3e7486f4eae")),
        (34443, unhexlify("1231deb6f5749ef6ce6943a275a1d3e7486f4eae")),
    ]
)

DISPLAY_FORMATS = [
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("5fd9ae2e"),
        intent="Swap",
        parameter_definitions=[
            Atomic(parse_bytes),  # _transactionId
            Dynamic(parse_string),  # _integrator
            Dynamic(parse_string),  # _referrer
            Atomic(parse_address),  # _receiver
            Atomic(parse_uint256),  # _minAmountOut
            Array(
                Struct(
                    (
                        parse_address,  # callTo,
                        parse_address,  # approveTo,
                        parse_address,  # sendingAssetId,
                        parse_address,  # receivingAssetId,
                        parse_uint256,  # fromAmount,
                        parse_bytes,  # callData,
                        parse_bool,  # requiresDeposit
                    ),
                    is_dynamic=False,
                )
            ),  # _swapData
        ],
        field_definitions=[
            FieldDefinition(
                (5, 0, 4), "Amount to Send", TokenAmountFormatter(token_path=(5, 0, 2))
            ),
            FieldDefinition(
                (4,), "Minimum to Receive", TokenAmountFormatter(token_path=(5, -1, 3))
            ),
            FieldDefinition((3,), "Recipient", AddressNameFormatter),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("2c57e884"),
        intent="Swap",
        parameter_definitions=[
            Atomic(parse_bytes),  # _transactionId
            Dynamic(parse_string),  # _integrator
            Dynamic(parse_string),  # _referrer
            Atomic(parse_address),  # _receiver
            Atomic(parse_uint256),  # _minAmountOut
            Array(
                Struct(
                    (
                        parse_address,  # callTo,
                        parse_address,  # approveTo,
                        parse_address,  # sendingAssetId,
                        parse_address,  # receivingAssetId,
                        parse_uint256,  # fromAmount,
                        parse_bytes,  # callData,
                        parse_bool,  # requiresDeposit
                    ),
                    is_dynamic=False,
                )
            ),  # _swapData
        ],
        field_definitions=[
            # WARNING: $ref $.display.definitions._minAmountOut not expanded
            FieldDefinition(
                (5, 0, 4), "Amount to Send", TokenAmountFormatter(token_path=(5, 0, 2))
            ),
            FieldDefinition((3,), "Receiver", AddressNameFormatter),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("736eac0b"),
        intent="Swap",
        parameter_definitions=[
            Atomic(parse_bytes),  # _transactionId
            Dynamic(parse_string),  # _integrator
            Dynamic(parse_string),  # _referrer
            Atomic(parse_address),  # _receiver
            Atomic(parse_uint256),  # _minAmountOut
            Array(
                Struct(
                    (
                        parse_address,  # callTo,
                        parse_address,  # approveTo,
                        parse_address,  # sendingAssetId,
                        parse_address,  # receivingAssetId,
                        parse_uint256,  # fromAmount,
                        parse_bytes,  # callData,
                        parse_bool,  # requiresDeposit
                    ),
                    is_dynamic=False,
                )
            ),  # _swapData
        ],
        field_definitions=[
            FieldDefinition(ContainerPath.Value, "Amount to send", AmountFormatter),
            FieldDefinition(
                (4,), "Minimum to Receive", TokenAmountFormatter(token_path=(5, -1, 3))
            ),
            FieldDefinition((3,), "Recipient", AddressNameFormatter),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("4666fc80"),
        intent="Swap",
        parameter_definitions=[
            Atomic(parse_bytes),  # _transactionId
            Dynamic(parse_string),  # _integrator
            Dynamic(parse_string),  # _referrer
            Atomic(parse_address),  # _receiver
            Atomic(parse_uint256),  # _minAmountOut
            Struct(
                (
                    parse_address,  # callTo,
                    parse_address,  # approveTo,
                    parse_address,  # sendingAssetId,
                    parse_address,  # receivingAssetId,
                    parse_uint256,  # fromAmount,
                    parse_bytes,  # callData,
                    parse_bool,  # requiresDeposit
                ),
                is_dynamic=True,
            ),  # _swapData
        ],
        field_definitions=[
            FieldDefinition(
                (5, 4), "Amount to Send", TokenAmountFormatter(token_path=(5, 2))
            ),
            FieldDefinition(
                (4,), "Minimum to Receive", TokenAmountFormatter(token_path=(5, 3))
            ),
            FieldDefinition((3,), "Recipient", AddressNameFormatter),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("733214a3"),
        intent="Swap",
        parameter_definitions=[
            Atomic(parse_bytes),  # _transactionId
            Dynamic(parse_string),  # _integrator
            Dynamic(parse_string),  # _referrer
            Atomic(parse_address),  # _receiver
            Atomic(parse_uint256),  # _minAmountOut
            Struct(
                (
                    parse_address,  # callTo,
                    parse_address,  # approveTo,
                    parse_address,  # sendingAssetId,
                    parse_address,  # receivingAssetId,
                    parse_uint256,  # fromAmount,
                    parse_bytes,  # callData,
                    parse_bool,  # requiresDeposit
                ),
                is_dynamic=True,
            ),  # _swapData
        ],
        field_definitions=[
            # WARNING: $ref $.display.definitions._minAmountOut not expanded
            FieldDefinition(
                (5, 4), "Amount to Send", TokenAmountFormatter(token_path=(5, 2))
            ),
            FieldDefinition((3,), "Receiver", AddressNameFormatter),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("af7060fd"),
        intent="Swap",
        parameter_definitions=[
            Atomic(parse_bytes),  # _transactionId
            Dynamic(parse_string),  # _integrator
            Dynamic(parse_string),  # _referrer
            Atomic(parse_address),  # _receiver
            Atomic(parse_uint256),  # _minAmountOut
            Struct(
                (
                    parse_address,  # callTo,
                    parse_address,  # approveTo,
                    parse_address,  # sendingAssetId,
                    parse_address,  # receivingAssetId,
                    parse_uint256,  # fromAmount,
                    parse_bytes,  # callData,
                    parse_bool,  # requiresDeposit
                ),
                is_dynamic=True,
            ),  # _swapData
        ],
        field_definitions=[
            FieldDefinition(ContainerPath.Value, "Amount to send", AmountFormatter),
            FieldDefinition(
                (4,), "Minimum to Receive", TokenAmountFormatter(token_path=(5, 3))
            ),
            FieldDefinition((3,), "Recipient", AddressNameFormatter),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("4630a0d8"),
        intent="Swap",
        parameter_definitions=[
            Atomic(parse_bytes),  # _transactionId
            Dynamic(parse_string),  # _integrator
            Dynamic(parse_string),  # _referrer
            Atomic(parse_address),  # _receiver
            Atomic(parse_uint256),  # _minAmount
            Array(
                Struct(
                    (
                        parse_address,  # callTo,
                        parse_address,  # approveTo,
                        parse_address,  # sendingAssetId,
                        parse_address,  # receivingAssetId,
                        parse_uint256,  # fromAmount,
                        parse_bytes,  # callData,
                        parse_bool,  # requiresDeposit
                    ),
                    is_dynamic=False,
                )
            ),  # _swapData
        ],
        field_definitions=[
            # WARNING: $ref $.display.definitions.fromAmount not expanded
            # WARNING: $ref $.display.definitions._minAmountOut not expanded
            FieldDefinition((3,), "Recipient", AddressNameFormatter),
        ],
    ),
]
