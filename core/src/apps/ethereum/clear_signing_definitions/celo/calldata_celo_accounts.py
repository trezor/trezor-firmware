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

BINDING_CONTEXT = BindingContext([(42220, unhexlify('7d21685c17607338b313a7174bab6620bad0aab7')), (44787, unhexlify('ed7f51a34b4e71fbe69b3091fcf879cd14bd73a9'))])

DISPLAY_FORMATS = [
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("b062c843"),
        intent="Add Storage Root",
        parameter_definitions=[
            Dynamic(parse_bytes), # url
        ],
        field_definitions=[
        FieldDefinition((0,), 'Storage Root URL', TODOFormatter()),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("76afa04c"),
        intent="Authorize Signer",
        parameter_definitions=[
            Atomic(parse_address), # signer
            Atomic(parse_uint8), # v
            Atomic(parse_bytes), # r
            Atomic(parse_bytes), # s
        ],
        field_definitions=[
        FieldDefinition((0,), 'Authorized Signer', AddressNameFormatter),
        FieldDefinition(ContainerPath.From, 'Authorizer', AddressNameFormatter),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("58b81ea8"),
        intent="Authorize Signer",
        parameter_definitions=[
            Atomic(parse_address), # signer
            Atomic(parse_bytes), # role
        ],
        field_definitions=[
        FieldDefinition((0,), 'Signer', AddressNameFormatter),
        FieldDefinition((1,), 'Role', TODOFormatter()),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("92f90fbf"),
        intent="Authorize Signer",
        parameter_definitions=[
            Atomic(parse_address), # signer
            Atomic(parse_bytes), # role
            Atomic(parse_uint8), # v
            Atomic(parse_bytes), # r
            Atomic(parse_bytes), # s
        ],
        field_definitions=[
        FieldDefinition((0,), 'Signer', AddressNameFormatter),
        FieldDefinition((1,), 'Role', TODOFormatter()),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("baf7ef0f"),
        intent="Authorize Validator",
        parameter_definitions=[
            Atomic(parse_address), # signer
            Atomic(parse_uint8), # v
            Atomic(parse_bytes), # r
            Atomic(parse_bytes), # s
        ],
        field_definitions=[
        FieldDefinition((0,), 'Validator Signer', AddressNameFormatter),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("0fa750d2"),
        intent="Authorize Validator",
        parameter_definitions=[
            Atomic(parse_address), # signer
            Atomic(parse_uint8), # v
            Atomic(parse_bytes), # r
            Atomic(parse_bytes), # s
            Dynamic(parse_bytes), # ecdsaPublicKey
        ],
        field_definitions=[
        FieldDefinition((0,), 'Authorized Signer', AddressNameFormatter),
        FieldDefinition((4,), 'Public Key', TODOFormatter()),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("4282ee6d"),
        intent="Authorize & Set Vote",
        parameter_definitions=[
            Atomic(parse_address), # signer
            Atomic(parse_uint8), # v
            Atomic(parse_bytes), # r
            Atomic(parse_bytes), # s
        ],
        field_definitions=[
        FieldDefinition((0,), 'Authorized Signer', AddressNameFormatter),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("9f682976"),
        intent="Authorize Signer",
        parameter_definitions=[
            Atomic(parse_address), # account
            Atomic(parse_bytes), # role
        ],
        field_definitions=[
        FieldDefinition((0,), 'Authorizing Account', AddressNameFormatter),
        FieldDefinition((1,), 'Role ID', TODOFormatter()),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("9dca362f"),
        intent="Create Account",
        parameter_definitions=[
        ],
        field_definitions=[
        FieldDefinition(ContainerPath.From, 'Account Owner', AddressNameFormatter),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("bce2b8d6"),
        intent="Delete Delegation",
        parameter_definitions=[
        ],
        field_definitions=[
        FieldDefinition(ContainerPath.From, 'Account', AddressNameFormatter),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("760fbbb2"),
        intent="Remove Signer",
        parameter_definitions=[
        ],
        field_definitions=[
        FieldDefinition(ContainerPath.From, 'Your Account', AddressNameFormatter),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("e7a16e6b"),
        intent="Remove Signer",
        parameter_definitions=[
            Atomic(parse_bytes), # role
        ],
        field_definitions=[
        FieldDefinition(ContainerPath.From, 'Account', AddressNameFormatter),
        FieldDefinition((0,), 'Role', TODOFormatter()),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("0185a232"),
        intent="Remove Signer",
        parameter_definitions=[
            Atomic(parse_bytes), # role
        ],
        field_definitions=[
        FieldDefinition((0,), 'Role', TODOFormatter()),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("fbe3c373"),
        intent="Remove Signer",
        parameter_definitions=[
            Atomic(parse_address), # signer
            Atomic(parse_bytes), # role
        ],
        field_definitions=[
        FieldDefinition((0,), 'Signer', AddressNameFormatter),
        FieldDefinition((1,), 'Role', TODOFormatter()),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("e8d787cb"),
        intent="Remove Root",
        parameter_definitions=[
            Atomic(parse_uint256), # index
        ],
        field_definitions=[
        FieldDefinition((0,), 'Storage Root Index', TODOFormatter()),
        FieldDefinition(ContainerPath.From, 'Account', AddressNameFormatter),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("a5ec94f9"),
        intent="Remove Signer",
        parameter_definitions=[
        ],
        field_definitions=[
        FieldDefinition(ContainerPath.From, 'Your Account', AddressNameFormatter),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("10c504b5"),
        intent="Remove Vote Signer",
        parameter_definitions=[
        ],
        field_definitions=[
        FieldDefinition(ContainerPath.From, 'Account', AddressNameFormatter),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("747daec5"),
        intent="Set Metadata URL",
        parameter_definitions=[
            Dynamic(parse_string), # metadataURL
        ],
        field_definitions=[
        FieldDefinition((0,), 'Metadata URL', TODOFormatter()),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("c47f0027"),
        intent="Set Account Name",
        parameter_definitions=[
            Dynamic(parse_string), # name
        ],
        field_definitions=[
        FieldDefinition((0,), 'Name', TODOFormatter()),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("8f9ae6dc"),
        intent="Delegate Payment",
        parameter_definitions=[
            Atomic(parse_address), # beneficiary
            Atomic(parse_uint256), # fraction
        ],
        field_definitions=[
        FieldDefinition((0,), 'Beneficiary', AddressNameFormatter),
        FieldDefinition((1,), 'Fraction', UnitFormatter(decimals=22, base='%')),
        ],
    ),
]
