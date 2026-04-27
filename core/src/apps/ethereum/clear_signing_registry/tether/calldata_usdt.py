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
        (1, unhexlify("dac17f958d2ee523a2206206994597c13d831ec7")),
        (137, unhexlify("c2132d05d31c914a87c6611c10748aeb04b58e8f")),
    ]
)

DISPLAY_FORMATS = [
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("a9059cbb"),  # transfer(address,uint256)
        intent="Send",
        parameter_definitions=[
            Atomic(parse_address),  # _to
            Atomic(parse_uint256),  # _value
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
            Atomic(parse_address),  # _spender
            Atomic(parse_uint256),  # _value
        ],
        field_definitions=[
            FieldDefinition((0,), "Spender", AddressNameFormatter),
            FieldDefinition(
                (1,), "Amount", TokenAmountFormatter(token_path=ContainerPath.TODO)
            ),
        ],
    ),
]
