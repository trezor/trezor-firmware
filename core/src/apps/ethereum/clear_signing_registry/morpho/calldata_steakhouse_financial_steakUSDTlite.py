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
    [(1, unhexlify("97ffedb80d4b2ca6105a07a4d90eb739c45a6660"))]
)

DISPLAY_FORMATS = [
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("6e553f65"),  # deposit(uint256 assets, address receiver)
        intent="Deposit",
        parameter_definitions=[
            Atomic(parse_uint256),  # assets
            Atomic(parse_address),  # receiver
        ],
        field_definitions=[
            FieldDefinition((0,), "Deposit asset", TokenAmountFormatter()),
            FieldDefinition((1,), "Send shares to", AddressNameFormatter),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("94bf804d"),  # mint(uint256 shares, address receiver)
        intent="Mint",
        parameter_definitions=[
            Atomic(parse_uint256),  # shares
            Atomic(parse_address),  # receiver
        ],
        field_definitions=[
            FieldDefinition(
                (0,),
                "Minted shares",
                TokenAmountFormatter(token_path=ContainerPath.TODO),
            ),
            FieldDefinition((1,), "Mint shares to", AddressNameFormatter),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify(
            "b460af94"
        ),  # withdraw(uint256 assets,address receiver,address owner)
        intent="Withdraw",
        parameter_definitions=[
            Atomic(parse_uint256),  # assets
            Atomic(parse_address),  # receiver
            Atomic(parse_address),  # owner
        ],
        field_definitions=[
            FieldDefinition((0,), "Withdraw exactly", TokenAmountFormatter()),
            FieldDefinition((1,), "To", AddressNameFormatter),
            FieldDefinition((2,), "Owner", AddressNameFormatter),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify(
            "ba087652"
        ),  # redeem(uint256 shares,address receiver,address owner)
        intent="Redeem",
        parameter_definitions=[
            Atomic(parse_uint256),  # shares
            Atomic(parse_address),  # receiver
            Atomic(parse_address),  # owner
        ],
        field_definitions=[
            FieldDefinition(
                (0,),
                "Shares to redeem",
                TokenAmountFormatter(token_path=ContainerPath.TODO),
            ),
            FieldDefinition((1,), "To", AddressNameFormatter),
            FieldDefinition((2,), "Owner", AddressNameFormatter),
        ],
    ),
]
