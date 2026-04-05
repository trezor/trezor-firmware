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

BINDING_CONTEXT = BindingContext([(1116, unhexlify('1011'))])

DISPLAY_FORMATS = [
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("25e2c700"),  # delegateCoin(address)
        intent="Delegate CORE",
        parameter_definitions=[
            Atomic(parse_address), # candidate
        ],
        field_definitions=[
        FieldDefinition((0,), 'Validator Address', AddressNameFormatter),
        FieldDefinition(ContainerPath.Value, 'CORE amount', AmountFormatter),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("65057e77"),  # undelegateCoin(address,uint256)
        intent="Unstake CORE",
        parameter_definitions=[
            Atomic(parse_address), # candidate
            Atomic(parse_uint256), # amount
        ],
        field_definitions=[
        FieldDefinition((0,), 'Validator Address', AddressNameFormatter),
        FieldDefinition((1,), 'CORE amount (0=All)', AmountFormatter),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("4db8a60b"),  # transferCoin(address,address,uint256)
        intent="Move staked CORE",
        parameter_definitions=[
            Atomic(parse_address), # sourceCandidate
            Atomic(parse_address), # targetCandidate
            Atomic(parse_uint256), # amount
        ],
        field_definitions=[
        FieldDefinition((0,), 'From Validator', AddressNameFormatter),
        FieldDefinition((1,), 'To Validator', AddressNameFormatter),
        FieldDefinition((2,), 'Amount (in CORE)', AmountFormatter),
        ],
    ),
]
