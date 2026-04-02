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
        (1, unhexlify("87870bca3f3fd6335c3f4ce8392d69350b4fa4e2")),
        (8453, unhexlify("a238dd80c259a72e81d7e4664a9801593f98d1c5")),
        (42220, unhexlify("3e59a31363e2ad014dcbc521c4a0d5757d9f3402")),
        (59144, unhexlify("c47b8c00b0f69a36fa203ffeac0334874574a8ac")),
        (59144, unhexlify("c47b8c00b0f69a36fa203ffeac0334874574a8ac")),
        (1088, unhexlify("90df02551bb792286e8d4f13e0e357b4bf1d6a57")),
        (146, unhexlify("5362dbb1e601abf3a4c14c22ffeda64042e5eaa3")),
        (100, unhexlify("b50201558b00496a145fe76f7424749556e326d8")),
        (534352, unhexlify("11fcfe756c05ad438e312a7fd934381537d3cffe")),
        (324, unhexlify("78e30497a3c7527d953c6b1e3541b021a98ac43c")),
        (137, unhexlify("794a61358d6845594f94dc1db02a252b5b4814ad")),
        (1868, unhexlify("dd3d7a7d03d9fd9ef45f3e587287922ef65ca38b")),
        (42161, unhexlify("794a61358d6845594f94dc1db02a252b5b4814ad")),
        (10, unhexlify("794a61358d6845594f94dc1db02a252b5b4814ad")),
        (43114, unhexlify("794a61358d6845594f94dc1db02a252b5b4814ad")),
        (9745, unhexlify("925a2a7214ed92428b5b1b090f80b25700095e12")),
    ]
)

DISPLAY_FORMATS = [
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify(
            "573ade81"
        ),  # repay(address asset, uint256 amount, uint256 interestRateMode, address onBehalfOf)
        intent="Repay loan",
        parameter_definitions=[
            Atomic(parse_address),  # asset
            Atomic(parse_uint256),  # amount
            Atomic(parse_uint256),  # interestRateMode
            Atomic(parse_address),  # onBehalfOf
        ],
        field_definitions=[
            FieldDefinition(
                (1,), "Amount to repay", TokenAmountFormatter(token_path=(0,))
            ),
            FieldDefinition((2,), "Interest rate mode", TODOFormatter()),
            FieldDefinition((3,), "For debt holder", AddressNameFormatter),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify(
            "ee3e210b"
        ),  # repayWithPermit(address asset, uint256 amount, uint256 interestRateMode, address onBehalfOf, uint256 deadline, uint8 permitV, bytes32 permitR, bytes32 permitS)
        intent="Repay loan",
        parameter_definitions=[
            Atomic(parse_address),  # asset
            Atomic(parse_uint256),  # amount
            Atomic(parse_uint256),  # interestRateMode
            Atomic(parse_address),  # onBehalfOf
            Atomic(parse_uint256),  # deadline
            Atomic(parse_uint8),  # permitV
            Atomic(parse_bytes),  # permitR
            Atomic(parse_bytes),  # permitS
        ],
        field_definitions=[
            FieldDefinition(
                (1,), "Amount to repay", TokenAmountFormatter(token_path=(0,))
            ),
            FieldDefinition((2,), "Interest rate mode", TODOFormatter()),
            FieldDefinition((3,), "For debt holder", AddressNameFormatter),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify(
            "2dad97d4"
        ),  # repayWithATokens(address asset, uint256 amount, uint256 interestRateMode)
        intent="Repay with aTokens",
        parameter_definitions=[
            Atomic(parse_address),  # asset
            Atomic(parse_uint256),  # amount
            Atomic(parse_uint256),  # interestRateMode
        ],
        field_definitions=[
            FieldDefinition(
                (1,), "Amount to repay", TokenAmountFormatter(token_path=(0,))
            ),
            FieldDefinition((2,), "Interest rate mode", TODOFormatter()),
            FieldDefinition(
                ContainerPath.From, "For debt holder", AddressNameFormatter
            ),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify(
            "5a3b74b9"
        ),  # setUserUseReserveAsCollateral(address asset, bool useAsCollateral)
        intent="Manage collateral",
        parameter_definitions=[
            Atomic(parse_address),  # asset
            Atomic(parse_bool),  # useAsCollateral
        ],
        field_definitions=[
            FieldDefinition((0,), "For asset", AddressNameFormatter),
            FieldDefinition((1,), "Use as collateral", TODOFormatter()),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify(
            "972b35fa"
        ),  # setUserUseReserveAsCollateralOnBehalfOf(address asset, bool useAsCollateral, address onBehalfOf)
        intent="Manage collateral",
        parameter_definitions=[
            Atomic(parse_address),  # asset
            Atomic(parse_bool),  # useAsCollateral
            Atomic(parse_address),  # onBehalfOf
        ],
        field_definitions=[
            FieldDefinition((0,), "For asset", AddressNameFormatter),
            FieldDefinition((1,), "Use as collateral", TODOFormatter()),
            FieldDefinition((2,), "Debtor", AddressNameFormatter),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify(
            "69328dec"
        ),  # withdraw(address asset, uint256 amount, address to)
        intent="Withdraw",
        parameter_definitions=[
            Atomic(parse_address),  # asset
            Atomic(parse_uint256),  # amount
            Atomic(parse_address),  # to
        ],
        field_definitions=[
            FieldDefinition(
                (1,), "Amount to withdraw", TokenAmountFormatter(token_path=(0,))
            ),
            FieldDefinition((2,), "To recipient", AddressNameFormatter),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify(
            "a415bcad"
        ),  # borrow(address asset, uint256 amount, uint256 interestRateMode, uint16 referralCode, address onBehalfOf)
        intent="Borrow",
        parameter_definitions=[
            Atomic(parse_address),  # asset
            Atomic(parse_uint256),  # amount
            Atomic(parse_uint256),  # interestRateMode
            Atomic(parse_uint16),  # referralCode
            Atomic(parse_address),  # onBehalfOf
        ],
        field_definitions=[
            FieldDefinition(
                (1,), "Amount to borrow", TokenAmountFormatter(token_path=(0,))
            ),
            FieldDefinition((2,), "Interest Rate mode", TODOFormatter()),
            FieldDefinition((4,), "Debtor", AddressNameFormatter),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify(
            "e8eda9df"
        ),  # deposit(address asset, uint256 amount, address onBehalfOf, uint16 referralCode)
        intent="Supply",
        parameter_definitions=[
            Atomic(parse_address),  # asset
            Atomic(parse_uint256),  # amount
            Atomic(parse_address),  # onBehalfOf
            Atomic(parse_uint16),  # referralCode
        ],
        field_definitions=[
            FieldDefinition(
                (1,), "Amount to supply", TokenAmountFormatter(token_path=(0,))
            ),
            FieldDefinition((2,), "Collateral recipient", AddressNameFormatter),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify(
            "617ba037"
        ),  # supply(address asset, uint256 amount, address onBehalfOf, uint16 referralCode)
        intent="Supply",
        parameter_definitions=[
            Atomic(parse_address),  # asset
            Atomic(parse_uint256),  # amount
            Atomic(parse_address),  # onBehalfOf
            Atomic(parse_uint16),  # referralCode
        ],
        field_definitions=[
            FieldDefinition(
                (1,), "Amount to supply", TokenAmountFormatter(token_path=(0,))
            ),
            FieldDefinition((2,), "Collateral recipient", AddressNameFormatter),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify(
            "02c205f0"
        ),  # supplyWithPermit(address asset, uint256 amount, address onBehalfOf, uint16 referralCode, uint256 deadline, uint8 permitV, bytes32 permitR, bytes32 permitS)
        intent="Supply",
        parameter_definitions=[
            Atomic(parse_address),  # asset
            Atomic(parse_uint256),  # amount
            Atomic(parse_address),  # onBehalfOf
            Atomic(parse_uint16),  # referralCode
            Atomic(parse_uint256),  # deadline
            Atomic(parse_uint8),  # permitV
            Atomic(parse_bytes),  # permitR
            Atomic(parse_bytes),  # permitS
        ],
        field_definitions=[
            FieldDefinition(
                (1,), "Amount to supply", TokenAmountFormatter(token_path=(0,))
            ),
            FieldDefinition((2,), "Collateral recipient", AddressNameFormatter),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify(
            "b8caa7c5"
        ),  # approvePositionManager(address positionManager, bool approve)
        intent="Approve Manager",
        parameter_definitions=[
            Atomic(parse_address),  # positionManager
            Atomic(parse_bool),  # approve
        ],
        field_definitions=[
            FieldDefinition((0,), "Position manager", AddressNameFormatter),
            FieldDefinition((1,), "Approve", TODOFormatter()),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("fea149a6"),  # renouncePositionManagerRole(address user)
        intent="Revoke Manager Role",
        parameter_definitions=[
            Atomic(parse_address),  # user
        ],
        field_definitions=[
            FieldDefinition(
                ContainerPath.From, "Position manager", AddressNameFormatter
            ),
            FieldDefinition((0,), "User", AddressNameFormatter),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("ac9650d8"),  # multicall(bytes[] data)
        intent="Multicall",
        parameter_definitions=[
            Array(Dynamic(parse_bytes)),  # data
        ],
        field_definitions=[
            FieldDefinition((0,), "Call", TODOFormatter()),
        ],
    ),
]
