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

BINDING_CONTEXT = BindingContext([(1116, unhexlify('f5fa1728babc3f8d2a617397fac2696c958c3409'))])

DISPLAY_FORMATS = [
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("6a627842"),  # mint(address)
        intent="Stake CORE",
        parameter_definitions=[
            Atomic(parse_address), # _validator
        ],
        field_definitions=[
        FieldDefinition(ContainerPath.Value, 'Amount to stake', AmountFormatter),
        FieldDefinition((0,), 'Validator Address', AddressNameFormatter),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("db006a75"),  # redeem(uint256)
        intent="Request Redeem",
        parameter_definitions=[
            Atomic(parse_uint256), # stCore
        ],
        field_definitions=[
        FieldDefinition((0,), 'Amount to Redeem', TokenAmountFormatter()),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("3ccfd60b"),  # withdraw()
        intent="Withdraw CORE",
        parameter_definitions=[
        ],
        field_definitions=[
        ],
    ),
]
