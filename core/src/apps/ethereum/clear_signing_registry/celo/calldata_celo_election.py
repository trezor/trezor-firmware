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
        (42220, unhexlify("8d6677192144292870907e3fa8a5527fe55a7ff6")),
        (44787, unhexlify("1c3edf937cfc2f6f51784d20deb1af1f9a8655fa")),
    ]
)

DISPLAY_FORMATS = [
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("1c5a9d9c"),
        intent="Activate",
        parameter_definitions=[
            Atomic(parse_address),  # group
        ],
        field_definitions=[
            FieldDefinition((0,), "Validator Group", AddressNameFormatter),
            FieldDefinition(ContainerPath.From, "Vote signer", AddressNameFormatter),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("c14470c4"),
        intent="Activate Votes",
        parameter_definitions=[
            Atomic(parse_address),  # group
            Atomic(parse_address),  # account
        ],
        field_definitions=[
            FieldDefinition((0,), "Validator Group", AddressNameFormatter),
            FieldDefinition((1,), "Account", AddressNameFormatter),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("6e198475"),
        intent="Revoke Votes",
        parameter_definitions=[
            Atomic(parse_address),  # group
            Atomic(parse_uint256),  # value
            Atomic(parse_address),  # lesser
            Atomic(parse_address),  # greater
            Atomic(parse_uint256),  # index
        ],
        field_definitions=[
            FieldDefinition((0,), "Validator Group", AddressNameFormatter),
            FieldDefinition((1,), "Votes to Revoke", TODOFormatter()),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("e0a2ab52"),
        intent="Revoke Votes",
        parameter_definitions=[
            Atomic(parse_address),  # group
            Atomic(parse_address),  # lesser
            Atomic(parse_address),  # greater
            Atomic(parse_uint256),  # index
        ],
        field_definitions=[
            FieldDefinition((0,), "Validator Group", AddressNameFormatter),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("9dfb6081"),
        intent="Revoke Votes",
        parameter_definitions=[
            Atomic(parse_address),  # group
            Atomic(parse_uint256),  # value
            Atomic(parse_address),  # lesser
            Atomic(parse_address),  # greater
            Atomic(parse_uint256),  # index
        ],
        field_definitions=[
            FieldDefinition((1,), "Votes to Revoke", TODOFormatter()),
            FieldDefinition((0,), "Validator Group", AddressNameFormatter),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("580d747a"),
        intent="Vote",
        parameter_definitions=[
            Atomic(parse_address),  # group
            Atomic(parse_uint256),  # value
            Atomic(parse_address),  # lesser
            Atomic(parse_address),  # greater
        ],
        field_definitions=[
            FieldDefinition((0,), "Validator Group", AddressNameFormatter),
            FieldDefinition((1,), "Gold to Vote", TODOFormatter()),
        ],
    ),
]
