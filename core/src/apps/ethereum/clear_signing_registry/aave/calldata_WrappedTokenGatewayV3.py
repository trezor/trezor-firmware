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
        (1, unhexlify("d01607c3c5ecaba394d8be377a08590149325722")),
        (10, unhexlify("5f2508cae9923b02316254026cd43d7902866725")),
        (100, unhexlify("721b9abab6511b46b9ee83a1aba23bdacb004149")),
        (137, unhexlify("bc302053db3aa514a3c86b9221082f162b91ad63")),
        (146, unhexlify("61d8e131f26512348ee5fa42e2df1ba9d6505e90")),
        (324, unhexlify("ae2b00d676130bdf22582781bbba8f4f21e8b0ff")),
        (1868, unhexlify("6376d4df995f32f308f2d5049a7a320943023232")),
        (8453, unhexlify("a0d9c1e9e48ca30c8d8c3b5d69ff5dc1f6dffc24")),
        (9745, unhexlify("54bdcc37c4143f944a3ee51c892a6cbdf305e7a0")),
        (42161, unhexlify("5283beced7adf6d003225c13896e536f2d4264ff")),
        (43114, unhexlify("2825ce5921538d17cc15ae00a8b24ff759c6cdae")),
        (59144, unhexlify("31a239f3e39c5d8ba6b201ba81ed584492ae960f")),
        (534352, unhexlify("e79ca44408dae5a57ea2a9594532f1e84d2edaa4")),
    ]
)

DISPLAY_FORMATS = [
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify(
            "474cf53d"
        ),  # depositETH(address pool, address onBehalfOf, uint16 referralCode)
        intent="Supply",
        parameter_definitions=[
            Atomic(parse_address),  # pool
            Atomic(parse_address),  # onBehalfOf
            Atomic(parse_uint16),  # referralCode
        ],
        field_definitions=[
            FieldDefinition(ContainerPath.Value, "Amount to supply", AmountFormatter),
            FieldDefinition((1,), "Collateral recipient", AddressNameFormatter),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify(
            "bcc3c255"
        ),  # repayETH(address pool, uint256 amount, address onBehalfOf)
        intent="Repay loan",
        parameter_definitions=[
            Atomic(parse_address),  # pool
            Atomic(parse_uint256),  # amount
            Atomic(parse_address),  # onBehalfOf
        ],
        field_definitions=[
            FieldDefinition((1,), "Amount to repay", AmountFormatter),
            FieldDefinition((2,), "For debt holder", AddressNameFormatter),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify(
            "80500d20"
        ),  # withdrawETH(address pool, uint256 amount, address to)
        intent="Withdraw",
        parameter_definitions=[
            Atomic(parse_address),  # pool
            Atomic(parse_uint256),  # amount
            Atomic(parse_address),  # to
        ],
        field_definitions=[
            FieldDefinition((1,), "Amount to withdraw", TokenAmountFormatter()),
            FieldDefinition((2,), "To recipient", AddressNameFormatter),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify(
            "d4c40b6c"
        ),  # withdrawETHWithPermit(address, uint256 amount, address to, uint256 deadline, uint8 permitV, bytes32 permitR, bytes32 permitS)
        intent="Withdraw",
        parameter_definitions=[
            Atomic(parse_address),  # pool
            Atomic(parse_uint256),  # amount
            Atomic(parse_address),  # to
            Atomic(parse_uint256),  # deadline
            Atomic(parse_uint8),  # permitV
            Atomic(parse_bytes),  # permitR
            Atomic(parse_bytes),  # permitS
        ],
        field_definitions=[
            FieldDefinition((1,), "Amount to withdraw", TokenAmountFormatter()),
            FieldDefinition((2,), "To recipient", AddressNameFormatter),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify(
            "e74f7b85"
        ),  # borrowETH(address pool, uint256 amount, uint16 referralCode)
        intent="Borrow",
        parameter_definitions=[
            Atomic(parse_address),  # pool
            Atomic(parse_uint256),  # amount
            Atomic(parse_uint16),  # referralCode
        ],
        field_definitions=[
            FieldDefinition((1,), "Amount to borrow", AmountFormatter),
            FieldDefinition(ContainerPath.From, "Debtor", AddressNameFormatter),
        ],
    ),
]
