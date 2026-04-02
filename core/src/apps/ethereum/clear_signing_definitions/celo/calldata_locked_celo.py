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

BINDING_CONTEXT = BindingContext([(42220, unhexlify('55e1a0c8f376964bd339167476063bfed7f213d5')), (44787, unhexlify('6a4cc5693dc5bfa3799c699f3b941ba2cb00c341'))])

DISPLAY_FORMATS = [
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("58f84a78"),
        intent="Delegate",
        parameter_definitions=[
            Atomic(parse_address), # delegatee
            Atomic(parse_uint256), # delegateFraction
        ],
        field_definitions=[
        FieldDefinition((1,), 'Fraction to Delegate', UnitFormatter(decimals=22, base='%')),
        FieldDefinition((0,), 'Delegatee', AddressNameFormatter),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("f83d08ba"),
        intent="Lock CELO",
        parameter_definitions=[
        ],
        field_definitions=[
        FieldDefinition(ContainerPath.Value, 'Amount to Lock', AmountFormatter),
        FieldDefinition(ContainerPath.From, 'Beneficiary', AddressNameFormatter),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("b2fb30cb"),
        intent="Relock",
        parameter_definitions=[
            Atomic(parse_uint256), # index
            Atomic(parse_uint256), # value
        ],
        field_definitions=[
        FieldDefinition((1,), 'Amount to Relock', AmountFormatter),
        FieldDefinition(ContainerPath.From, 'Beneficiary', AddressNameFormatter),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("18629a92"),
        intent="Revoke Delegation",
        parameter_definitions=[
            Atomic(parse_address), # delegatee
            Atomic(parse_uint256), # revokeFraction
        ],
        field_definitions=[
        FieldDefinition((0,), 'Delegatee', AddressNameFormatter),
        FieldDefinition((1,), 'Fraction to Revoke', UnitFormatter(decimals=22, base='%')),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("6198e339"),
        intent="Unlock",
        parameter_definitions=[
            Atomic(parse_uint256), # value
        ],
        field_definitions=[
        FieldDefinition((0,), 'Amount to Unlock', AmountFormatter),
        FieldDefinition(ContainerPath.From, 'Beneficiary', AddressNameFormatter),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("2e1a7d4d"),
        intent="Withdraw CELO",
        parameter_definitions=[
            Atomic(parse_uint256), # index
        ],
        field_definitions=[
        FieldDefinition(ContainerPath.From, 'Beneficiary', AddressNameFormatter),
        FieldDefinition((0,), 'Withdrawal Index', TODOFormatter()),
        ],
    ),
]
