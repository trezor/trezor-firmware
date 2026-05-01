from micropython import const
from typing import TYPE_CHECKING

from trezor import TR

from .definitions import Definitions
from .helpers import (
    address_from_bytes,
    bytes_from_address,
    format_ethereum_amount,
    get_account_and_path,
)

if TYPE_CHECKING:
    from buffer_types import AnyBytes
    from typing import Callable, Iterable

    from trezor.messages import (
        EthereumABIValueInfo,
        EthereumERC7730FieldInfo,
        EthereumTokenInfo,
    )
    from trezor.ui.layouts import StrPropertyType
    from typing_extensions import Self

    from apps.common.payment_request import PaymentRequestVerifier

    from .keychain import MsgInSignTx

    # Represents values that have been parsed from the calldata
    # into our internal representation.
    Value = int | bytes | bool | str | None | list["Value"]
    TupleValue = tuple[Value, ...]
    ListValue = list[TupleValue]
    AnyValue = Value | TupleValue | ListValue | list[Value | TupleValue | ListValue]

    Path = tuple[int | tuple[int] | tuple[int, int], ...] | int
    PathWalker = Callable[[Path], Value]

    # Parses a Value from a slice of the calldata.
    # Assumes that the memoryview contains just that value.
    Parser = Callable[[memoryview], AnyValue]


SC_FUNC_SIG_BYTES = const(4)


class ClearSigningFailed(Exception):
    pass


class InvalidFunctionCall(ClearSigningFailed):
    """Raised when the calldata encoding of a function call,
    including its parameters, is invalid."""

    pass


class ValueOverflow(InvalidFunctionCall):
    """Raised when a value that should be encoded on less than 32 bytes
    actually uses more bytes than it should."""

    pass


class DirtyAddress(ValueOverflow):
    pass


class OutOfBounds(InvalidFunctionCall):
    """Raised when we try to read outside the bounds of the raw data."""

    pass


class InvalidFormatDefinition(ClearSigningFailed):
    """Raised when we fail to format data according to the definitions,
    if for example the parsed calldata has other types than what
    the format definition expects."""

    pass


# Value Parsers


def _check_padding_zero(
    raw_data: memoryview, used_bytes: int, exc: type[ValueOverflow] = ValueOverflow
) -> None:
    """Sanity check to make sure unused data is zeroed out."""
    if any(raw_data[: 32 - used_bytes]):
        raise exc


def parse_address(raw_data: memoryview) -> Value:
    _ZERO_PADDING = const(20)
    if len(raw_data) < 32:
        raise OutOfBounds
    _check_padding_zero(raw_data, _ZERO_PADDING, DirtyAddress)
    return bytes(raw_data[32 - _ZERO_PADDING :])


def parse_uint256(raw_data: memoryview) -> Value:
    if len(raw_data) < 32:
        raise OutOfBounds
    return int.from_bytes(raw_data, "big")


def _make_uint_parser(bit_width: int) -> "Parser":
    byte_width = bit_width // 8

    def parser(raw_data: memoryview) -> Value:
        if len(raw_data) < 32:
            raise OutOfBounds
        _check_padding_zero(raw_data, byte_width)
        return parse_uint256(raw_data)

    return parser


parse_uint248 = _make_uint_parser(248)
parse_uint160 = _make_uint_parser(160)
parse_uint128 = _make_uint_parser(128)
parse_uint120 = _make_uint_parser(120)
parse_uint112 = _make_uint_parser(112)
parse_uint96 = _make_uint_parser(96)
parse_uint72 = _make_uint_parser(72)
parse_uint64 = _make_uint_parser(64)
parse_uint48 = _make_uint_parser(48)
parse_uint40 = _make_uint_parser(40)
parse_uint32 = _make_uint_parser(32)
parse_uint24 = _make_uint_parser(24)
parse_uint16 = _make_uint_parser(16)
parse_uint8 = _make_uint_parser(8)


def parse_bool(raw_data: memoryview) -> Value:
    if len(raw_data) < 32:
        raise OutOfBounds
    uint_value = parse_uint256(raw_data)
    if uint_value not in (0, 1):
        raise ValueOverflow
    return uint_value == 1


def parse_bytes(raw_data: memoryview) -> Value:
    return bytes(raw_data)


def parse_string(raw_data: memoryview) -> Value:
    return bytes(raw_data).decode("utf-8")


def parse_uint256_array(raw_data: memoryview) -> list[Value]:
    return [
        parse_uint256(raw_data[i * 32 : (i + 1) * 32])
        for i in range(len(raw_data) // 32)
    ]


DYNAMIC_DATA_PARSERS = [parse_bytes, parse_string, parse_uint256_array]


def _get_parser(t: int) -> Parser:
    """Get a parser for a type we received over the wire protocol."""
    from trezor.enums import EthereumABIType as T

    if t == T.ABI_ADDRESS:
        return parse_address
    elif t == T.ABI_BYTES:
        return parse_bytes
    elif t == T.ABI_STRING:
        return parse_string
    elif t == T.ABI_UINT256:
        return parse_uint256
    elif t == T.ABI_UINT248:
        return parse_uint248
    elif t == T.ABI_UINT160:
        return parse_uint160
    elif t == T.ABI_UINT128:
        return parse_uint128
    elif t == T.ABI_UINT120:
        return parse_uint120
    elif t == T.ABI_UINT112:
        return parse_uint112
    elif t == T.ABI_UINT96:
        return parse_uint96
    elif t == T.ABI_UINT72:
        return parse_uint72
    elif t == T.ABI_UINT64:
        return parse_uint64
    elif t == T.ABI_UINT48:
        return parse_uint48
    elif t == T.ABI_UINT40:
        return parse_uint40
    elif t == T.ABI_UINT32:
        return parse_uint32
    elif t == T.ABI_UINT24:
        return parse_uint24
    elif t == T.ABI_UINT16:
        return parse_uint16
    elif t == T.ABI_UINT8:
        return parse_uint8
    elif t == T.ABI_BOOL:
        return parse_bool
    raise InvalidFormatDefinition


def _get_leaf_parser(info: EthereumABIValueInfo) -> Parser:
    """Get a parser for a leaf (atomic or dynamic) value. Raises for nested structures."""
    if info.atomic is not None:
        return _get_parser(info.atomic)
    elif info.dynamic is not None:
        return _get_parser(info.dynamic)
    raise InvalidFormatDefinition


# Field formatters: https://eips.ethereum.org/EIPS/eip-7730#field-formats


class FieldFormatter:
    async def format(
        self,
        value: AnyValue,
        msg: MsgInSignTx,
        defs: Definitions,
        path_walker: PathWalker,
    ) -> tuple[str | None, EthereumTokenInfo | None, AnyBytes | None]:
        """
        Format a field using the current formatter.
        Return the formatted value and optionally a token and a token address,
        if formatting this value implied dealing with a new token
        (like getting a token from parameters using `token_path`).
        """
        raise NotImplementedError


class AddressNameFormatter(FieldFormatter):
    async def format(
        self,
        address: AnyValue,
        _msg: MsgInSignTx,
        defs: Definitions,
        _path_walker: PathWalker,
    ) -> tuple[str | None, EthereumTokenInfo | None, AnyBytes | None]:
        if address is None:
            return None, None, None
        elif isinstance(address, str):
            return address, None, None
        else:
            if not isinstance(address, bytes):
                raise InvalidFormatDefinition
            return address_from_bytes(address, defs.network), None, None


class AmountFormatter(FieldFormatter):
    async def format(
        self,
        amount: AnyValue,
        _msg: MsgInSignTx,
        defs: Definitions,
        _path_walker: PathWalker,
    ) -> tuple[str | None, EthereumTokenInfo | None, AnyBytes | None]:
        if amount is None:
            return None, None, None
        else:
            if not isinstance(amount, int):
                raise InvalidFormatDefinition

            # Note: we are passing None rather than `_token`
            # to `format_ethereum_amount` because this formatter
            # is meant to be used with native ETH amounts
            return format_ethereum_amount(amount, None, defs.network), None, None


class TokenAmountFormatter(FieldFormatter):
    # TODO: figure out a way for the formatter to signal that the amount was above the threshold.
    # For now we return None and `confirm_ethereum_approve` shows the "Unlimited amount" warning,
    # but the `tokenAmount` spec allows this message to be customized in which case
    # being above the threshold could mean something else, not just "Unlimited".

    def __init__(
        self,
        token_path: Path,
        native_currency_address: list[bytes] | None = None,
        threshold: int | None = None,
    ) -> None:
        self.token_path = token_path
        self.native_currency_address = native_currency_address
        self.threshold = threshold

    async def format(
        self,
        amount: AnyValue,
        msg: MsgInSignTx,
        defs: Definitions,
        path_walker: PathWalker,
    ) -> tuple[str | None, EthereumTokenInfo | None, AnyBytes | None]:
        from .tokens import UNKNOWN_TOKEN

        if amount is None:
            return None, None, None

        if not isinstance(amount, int):
            raise InvalidFormatDefinition

        token_address = path_walker(self.token_path)
        if not isinstance(token_address, bytes):
            raise InvalidFormatDefinition

        if self.native_currency_address is not None:
            if token_address in self.native_currency_address:
                if self.threshold is not None and amount > self.threshold:
                    return None, None, None
                else:
                    return (
                        format_ethereum_amount(amount, None, defs.network),
                        None,
                        None,
                    )

        # Non-native currency - dealing with tokens

        token = defs.get_token(token_address)
        if token is UNKNOWN_TOKEN:
            if msg.supports_definition_request:
                received_definitions, _ = await _request_definitions(
                    msg.chain_id, token_address, func_sig=None
                )
                if received_definitions is not None:
                    token = received_definitions.get_token(token_address)

        if self.threshold is not None and amount > self.threshold:
            return None, token, token_address
        else:
            return (
                format_ethereum_amount(amount, token, defs.network),
                token,
                token_address,
            )


class UnitFormatter(FieldFormatter):
    def __init__(self, decimals: int = 0, base: str = "", prefix: bool = False) -> None:
        self.decimals = decimals
        self.base = base
        self.prefix = prefix

    async def format(
        self,
        value: AnyValue,
        _msg: MsgInSignTx,
        _definitions: Definitions,
        _path_walker: PathWalker,
    ) -> tuple[str | None, EthereumTokenInfo | None, AnyBytes | None]:
        if value is None:
            return None, None, None
        else:
            if not isinstance(value, int):
                raise InvalidFormatDefinition

            scaled_value = value / (10**self.decimals)

            if not self.prefix or scaled_value == 0:
                return f"{scaled_value:g}{self.base}", None, None

            si_prefixes = {12: "T", 9: "G", 6: "M", 3: "k", 0: "", -3: "m"}

            temp_val = abs(scaled_value)
            exponent = 0
            if temp_val >= 1:
                while temp_val >= 1000 and exponent < 12:
                    temp_val /= 1000
                    exponent += 3
            else:
                while temp_val < 1 and exponent > -3:
                    temp_val *= 1000
                    exponent -= 3

            significand = scaled_value / (10**exponent)
            prefix_symbol = si_prefixes.get(exponent, "")

            return f"{significand:g}{prefix_symbol}{self.base}", None, None


# https://eips.ethereum.org/EIPS/eip-7730#context-section


class BindingContext:
    def __init__(self, deployments: Iterable[tuple[int, bytes]]) -> None:
        self.deployments = deployments

    def matches(self, chain_id: int, address: bytes) -> bool:
        for d_chain_id, d_address in self.deployments:
            if d_chain_id == chain_id and d_address == address:
                return True
        return False


# https://eips.ethereum.org/EIPS/eip-7730#structured-data-format-specification


class ABIValue:
    def parse(self, raw_data: memoryview, offset: int) -> tuple[AnyValue, int]:
        raise NotImplementedError

    @staticmethod
    def from_proto(info: EthereumABIValueInfo) -> "ABIValue":
        if info.atomic is not None:
            return Atomic(_get_parser(info.atomic))
        elif info.dynamic is not None:
            return Dynamic(_get_parser(info.dynamic))
        elif info.tuple is not None:
            return Tuple(
                tuple(_get_leaf_parser(f) for f in info.tuple.fields),
                info.tuple.is_dynamic,
            )
        elif info.array is not None:
            element = info.array
            if element.atomic is not None:
                return Array(Atomic(_get_parser(element.atomic)))
            elif element.dynamic is not None:
                return Array(Dynamic(_get_parser(element.dynamic)))
            elif element.tuple is not None:
                return Array(
                    Tuple(
                        tuple(_get_leaf_parser(f) for f in element.tuple.fields),
                        is_dynamic=False,  # Tuples inside Arrays are always parsed as static!
                    )
                )
            raise InvalidFormatDefinition  # Array of arrays not supported
        raise InvalidFormatDefinition


class Atomic(ABIValue):
    """Atomic values, such as integers or addresses, are always stored on 32 bytes."""

    def __init__(self, parser: Parser) -> None:
        self.parser = parser

    def parse(self, raw_data: memoryview, offset: int) -> tuple[AnyValue, int]:
        if offset > len(raw_data):
            raise OutOfBounds
        return self.parser(raw_data[offset : offset + 32]), 32


class Dynamic(ABIValue):
    """Dynamic values, such as strings or `bytes` are stored later in the calldata,
    the inline value being just a pointer to the actual location.
    Also they have an arbitrary length, which is encoded on the first 32 bytes,
    after which the actual value follows."""

    def __init__(self, parser: Parser) -> None:
        self.parser = parser

    def parse(self, raw_data: memoryview, offset: int) -> tuple[AnyValue, int]:
        if offset + 32 > len(raw_data):
            raise OutOfBounds
        pointer = int.from_bytes(raw_data[offset : offset + 32], "big")
        if pointer + 32 > len(raw_data):
            raise OutOfBounds
        length = int.from_bytes(raw_data[pointer : pointer + 32], "big")
        if pointer + 32 + length > len(raw_data):
            raise OutOfBounds
        data = raw_data[pointer + 32 : pointer + 32 + length]
        return self.parser(data), 32


class Tuple(ABIValue):
    """Tuples (or Structs, which are essentially the same thing as far as ABI is concerned)
    contain multiple values of different types.
    A Tuple is "dynamic" if at least one of the values is dynamic.
    However, dynamic structs inside arrays behave as static structs,
    hence we cannot guess if the Tuple is dynamic by looking at just its fields."""

    def __init__(self, fields: tuple[Parser, ...], is_dynamic: bool) -> None:
        self.fields = fields
        self.is_dynamic = is_dynamic
        self.static_size = len(fields) * 32

    def parse(self, raw_data: memoryview, offset: int) -> tuple[TupleValue, int]:
        if not self.is_dynamic:
            base_offset = offset
            consumed = self.static_size
        else:
            if offset + 32 > len(raw_data):
                raise OutOfBounds
            pointer = int.from_bytes(raw_data[offset : offset + 32], "big")
            base_offset = pointer
            consumed = 32  # dynamic structs just consume the pointer

        if base_offset + self.static_size > len(raw_data):
            raise OutOfBounds

        value: list[Value] = [None] * len(self.fields)

        for i, parser in enumerate(self.fields):
            field_head_pos = base_offset + (i * 32)
            raw_field = raw_data[field_head_pos : field_head_pos + 32]
            if parser not in DYNAMIC_DATA_PARSERS:
                v = parser(raw_field)
                if isinstance(v, (tuple, list)):
                    # Tuple or Array inside a Tuple
                    raise NotImplementedError
                value[i] = v
            else:
                field_pointer = base_offset + int.from_bytes(raw_field, "big")

                if field_pointer + 32 > len(raw_data):
                    raise OutOfBounds
                length = int.from_bytes(
                    raw_data[field_pointer : field_pointer + 32], "big"
                )
                if field_pointer + 32 + length > len(raw_data):
                    raise OutOfBounds
                raw_field = raw_data[field_pointer + 32 : field_pointer + 32 + length]
                v = parser(raw_field)
                if isinstance(v, (tuple, list)):
                    # Tuple or Array inside a Tuple
                    raise NotImplementedError
                value[i] = v
        return tuple(value), consumed


class Array(ABIValue):
    """Arrays are sequences of value of the same type."""

    def __init__(self, element_definition: ABIValue) -> None:
        self.element_definition = element_definition

    def parse(self, raw_data: memoryview, offset: int) -> tuple[ListValue, int]:
        if offset + 32 > len(raw_data):
            raise OutOfBounds
        array_pointer = int.from_bytes(raw_data[offset : offset + 32], "big")
        if array_pointer + 32 > len(raw_data):
            raise OutOfBounds
        array_length = int.from_bytes(
            raw_data[array_pointer : array_pointer + 32], "big"
        )
        array_heads_end = array_pointer + 32 + (array_length * 32)
        if array_heads_end > len(raw_data):
            raise OutOfBounds

        value = []

        for i in range(array_length):
            p = array_pointer + 32 + (i * 32)
            if p + 32 > len(raw_data):
                raise OutOfBounds
            if isinstance(self.element_definition, Atomic):
                # atomic types are encoded in place
                data, _ = self.element_definition.parse(raw_data, p)
            else:
                element_pointer = int.from_bytes(raw_data[p : p + 32], "big")
                element_absolute_pointer = array_pointer + 32 + element_pointer
                data, _ = self.element_definition.parse(
                    raw_data, element_absolute_pointer
                )
            value.append(data)

        return value, 32  # arrays just consume the pointer


# https://eips.ethereum.org/EIPS/eip-7730#evm-transaction-container


# Note: Keep this in sync with `EthereumERC7730ContainerPath` from `messages-definitions.proto`.
class ContainerPath:
    From = 1
    Value = 2
    To = 3


class FieldDefinition:
    def __init__(
        self,
        path: Path,
        label: str,
        formatter: FieldFormatter | type[FieldFormatter],
    ) -> None:
        self.path = path
        self.label = label
        self.formatter = formatter

    @staticmethod
    def from_proto(info: EthereumERC7730FieldInfo) -> "FieldDefinition":
        from trezor.enums import EthereumERC7730FieldFormatterType as FT
        from trezor.messages import EthereumERC7730Path

        def decode_path(p: EthereumERC7730Path) -> Path:
            if p.container_path is not None:
                return p.container_path
            return tuple(p.path)

        path = decode_path(info.path)

        fmt_type = info.formatter
        if fmt_type == FT.FORMATTER_ADDRESS_NAME:
            formatter = AddressNameFormatter
        elif fmt_type == FT.FORMATTER_AMOUNT:
            formatter = AmountFormatter
        elif fmt_type == FT.FORMATTER_TOKEN_AMOUNT:
            formatter_params = {}
            if info.token_path is not None:
                formatter_params["token_path"] = decode_path(info.token_path)
            if info.threshold is not None:
                formatter_params["threshold"] = int.from_bytes(info.threshold, "big")
            formatter = TokenAmountFormatter(**formatter_params)
        elif fmt_type == FT.FORMATTER_UNIT:
            formatter_params = {}
            if info.decimals is not None:
                formatter_params["decimals"] = info.decimals
            if info.base is not None:
                formatter_params["base"] = info.base
            if info.prefix is not None:
                formatter_params["prefix"] = info.prefix
            formatter = UnitFormatter(**formatter_params)
        else:
            raise InvalidFormatDefinition

        return FieldDefinition(path=path, label=info.label, formatter=formatter)

    def get_formatter(self) -> FieldFormatter:
        # instantiate formatters only if needed
        formatter = self.formatter
        if isinstance(formatter, type):
            formatter = formatter()
        return formatter


class DisplayFormat:
    def __init__(
        self,
        binding_context: BindingContext | None,
        func_sig: bytes,
        intent: str,
        parameter_definitions: list[ABIValue],
        field_definitions: list[FieldDefinition],
    ) -> None:
        self.binding_context = binding_context
        self.func_sig = func_sig
        self.intent = intent
        self.parameter_definitions = parameter_definitions
        self.field_definitions = field_definitions

        self.parameters = []

    def matches_context(self, chain_id: int, address: bytes) -> bool:
        if self.binding_context is None:
            # applies to anything without context verification
            # (for approve and transfer)
            return True

        return self.binding_context.matches(chain_id, address)

    async def parse_calldata(
        self,
        calldata: memoryview,
        msg: MsgInSignTx,
        defs: Definitions,
    ) -> tuple[
        list[AnyValue],
        list[tuple[StrPropertyType, EthereumTokenInfo | None, AnyBytes | None]],
    ]:
        parameters: list[AnyValue] = []

        offset = 0
        for parameter_definition in self.parameter_definitions:
            value, consumed = parameter_definition.parse(calldata, offset)
            parameters.append(value)
            offset += consumed

        def get_value_for_path(path: Path) -> Value:
            if isinstance(path, int):  # ContainerPath
                # standard container paths like @.from, @.value...
                if path == ContainerPath.From:
                    account, _ = get_account_and_path(msg.address_n)
                    return account
                elif path == ContainerPath.Value:
                    return int.from_bytes(msg.value, "big")
                elif path == ContainerPath.To:
                    return bytes_from_address(msg.to)
                else:
                    raise NotImplementedError  # TODO
            else:
                if len(path) == 0:
                    # can't get anywhere by walking an inexisting path!
                    raise InvalidFormatDefinition

                # walk the path
                p = parameters
                for step in path:
                    if p is None:
                        p = None
                        break
                    if isinstance(p, (list, tuple, bytes)):
                        # walk inside Arrays or Tuples
                        try:
                            if isinstance(step, int):
                                p = p[step]
                            elif isinstance(step, tuple) and len(step) in (1, 2):
                                # steps encoded as tuples represent slices... [a:b] or [a:]
                                if len(step) == 1:
                                    p = p[step[0] :]
                                else:
                                    p = p[step[0] : step[1]]
                            else:
                                raise InvalidFormatDefinition
                        except (IndexError, TypeError):
                            raise InvalidFormatDefinition
                    else:
                        # can't walk inside basic types
                        raise InvalidFormatDefinition
                if isinstance(p, (list, tuple)):
                    # at the end of the path, we must have arrived somewhere
                    # ie. not on an Array or Tuple
                    raise InvalidFormatDefinition
                return p

        fields: list[
            tuple[StrPropertyType, EthereumTokenInfo | None, AnyBytes | None]
        ] = []
        for field_definition in self.field_definitions:
            value = get_value_for_path(field_definition.path)
            formatter = field_definition.get_formatter()

            formatted, token, token_address = await formatter.format(
                value, msg, defs, get_value_for_path
            )

            fields.append(
                (
                    (field_definition.label, formatted, None),
                    token,
                    token_address,
                )
            )

        return parameters, fields

    @classmethod
    def from_encoded(cls, encoded: AnyBytes) -> Self:
        from trezor.messages import EthereumDisplayFormatInfo

        from apps.common.definitions import decode_definition

        proto = decode_definition(encoded, EthereumDisplayFormatInfo)

        return cls(
            binding_context=BindingContext([(proto.chain_id, bytes(proto.address))]),
            func_sig=bytes(proto.func_sig),
            intent=proto.intent,
            parameter_definitions=[
                ABIValue.from_proto(p) for p in proto.parameter_definitions
            ],
            field_definitions=[
                FieldDefinition.from_proto(f) for f in proto.field_definitions
            ],
        )


async def _request_definitions(
    chain_id: int, token_address: bytes, func_sig: bytes | None
) -> tuple[Definitions | None, DisplayFormat | None]:
    from trezor.messages import EthereumDefinitionAck, EthereumDefinitionRequest
    from trezor.wire.context import call

    req = EthereumDefinitionRequest(
        chain_id=chain_id,
        token_address=token_address,
        func_sig=func_sig,
    )
    res = await call(req, EthereumDefinitionAck)

    if res.definitions is None:
        return None, None

    definitions = Definitions.from_encoded(
        res.definitions.encoded_network, res.definitions.encoded_token, chain_id
    )

    display_format = (
        DisplayFormat.from_encoded(res.definitions.encoded_display_format)
        if res.definitions.encoded_display_format is not None
        else None
    )

    return definitions, display_format


async def try_confirm(
    data: AnyBytes,
    address_bytes: bytes,
    msg: MsgInSignTx,
    defs: Definitions,
    maximum_fee: str,
    fee_items: Iterable[StrPropertyType],
    payment_request_verifier: PaymentRequestVerifier | None,
) -> bool:
    from .clear_signing_definitions import (
        ALL_DISPLAY_FORMATS,
        APPROVE_DISPLAY_FORMAT,
        TRANSFER_DISPLAY_FORMAT,
    )

    if not address_bytes:
        return False

    if len(data) < SC_FUNC_SIG_BYTES:
        return False

    func_sig = bytes(data[0:SC_FUNC_SIG_BYTES])

    display_format = None
    for f in ALL_DISPLAY_FORMATS:
        # Start by trying built-in definitions...
        if f.func_sig == func_sig and f.matches_context(msg.chain_id, address_bytes):
            display_format = f
            break
    else:
        if msg.definitions and msg.definitions.encoded_display_format:
            # ... look at definitions provided in the initial request...
            f = DisplayFormat.from_encoded(msg.definitions.encoded_display_format)
            if f.func_sig == func_sig and f.matches_context(
                msg.chain_id, address_bytes
            ):
                display_format = f
        if display_format is None:
            # ... finally request the display format via another call!
            if msg.supports_definition_request:
                _, f = await _request_definitions(msg.chain_id, address_bytes, func_sig)
                if f:
                    if f.func_sig == func_sig and f.matches_context(
                        msg.chain_id, address_bytes
                    ):
                        display_format = f

    if display_format is None:
        return False

    calldata = memoryview(data)[SC_FUNC_SIG_BYTES:]

    # custom treatment of certain functions (APPROVE, TRANSFER)
    if display_format.func_sig == APPROVE_DISPLAY_FORMAT.func_sig:
        await _handle_approve(
            calldata,
            display_format,
            address_bytes,
            msg,
            defs,
            maximum_fee,
            fee_items,
        )
    elif display_format.func_sig == TRANSFER_DISPLAY_FORMAT.func_sig:
        await _handle_transfer(
            calldata,
            display_format,
            address_bytes,
            msg,
            defs,
            maximum_fee,
            fee_items,
            payment_request_verifier,
        )
    else:
        # generic UI for any function that has a `DisplayFormat`
        await _handle_generic_ui(
            calldata,
            display_format,
            msg,
            defs,
            maximum_fee,
        )
    return True


async def _handle_approve(
    calldata: memoryview,
    display_format: DisplayFormat,
    address_bytes: bytes,
    msg: MsgInSignTx,
    defs: Definitions,
    maximum_fee: str,
    fee_items: Iterable[StrPropertyType],
) -> None:
    from .clear_signing_definitions import SC_FUNC_APPROVE_REVOKE_AMOUNT
    from .layout import require_confirm_approve
    from .sc_constants import KNOWN_ADDRESSES
    from .yielding_vaults import UNKNOWN_VAULT, lookup_vault

    args, fields = await display_format.parse_calldata(calldata, msg, defs)

    assert len(args) == 2
    assert len(fields) == 2

    arg0_raw_value = args[0]
    (field0_name, recipient_addr, _), _, _ = fields[0]
    assert field0_name == "Spender"
    assert isinstance(arg0_raw_value, bytes)
    assert isinstance(recipient_addr, str)

    arg1_raw_value = args[1]
    (field1_name, value, _), actual_token, _ = fields[1]
    assert field1_name == "Amount"
    assert isinstance(arg1_raw_value, int)

    recipient_str = KNOWN_ADDRESSES.get(arg0_raw_value)
    if recipient_str is None:
        vault = lookup_vault(defs.network, arg0_raw_value)
        if vault is not UNKNOWN_VAULT:
            recipient_str = vault.name

    is_revoke = arg1_raw_value == SC_FUNC_APPROVE_REVOKE_AMOUNT

    await require_confirm_approve(
        recipient_addr,
        value,
        recipient_str,
        msg.address_n,
        maximum_fee,
        fee_items,
        msg.chain_id,
        defs.network,
        actual_token or defs.get_token(address_bytes),
        address_bytes,
        is_revoke,
        bool(msg.chunkify),
    )


async def _handle_transfer(
    calldata: memoryview,
    display_format: DisplayFormat,
    address_bytes: bytes,
    msg: MsgInSignTx,
    defs: Definitions,
    maximum_fee: str,
    fee_items: Iterable[StrPropertyType],
    payment_request_verifier: PaymentRequestVerifier | None,
) -> None:
    from .layout import require_confirm_payment_request, require_confirm_tx

    args, fields = await display_format.parse_calldata(calldata, msg, defs)

    assert len(args) == 2
    assert len(fields) == 2

    (arg0_name, recipient_addr, _), _, _ = fields[0]
    assert arg0_name == "To"
    assert isinstance(recipient_addr, str)

    arg1_raw_value = args[1]
    assert isinstance(arg1_raw_value, int)
    (arg1_name, value, _), actual_token, _ = fields[1]
    assert arg1_name == "Amount"
    assert isinstance(value, str)

    if payment_request_verifier:
        # SLIP-24 payment requests for ERC-20 token transfers

        assert msg.payment_req is not None

        payment_request_verifier.add_output(arg1_raw_value, recipient_addr)
        payment_request_verifier.verify()
        await require_confirm_payment_request(
            recipient_addr,
            msg.payment_req,
            msg.address_n,
            maximum_fee,
            fee_items,
            msg.chain_id,
            defs.network,
            actual_token or defs.get_token(address_bytes),
            address_from_bytes(address_bytes, defs.network),
        )
    else:
        await require_confirm_tx(
            recipient_addr,
            value,
            address_bytes,
            msg.address_n,
            maximum_fee,
            fee_items,
            actual_token or defs.get_token(address_bytes),
            is_send=True,
            chunkify=bool(msg.chunkify),
        )


async def _handle_generic_ui(
    calldata: memoryview,
    display_format: DisplayFormat,
    msg: MsgInSignTx,
    defs: Definitions,
    maximum_fee: str,
) -> None:
    from . import tokens
    from .helpers import bytes_from_address
    from .layout import require_confirm_clear_signing
    from .sc_constants import KNOWN_ADDRESSES

    _, fields = await display_format.parse_calldata(calldata, msg, defs)

    properties_to_confirm = []

    for field, actual_token, actual_token_address in fields:
        properties_to_confirm.append(field)
        if actual_token is tokens.UNKNOWN_TOKEN:
            assert actual_token_address is not None
            token_address_str = address_from_bytes(actual_token_address, defs.network)
            token_address_property: StrPropertyType = (
                TR.ethereum__token_contract,
                token_address_str,
                None,
            )
            properties_to_confirm.append(token_address_property)

    recipient_str = KNOWN_ADDRESSES.get(bytes_from_address(msg.to), msg.to)

    await require_confirm_clear_signing(
        recipient_str, display_format.intent, properties_to_confirm, maximum_fee
    )
