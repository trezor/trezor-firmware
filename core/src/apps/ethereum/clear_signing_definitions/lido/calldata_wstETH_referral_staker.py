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

BINDING_CONTEXT = BindingContext([(1, unhexlify('a88f0329c2c4ce51ba3fc619bbf44efe7120dd0d'))])

DISPLAY_FORMATS = [
    DisplayFormat(
        binding_context=BINDING_CONTEXT,
        func_sig=unhexlify("946fe3e8"),  # stakeETH(address)
        intent="Stake ETH",
        parameter_definitions=[
            Atomic(parse_address), # _referral
        ],
        field_definitions=[
        FieldDefinition(ContainerPath.Value, 'Amount to stake', AmountFormatter),
        ],
    ),
]
