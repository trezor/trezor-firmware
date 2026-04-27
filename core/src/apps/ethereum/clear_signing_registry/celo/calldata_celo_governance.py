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
        (42220, unhexlify("d533ca259b330c7a88f74e000a3faea2d63b7972")),
        (44787, unhexlify("aa963fc97281d9632d96700ab62a4d1340f9a28a")),
    ]
)

DISPLAY_FORMATS = [
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("5d35a3d9"),
        intent="Approve",
        parameter_definitions=[
            Atomic(parse_uint256),  # proposalId
            Atomic(parse_uint256),  # index
        ],
        field_definitions=[
            FieldDefinition((0,), "Proposal ID", TODOFormatter()),
            FieldDefinition((1,), "Item Index", TODOFormatter()),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("3bb0ed2b"),
        intent="Dequeue Proposals",
        parameter_definitions=[],
        field_definitions=[],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("5601eaea"),
        intent="Execute Proposal",
        parameter_definitions=[
            Atomic(parse_uint256),  # proposalId
            Atomic(parse_uint256),  # index
        ],
        field_definitions=[
            FieldDefinition((0,), "Proposal ID", TODOFormatter()),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("cf48eb94"),
        intent="Execute Hotfix",
        parameter_definitions=[
            Array(Atomic(parse_uint256)),  # values
            Array(Atomic(parse_address)),  # destinations
            Dynamic(parse_bytes),  # data
            Array(Atomic(parse_uint256)),  # dataLengths
            Atomic(parse_bytes),  # salt
        ],
        field_definitions=[
            FieldDefinition((0,), "CELO to Send", AmountFormatter),
            FieldDefinition((1,), "Recipient", AddressNameFormatter),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("9cb02dfc"),
        intent="Prepare Hotfix",
        parameter_definitions=[
            Atomic(parse_bytes),  # hash
        ],
        field_definitions=[
            FieldDefinition((0,), "Hotfix Hash", TODOFormatter()),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("65bbdaa0"),
        intent="Propose",
        parameter_definitions=[
            Array(Atomic(parse_uint256)),  # values
            Array(Atomic(parse_address)),  # destinations
            Dynamic(parse_bytes),  # data
            Array(Atomic(parse_uint256)),  # dataLengths
            Dynamic(parse_string),  # descriptionUrl
        ],
        field_definitions=[
            FieldDefinition((0,), "Amount to Send", AmountFormatter),
            FieldDefinition((1,), "Recipient", AddressNameFormatter),
            FieldDefinition(ContainerPath.Value, "Deposit", AmountFormatter),
            FieldDefinition((4,), "Description URL", TODOFormatter()),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("af108a0e"),
        intent="Revoke Upvote",
        parameter_definitions=[
            Atomic(parse_uint256),  # lesser
            Atomic(parse_uint256),  # greater
        ],
        field_definitions=[],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("9381ab25"),
        intent="Revoke Votes",
        parameter_definitions=[],
        field_definitions=[
            FieldDefinition(
                ContainerPath.From, "Signing Address", AddressNameFormatter
            ),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("57333978"),
        intent="Upvote",
        parameter_definitions=[
            Atomic(parse_uint256),  # proposalId
            Atomic(parse_uint256),  # lesser
            Atomic(parse_uint256),  # greater
        ],
        field_definitions=[
            FieldDefinition((0,), "Proposal ID", TODOFormatter()),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("bbb2eab9"),
        intent="Vote",
        parameter_definitions=[
            Atomic(parse_uint256),  # proposalId
            Atomic(parse_uint256),  # index
            Atomic(parse_uint8),  # value
        ],
        field_definitions=[
            FieldDefinition((0,), "Proposal ID", TODOFormatter()),
            FieldDefinition((2,), "Vote", TODOFormatter()),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("2edfd12e"),
        intent="Partial Vote",
        parameter_definitions=[
            Atomic(parse_uint256),  # proposalId
            Atomic(parse_uint256),  # index
            Atomic(parse_uint256),  # yesVotes
            Atomic(parse_uint256),  # noVotes
            Atomic(parse_uint256),  # abstainVotes
        ],
        field_definitions=[
            FieldDefinition((0,), "Proposal ID", TODOFormatter()),
            FieldDefinition((2,), "Yes Votes", TODOFormatter()),
            FieldDefinition((3,), "No Votes", TODOFormatter()),
            FieldDefinition((4,), "Abstain Votes", TODOFormatter()),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("3ccfd60b"),
        intent="Withdraw",
        parameter_definitions=[],
        field_definitions=[
            FieldDefinition(ContainerPath.From, "Beneficiary", AddressNameFormatter),
        ],
    ),
]
