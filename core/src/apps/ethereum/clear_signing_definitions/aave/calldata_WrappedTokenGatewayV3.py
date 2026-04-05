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

BINDING_CONTEXT = BindingContext([(1, unhexlify('d01607c3c5aecaba394d8be3a77a08590149325722'))])

DISPLAY_FORMATS = [
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("474cf53d"),  # depositETH(address pool, address onBehalfOf, uint16 referralCode)
        intent="Supply",
        parameter_definitions=[
            Atomic(parse_address), # pool
            Atomic(parse_address), # onBehalfOf
            Atomic(parse_uint16), # referralCode
        ],
        field_definitions=[
        FieldDefinition(ContainerPath.Value, 'Amount to supply', AmountFormatter),
        FieldDefinition((1,), 'Collateral recipient', AddressNameFormatter),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("bcc3c255"),  # repayETH(address pool, uint256 amount, address onBehalfOf)
        intent="Repay loan",
        parameter_definitions=[
            Atomic(parse_address), # pool
            Atomic(parse_uint256), # amount
            Atomic(parse_address), # onBehalfOf
        ],
        field_definitions=[
        FieldDefinition((1,), 'Amount to repay', AmountFormatter),
        FieldDefinition((2,), 'For debt holder', AddressNameFormatter),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("80500d20"),  # withdrawETH(address pool, uint256 amount, address to)
        intent="Withdraw",
        parameter_definitions=[
            Atomic(parse_address), # pool
            Atomic(parse_uint256), # amount
            Atomic(parse_address), # to
        ],
        field_definitions=[
        FieldDefinition((1,), 'Amount to withdraw', TokenAmountFormatter()),
        FieldDefinition((2,), 'To recipient', AddressNameFormatter),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("d4c40b6c"),  # withdrawETHWithPermit(address, uint256 amount, address to, uint256 deadline, uint8 permitV, bytes32 permitR, bytes32 permitS)
        intent="Withdraw",
        parameter_definitions=[
            Atomic(parse_address), # pool
            Atomic(parse_uint256), # amount
            Atomic(parse_address), # to
            Atomic(parse_uint256), # deadline
            Atomic(parse_uint8), # permitV
            Atomic(parse_bytes), # permitR
            Atomic(parse_bytes), # permitS
        ],
        field_definitions=[
        FieldDefinition((1,), 'Amount to withdraw', TokenAmountFormatter()),
        FieldDefinition((2,), 'To recipient', AddressNameFormatter),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("e74f7b85"),  # borrowETH(address pool, uint256 amount, uint16 referralCode)
        intent="Borrow",
        parameter_definitions=[
            Atomic(parse_address), # pool
            Atomic(parse_uint256), # amount
            Atomic(parse_uint16), # referralCode
        ],
        field_definitions=[
        FieldDefinition((1,), 'Amount to borrow', AmountFormatter),
        FieldDefinition(ContainerPath.From, 'Debtor', AddressNameFormatter),
        ],
    ),
]
