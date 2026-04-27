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
        (1, unhexlify("2cc8475177918e8c4d840150b68815a4b6f0f5f3")),
        (10, unhexlify("d0efb07126e865ac95b60381b468081ef648ec5f")),
        (137, unhexlify("2cc8475177918e8c4d840150b68815a4b6f0f5f3")),
        (8453, unhexlify("d0efb07126e865ac95b60381b468081ef648ec5f")),
        (42161, unhexlify("d0efb07126e865ac95b60381b468081ef648ec5f")),
        (11155111, unhexlify("2cc8475177918e8c4d840150b68815a4b6f0f5f3")),
    ]
)

DISPLAY_FORMATS = [
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("1a833ee3"),
        intent="Batch transactions",
        parameter_definitions=[
            Array(
                Struct(
                    (
                        parse_address,  # to,
                        parse_uint256,  # value,
                        parse_bytes,  # data
                    ),
                    is_dynamic=False,
                )
            ),  # calls
        ],
        field_definitions=[
            FieldDefinition((0, 2), "Transaction", TODOFormatter()),
        ],
    ),
]
