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
        (1, unhexlify("91e677b07f7af907ec9a428aafa9fc14a0d3a338")),
        (560048, unhexlify("cd1442415fc5c29aa848a49d2e232720be07976c")),
    ]
)

DISPLAY_FORMATS = [
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("84d81062"),  # createPod()
        intent="Create EigenLayerPod",
        parameter_definitions=[],
        field_definitions=[],
    ),
]
