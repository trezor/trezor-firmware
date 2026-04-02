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

BINDING_CONTEXT = BindingContext([(42220, unhexlify('aeb865bca93ddc8f47b8e29f40c5399ce34d0c58')), (44787, unhexlify('9acf2a99914e083ad0d610672e93d14b0736bbcc'))])

DISPLAY_FORMATS = [
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("3173b8db"),
        intent="Add Member",
        parameter_definitions=[
            Atomic(parse_address), # validator
            Atomic(parse_address), # lesser
            Atomic(parse_address), # greater
        ],
        field_definitions=[
        FieldDefinition((0,), 'Validator', AddressNameFormatter),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("ca6d56dc"),
        intent="Add Member",
        parameter_definitions=[
            Atomic(parse_address), # validator
        ],
        field_definitions=[
        FieldDefinition((0,), 'Validator', AddressNameFormatter),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("b591d3a5"),
        intent="Affiliate",
        parameter_definitions=[
            Atomic(parse_address), # group
        ],
        field_definitions=[
        FieldDefinition((0,), 'Validator Group', AddressNameFormatter),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("fffdfccb"),
        intent="Deaffiliate",
        parameter_definitions=[
        ],
        field_definitions=[
        FieldDefinition(ContainerPath.From, 'Validator Account', AddressNameFormatter),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("8b16b1c6"),
        intent="Deregister",
        parameter_definitions=[
            Atomic(parse_uint256), # index
        ],
        field_definitions=[
        FieldDefinition(ContainerPath.From, 'Validator Address', AddressNameFormatter),
        FieldDefinition((0,), 'Validator Index', TODOFormatter()),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("60fb822c"),
        intent="Deregister Group",
        parameter_definitions=[
            Atomic(parse_uint256), # index
        ],
        field_definitions=[
        FieldDefinition((0,), 'Group Index', TODOFormatter()),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("602a9eee"),
        intent="Register Validator",
        parameter_definitions=[
            Dynamic(parse_bytes), # ecdsaPublicKey
        ],
        field_definitions=[
        FieldDefinition((0,), 'ECDSA Public Key', TODOFormatter()),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("ee098310"),
        intent="Register Group",
        parameter_definitions=[
            Atomic(parse_uint256), # commission
        ],
        field_definitions=[
        FieldDefinition((0,), 'Commission', UnitFormatter(decimals=22, base='%')),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("caf3c426"),
        intent="Register Validator",
        parameter_definitions=[
            Dynamic(parse_bytes), # ecdsaPublicKey
        ],
        field_definitions=[
        FieldDefinition((0,), 'ECDSA Public Key', TODOFormatter()),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("0b1ca49a"),
        intent="Remove Member",
        parameter_definitions=[
            Atomic(parse_address), # validator
        ],
        field_definitions=[
        FieldDefinition((0,), 'Validator', AddressNameFormatter),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("988dcd1f"),
        intent="Reorder Member",
        parameter_definitions=[
            Atomic(parse_address), # validator
            Atomic(parse_address), # lesserMember
            Atomic(parse_address), # greaterMember
        ],
        field_definitions=[
        FieldDefinition((0,), 'Validator', AddressNameFormatter),
        FieldDefinition((1,), 'Place After', AddressNameFormatter),
        FieldDefinition((2,), 'Place Before', AddressNameFormatter),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("b8f93943"),
        intent="Reset Slashing",
        parameter_definitions=[
        ],
        field_definitions=[
        FieldDefinition(ContainerPath.From, 'Signer', AddressNameFormatter),
        ],
    ),
]
