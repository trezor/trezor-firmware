from typing import Generator

from .clear_signing import (
    AddressNameFormatter,
    Atomic,
    ContainerPath,
    DisplayFormat,
    FieldDefinition,
    TokenAmountFormatter,
    parse_address,
    parse_uint256,
)

# https://github.com/ethereum/clear-signing-erc7730-registry/blob/master/ercs/calldata-erc20-tokens.json#L27

APPROVE_DISPLAY_FORMAT = DisplayFormat(
    binding_context=None,
    func_sig=b"\x09\x5e\xa7\xb3",  # approve(address,uint256)
    intent="Approve",
    provider_name=None,
    parameter_definitions=[
        Atomic(parse_address),  # _spender
        Atomic(parse_uint256),  # _value
    ],
    field_definitions=[
        FieldDefinition((0,), "Spender", AddressNameFormatter),
        FieldDefinition(
            (1,),
            "Amount",
            TokenAmountFormatter(
                token_path=ContainerPath.To,
                threshold=0x8000000000000000000000000000000000000000000000000000000000000000,
            ),
        ),
    ],
)

TRANSFER_DISPLAY_FORMAT = DisplayFormat(
    binding_context=None,
    func_sig=b"\xa9\x05\x9c\xbb",  # transfer(address,uint256)
    intent="Send",
    provider_name=None,
    parameter_definitions=[
        Atomic(parse_address),  # _to
        Atomic(parse_uint256),  # _value
    ],
    field_definitions=[
        FieldDefinition((0,), "To", AddressNameFormatter),
        FieldDefinition(
            (1,), "Amount", TokenAmountFormatter(token_path=ContainerPath.To)
        ),
    ],
)


def all_display_formats() -> Generator[DisplayFormat, None, None]:

    from .clear_signing import AmountFormatter, BindingContext

    yield APPROVE_DISPLAY_FORMAT
    yield TRANSFER_DISPLAY_FORMAT

    # Canonical WETH (Wrapped Ether) contracts holding the chain's native currency.
    # Wrapping is 1:1 and reversible, so the amounts are rendered with the native
    # currency formatter: deposit() wraps the transaction value into WETH and
    # withdraw(wad) unwraps the same amount of WETH back to the native currency.
    # https://github.com/trezor/trezor-firmware/issues/7252
    # The deployments list is generated from `sc_constants.py.mako`.
    from .sc_constants import weth_deployments

    WETH_CONTEXT = BindingContext(tuple(weth_deployments()))

    yield DisplayFormat(
        binding_context=WETH_CONTEXT,
        func_sig=b"\xd0\xe3\x0d\xb0",  # deposit()
        intent="Wrap ETH to WETH",
        provider_name=None,
        parameter_definitions=[],  # no arguments, the amount is the tx value
        field_definitions=[
            FieldDefinition(
                ContainerPath.Value,  # @.value
                "Amount",
                AmountFormatter,
            ),
        ],
    )

    yield DisplayFormat(
        binding_context=WETH_CONTEXT,
        func_sig=b"\x2e\x1a\x7d\x4d",  # withdraw(uint256)
        intent="Unwrap WETH to ETH",
        provider_name=None,
        parameter_definitions=[
            Atomic(parse_uint256),  # wad
        ],
        field_definitions=[
            FieldDefinition(
                (0,),  # wad
                "Amount",
                AmountFormatter,
            ),
        ],
    )

    if __debug__:
        from .clear_signing import (
            Array,
            DateFormatter,
            DynamicLeaf,
            RawFormatter,
            Tuple,
            UnitFormatter,
            make_fixed_bytes_parser,
            make_uint_parser,
            parse_bool,
            parse_bytes,
            parse_string,
        )

        parse_bytes32 = make_fixed_bytes_parser(32)
        parse_uint160 = make_uint_parser(160)

        # One contract to test it all would have been easier. But Caesar has a paragraph limit.
        #   * TREZOR_TEST_SCALARS_DESCRIPTOR  - scalar/atomic formatters
        #   * TREZOR_TEST_TOKEN_DESCRIPTOR    - token-amount resolution (path + const)
        #   * TREZOR_TEST_ARRAYS_DESCRIPTOR   - multi-value arrays
        #   * TREZOR_TEST_PATHS_DESCRIPTOR    - composite path styles (slices + nested)
        TREZOR_TEST_CHAIN_ID = 1
        TREZOR_TEST_ADDRESS = b"\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd"
        TREZOR_TEST_CONST_TOKEN = b"\xee\xee\xee\xee\xee\xee\xee\xee\xee\xee\xee\xee\xee\xee\xee\xee\xee\xee\xee\xee"
        TREZOR_TEST_NATIVE = b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"

        TREZOR_TEST_CONTEXT = BindingContext(
            [(TREZOR_TEST_CHAIN_ID, TREZOR_TEST_ADDRESS)]
        )

        # --- 1) scalar / atomic formatters ---
        yield DisplayFormat(
            binding_context=TREZOR_TEST_CONTEXT,
            func_sig=b"\x7e\x57\x7e\x01",  # synthetic selector (dummy contract)
            intent="Trezor Test Scalars. DO NOT USE",
            provider_name="Trezor Test. DO NOT USE",
            parameter_definitions=[
                Atomic(parse_address),  # 0 recipient
                Atomic(parse_uint256),  # 1 nativeAmount
                Atomic(parse_uint256),  # 2 rawInt
                Atomic(parse_uint256),  # 3 unitValue
                Atomic(parse_uint256),  # 4 timestamp
                Atomic(parse_bytes32),  # 5 hashBytes32
                Atomic(parse_bool),  # 6 flagBool
                Atomic(parse_uint160),  # 7 sizedUint
                DynamicLeaf(parse_string),  # 8 note
                DynamicLeaf(parse_bytes),  # 9 payload
            ],
            field_definitions=[
                FieldDefinition((0,), "Recipient", AddressNameFormatter),
                FieldDefinition((1,), "Native Amount", AmountFormatter),
                FieldDefinition((2,), "Raw Integer", RawFormatter),
                FieldDefinition(
                    (3,),
                    "Unit Value",
                    UnitFormatter(decimals=2, base=" UNIT", prefix=False),
                ),
                FieldDefinition((4,), "Date", DateFormatter),
                FieldDefinition((5,), "Raw Bytes32", RawFormatter),  # parse_bytes32
                FieldDefinition((6,), "Raw Bool", RawFormatter),  # parse_bool
                FieldDefinition((7,), "Raw Uint160", RawFormatter),  # parse_uint160
                FieldDefinition((8,), "Raw String", RawFormatter),  # string passthrough
                FieldDefinition((9,), "Raw Bytes", RawFormatter),  # bytes -> hex
            ],
        )

        # --- 2) token-amount resolution: via token_path and via constant address ---
        yield DisplayFormat(
            binding_context=TREZOR_TEST_CONTEXT,
            func_sig=b"\x7e\x57\x7e\x02",  # synthetic selector (dummy contract)
            intent="Trezor Test Token. DO NOT USE",
            provider_name="Trezor Test. DO NOT USE",
            parameter_definitions=[
                Atomic(parse_address),  # 0 token (target of token_path below)
                Atomic(parse_uint256),  # 1 tokenAmount
                Atomic(parse_uint256),  # 2 constTokenAmount
            ],
            field_definitions=[
                FieldDefinition(
                    (1,), "Token (via path)", TokenAmountFormatter(token_path=(0,))
                ),
                FieldDefinition(
                    (2,),
                    "Token (via constant)",
                    TokenAmountFormatter(const_token_address=TREZOR_TEST_CONST_TOKEN),
                ),
            ],
        )

        # --- 3) multi-value arrays ---
        yield DisplayFormat(
            binding_context=TREZOR_TEST_CONTEXT,
            func_sig=b"\x7e\x57\x7e\x03",  # synthetic selector (dummy contract)
            intent="Trezor Test Arrays. DO NOT USE",
            provider_name="Trezor Test. DO NOT USE",
            parameter_definitions=[
                Array(Atomic(parse_uint256)),  # 0 amounts (multi-value array)
                Array(
                    Atomic(parse_uint256)
                ),  # 1 tokenAmounts (multi-value tokenAmount)
                Array(Atomic(parse_uint256)),  # 2 dates (multi-value date)
            ],
            field_definitions=[
                FieldDefinition(
                    (0,), "Amounts (array)", RawFormatter
                ),  # multi-value raw
                # multi-value tokenAmount sharing one constant token
                FieldDefinition(
                    (1,),
                    "Token Amounts (array)",
                    TokenAmountFormatter(const_token_address=TREZOR_TEST_CONST_TOKEN),
                ),
                FieldDefinition(
                    (2,), "Dates (array)", DateFormatter
                ),  # multi-value date
            ],
        )

        # --- 4) composite path styles: bytes slicing + nested array-of-structs ---
        yield DisplayFormat(
            binding_context=TREZOR_TEST_CONTEXT,
            func_sig=b"\x7e\x57\x7e\x04",  # synthetic selector (dummy contract)
            intent="Trezor Test Paths. DO NOT USE",
            provider_name="Trezor Test. DO NOT USE",
            parameter_definitions=[
                Atomic(parse_uint256),  # 0 amount (reused by both slice fields)
                DynamicLeaf(parse_bytes),  # 1 packedPath (sliced for token addresses)
                Array(  # 2 swapData: (sendingAssetId, receivingAssetId, fromAmount)[]
                    Tuple(
                        (parse_address, parse_address, parse_uint256),
                        is_dynamic=False,
                    )
                ),
            ],
            field_definitions=[
                # token_path slicing a packed bytes blob: packedPath[0:20] / [-20:]
                FieldDefinition(
                    (0,),
                    "Token (path[0:20] slice)",
                    TokenAmountFormatter(token_path=(1, (0, 20))),
                ),
                FieldDefinition(
                    (0,),
                    "Token (path[-20:] slice)",
                    TokenAmountFormatter(token_path=(1, (-20,))),
                ),
                # nested array-of-structs: swapData[0].fromAmount, token sendingAssetId
                FieldDefinition(
                    (2, 0, 2),
                    "Token (nested swap[0])",
                    TokenAmountFormatter(token_path=(2, 0, 0)),
                ),
                # negative index + native currency: swapData[-1].fromAmount, token
                # swapData[-1].receivingAssetId (the native sentinel -> renders native)
                FieldDefinition(
                    (2, -1, 2),
                    "Token (neg index swap[-1], native)",
                    TokenAmountFormatter(
                        token_path=(2, -1, 1),
                        native_currency_address=[TREZOR_TEST_NATIVE],
                    ),
                ),
            ],
        )
