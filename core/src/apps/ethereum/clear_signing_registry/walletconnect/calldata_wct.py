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
        (10, unhexlify("ef4461891dfb3ac8572ccf7c794664a8dd927945")),
        (1, unhexlify("ef4461891dfb3ac8572ccf7c794664a8dd927945")),
        (8453, unhexlify("ef4461891dfb3ac8572ccf7c794664a8dd927945")),
    ]
)

DISPLAY_FORMATS = [
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("a9059cbb"),  # transfer(address,uint256)
        intent="Send",
        parameter_definitions=[
            Atomic(parse_address),  # to
            Atomic(parse_uint256),  # value
        ],
        field_definitions=[
            FieldDefinition(
                (1,), "Amount", TokenAmountFormatter(token_path=ContainerPath.TODO)
            ),
            FieldDefinition((0,), "To", AddressNameFormatter),
        ],
    ),
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("095ea7b3"),  # approve(address,uint256)
        intent="Approve",
        parameter_definitions=[
            Atomic(parse_address),  # spender
            Atomic(parse_uint256),  # value
        ],
        field_definitions=[
            FieldDefinition((0,), "Spender", AddressNameFormatter),
            FieldDefinition(
                (1,), "Amount", TokenAmountFormatter(token_path=ContainerPath.TODO)
            ),
        ],
    ),
]
