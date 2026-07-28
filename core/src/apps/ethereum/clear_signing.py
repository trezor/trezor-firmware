from micropython import const
from typing import TYPE_CHECKING

from trezor import TR
from trezor.wire import DataError

from .definitions import Definitions
from .helpers import (
    address_from_bytes,
    bytes_from_address,
    format_ethereum_amount,
    get_account_and_path,
)

if TYPE_CHECKING:
    from buffer_types import AnyBytes
    from typing import Callable, Iterable, Sequence

    from trezor.messages import (
        EthereumABIValueInfo,
        EthereumERC7730FieldInfo,
        EthereumTokenInfo,
    )
    from trezor.ui.layouts import StrPropertyType
    from trezor.ui.layouts.properties import AboveThreshold
    from typing_extensions import Self

    from apps.common.payment_request import PaymentRequestVerifier

    from .keychain import MsgInSignTx

    # Represents values that have been parsed from the calldata
    # into our internal representation.
    # TODO: Revisit simplifying this.
    Value = int | bytes | bool | str | None | list["Value"]
    TupleValue = tuple[Value, ...]
    ListValue = list[TupleValue]
    AnyValue = Value | TupleValue | list["AnyValue"]

    # A data path (tuple of steps), a container path (int enum), or a literal
    # constant value (str, resolved by the parser — not walked from calldata).
    Path = tuple[int | tuple[int] | tuple[int, int], ...] | int | str
    PathWalker = Callable[[Path], AnyValue]

    # Parses a Value from a slice of the calldata.
    # Assumes that the memoryview contains just that value.
    Parser = Callable[[memoryview], Value]

    # One displayed row: ((label, formatted value, is_mono), token, token_address)
    DisplayedField = tuple[
        tuple[str, str | AboveThreshold | None, bool | None],
        EthereumTokenInfo | None,
        AnyBytes | None,
    ]


SC_FUNC_SIG_BYTES = const(4)
_EVM_WORD_SIZE = const(32)  # in bytes
_EVM_WORD_BITS = const(8 * _EVM_WORD_SIZE)
_ADDRESS_BYTES = const(20)


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


def _check_padding_zero(
    raw_data: memoryview, used_bytes: int, exc: type[ValueOverflow] = ValueOverflow
) -> None:
    """Sanity check to make sure unused data is zeroed out."""
    if not 0 <= used_bytes <= _EVM_WORD_SIZE:
        raise InvalidFormatDefinition
    if any(raw_data[: _EVM_WORD_SIZE - used_bytes]):
        raise exc


def parse_address(raw_data: memoryview) -> Value:
    if len(raw_data) < _EVM_WORD_SIZE:
        raise OutOfBounds
    _check_padding_zero(raw_data, _ADDRESS_BYTES, DirtyAddress)
    return bytes(raw_data[_EVM_WORD_SIZE - _ADDRESS_BYTES :])


def parse_uint256(raw_data: memoryview) -> int:
    if len(raw_data) < _EVM_WORD_SIZE:
        raise OutOfBounds
    return int.from_bytes(raw_data, "big")


def make_uint_parser(bit_width: int) -> "Parser":
    byte_width = bit_width // 8

    def parser(raw_data: memoryview) -> Value:
        if len(raw_data) < _EVM_WORD_SIZE:
            raise OutOfBounds
        _check_padding_zero(raw_data, byte_width)
        return parse_uint256(raw_data)

    return parser


def make_fixed_bytes_parser(byte_width: int) -> "Parser":
    """bytesN values are left-aligned in the word: the padding to check
    for zeroes is on the right, unlike the numeric types.
    See "bytes<M>: enc(X) is the sequence of bytes in X padded with
    trailing zero-bytes to a length of 32 bytes" in
    https://docs.soliditylang.org/en/latest/abi-spec.html#formal-specification-of-the-encoding
    """

    def parser(raw_data: memoryview) -> Value:
        if len(raw_data) < _EVM_WORD_SIZE:
            raise OutOfBounds
        if any(raw_data[byte_width:_EVM_WORD_SIZE]):
            raise ValueOverflow
        return bytes(raw_data[:byte_width])

    return parser


def make_int_parser(bit_width: int) -> Parser:
    if not 0 < bit_width <= _EVM_WORD_BITS:
        raise InvalidFormatDefinition

    def parser(raw_data: memoryview) -> Value:
        value = parse_uint256(raw_data)
        # Two's complement.
        if value >= 1 << (_EVM_WORD_BITS - 1):
            value -= 1 << _EVM_WORD_BITS
        # the range check doubles as the sign-extension padding check
        if not -(1 << (bit_width - 1)) <= value < 1 << (bit_width - 1):
            raise ValueOverflow
        return value

    return parser


def _word_bytes(value: AnyValue) -> AnyValue:
    """An EVM word can be viewed as an integer or as 32 bytes. A byte-slice
    step selects the bytes view: e.g. `token.[-20:]` reads the low 20 bytes
    of a uint256 (the 1inch packed `Address` type). Non-numeric values are
    returned unchanged - they are sliced directly."""
    if type(value) is int:  # not isinstance: bool is an int subclass
        if value < 0:
            # byte-slicing a signed value has no defined meaning
            raise InvalidFormatDefinition
        return value.to_bytes(_EVM_WORD_SIZE, "big")
    return value


def parse_bool(raw_data: memoryview) -> Value:
    if len(raw_data) < _EVM_WORD_SIZE:
        raise OutOfBounds
    uint_value = parse_uint256(raw_data)
    if uint_value not in (0, 1):
        raise ValueOverflow
    return uint_value == 1


def parse_bytes(raw_data: memoryview) -> Value:
    return bytes(raw_data)


def parse_string(raw_data: memoryview) -> Value:
    return bytes(raw_data).decode("utf-8")


DYNAMIC_DATA_PARSERS = [parse_bytes, parse_string]


def _get_parser(t: int, is_dynamic: bool) -> Parser:
    """Get a parser for a type we received over the wire protocol.
    `is_dynamic` selects whether the type is being used in a dynamic
    (variable-length) or atomic (32-byte) context, and must match the type."""
    from trezor.enums import EthereumABIType as T

    if is_dynamic:
        if t == T.ABI_BYTES:
            return parse_bytes
        elif t == T.ABI_STRING:
            return parse_string
        raise InvalidFormatDefinition

    if t == T.ABI_ADDRESS:
        return parse_address
    elif t == T.ABI_UINT256:
        return parse_uint256
    elif t == T.ABI_UINT248:
        return make_uint_parser(248)
    elif t == T.ABI_UINT160:
        return make_uint_parser(160)
    elif t == T.ABI_UINT128:
        return make_uint_parser(128)
    elif t == T.ABI_UINT120:
        return make_uint_parser(120)
    elif t == T.ABI_UINT112:
        return make_uint_parser(112)
    elif t == T.ABI_UINT96:
        return make_uint_parser(96)
    elif t == T.ABI_UINT72:
        return make_uint_parser(72)
    elif t == T.ABI_UINT64:
        return make_uint_parser(64)
    elif t == T.ABI_UINT48:
        return make_uint_parser(48)
    elif t == T.ABI_UINT40:
        return make_uint_parser(40)
    elif t == T.ABI_UINT32:
        return make_uint_parser(32)
    elif t == T.ABI_UINT24:
        return make_uint_parser(24)
    elif t == T.ABI_UINT16:
        return make_uint_parser(16)
    elif t == T.ABI_UINT8:
        return make_uint_parser(8)
    elif t == T.ABI_BOOL:
        return parse_bool
    elif t == T.ABI_INT160:
        return make_int_parser(160)
    elif t == T.ABI_BYTES32:
        return make_fixed_bytes_parser(32)
    elif t == T.ABI_BYTES20:
        return make_fixed_bytes_parser(20)
    elif t == T.ABI_BYTES16:
        return make_fixed_bytes_parser(16)
    elif t == T.ABI_BYTES8:
        return make_fixed_bytes_parser(8)
    elif t == T.ABI_BYTES4:
        return make_fixed_bytes_parser(4)
    raise InvalidFormatDefinition


def _get_leaf_parser(info: EthereumABIValueInfo) -> Parser:
    """Get a parser for a leaf (atomic or dynamic) value. Raises for nested structures."""
    if info.atomic is not None:
        return _get_parser(info.atomic, is_dynamic=False)
    elif info.dynamic is not None:
        return _get_parser(info.dynamic, is_dynamic=True)
    raise InvalidFormatDefinition


# Field formatters: https://eips.ethereum.org/EIPS/eip-7730#field-formats


class FieldFormatter:
    async def format(
        self,
        value: AnyValue,
        msg: MsgInSignTx,
        defs: Definitions,
        path_walker: PathWalker,
    ) -> tuple[str | AboveThreshold | None, EthereumTokenInfo | None, AnyBytes | None]:
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
    ) -> tuple[str | AboveThreshold | None, EthereumTokenInfo | None, AnyBytes | None]:
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
    ) -> tuple[str | AboveThreshold | None, EthereumTokenInfo | None, AnyBytes | None]:
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
    def __init__(
        self,
        token_path: Path | None = None,
        const_token_address: bytes | None = None,
        native_currency_address: list[bytes] | None = None,
        threshold: int | None = None,
    ) -> None:
        self.token_path = token_path
        self.const_token_address = const_token_address
        self.native_currency_address = native_currency_address
        self.threshold = threshold

    async def format(
        self,
        amount: AnyValue,
        msg: MsgInSignTx,
        defs: Definitions,
        path_walker: PathWalker,
    ) -> tuple[str | AboveThreshold | None, EthereumTokenInfo | None, AnyBytes | None]:
        from trezor.ui.layouts.properties import AboveThreshold

        from .tokens import UNKNOWN_TOKEN

        if amount is None:
            return None, None, None

        if not isinstance(amount, int):
            raise InvalidFormatDefinition

        if self.const_token_address is not None:
            # token given as a literal constant address
            token_address = self.const_token_address
        elif self.token_path is not None:
            walked = path_walker(self.token_path)
            if not isinstance(walked, bytes):
                raise InvalidFormatDefinition
            token_address = walked
        else:
            raise InvalidFormatDefinition

        if self.native_currency_address is not None:
            if token_address in self.native_currency_address:
                if self.threshold is not None and amount > self.threshold:
                    return AboveThreshold(TR.words__unlimited), None, None
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
                received_definitions, _ = await request_definitions(
                    msg.chain_id, token_address, func_sig=None
                )
                if received_definitions is not None:
                    token = received_definitions.get_token(token_address)

        if self.threshold is not None and amount > self.threshold:
            return AboveThreshold(TR.words__unlimited), token, token_address
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
    ) -> tuple[str | AboveThreshold | None, EthereumTokenInfo | None, AnyBytes | None]:
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


class RawFormatter(FieldFormatter):
    """Lazy placeholder. Simply adds label to the value and show it essentially as-is.
    ERC-7730 `raw` format: display the decoded value with no transformation,
    rendering by its Solidity type per the spec:
      * int    -> decimal string (natural representation)
      * string -> the UTF-8 string as-is
      * bytes  -> hex-encoded string
    """

    async def format(
        self,
        value: AnyValue,
        _msg: MsgInSignTx,
        _definitions: Definitions,
        _path_walker: PathWalker,
    ) -> tuple[str | AboveThreshold | None, EthereumTokenInfo | None, AnyBytes | None]:
        if value is None:
            return None, None, None
        elif isinstance(value, str):
            return value, None, None
        elif isinstance(value, (bytes, bytearray)):
            from ubinascii import hexlify

            return hexlify(value).decode(), None, None
        elif isinstance(value, bool):
            return str(value), None, None
        elif isinstance(value, int):
            return str(value), None, None
        else:
            raise InvalidFormatDefinition


class DateFormatter(FieldFormatter):
    """ERC-7730 `date` format with `encoding: timestamp` (the only encoding used
    by the supported definitions). Renders a unix timestamp (seconds) as a
    human-readable date."""

    async def format(
        self,
        value: AnyValue,
        _msg: MsgInSignTx,
        _definitions: Definitions,
        _path_walker: PathWalker,
    ) -> tuple[str | AboveThreshold | None, EthereumTokenInfo | None, AnyBytes | None]:
        from trezor.strings import format_timestamp

        if value is None:
            return None, None, None
        if isinstance(value, (bytes, bytearray)):
            # a sliced word, e.g. `goodUntil.[-4:]`: big-endian seconds
            value = int.from_bytes(value, "big")
        if isinstance(value, int):
            return format_timestamp(value), None, None
        raise InvalidFormatDefinition


class CalldataFormatter(RawFormatter):
    """ERC-7730 `calldata` format: the field's value is the embedded calldata
    of a nested call, rendered with the display format of the called contract
    (resolved from `callee_path`). Unlike every other formatter it expands
    into multiple display rows, so `DisplayFormat.parse_calldata` handles it
    directly (see `_expand_calldata_field`) instead of going through the
    single-value `format` interface. Subclassing `RawFormatter` is defense
    in depth: should a code path ever fail to special-case this formatter,
    the inherited `format` renders the blob as raw hex instead of failing
    clear signing."""

    def __init__(self, callee_path: Path, selector: bytes | None = None) -> None:
        self.callee_path = callee_path
        self.selector = selector
class EnumFormatter(FieldFormatter):
    """ERC-7730 `enum` format: the value read from calldata is a key into a
    descriptor-supplied mapping and is displayed as the mapped string."""

    def __init__(self, entries: dict[int, str]) -> None:
        self.entries = entries

    async def format(
        self,
        value: AnyValue,
        _msg: MsgInSignTx,
        _definitions: Definitions,
        _path_walker: PathWalker,
    ) -> tuple[str | AboveThreshold | None, EthereumTokenInfo | None, AnyBytes | None]:
        if value is None:
            return None, None, None
        if isinstance(value, (bytes, bytearray)):
            # byte sliced to be read as an int
            value = int.from_bytes(value, "big")
        if type(value) is not int:
            raise InvalidFormatDefinition
        formatted = self.entries.get(value)
        if formatted is None:
            raise InvalidFormatDefinition
        return formatted, None, None


async def _format_field_value(
    formatter: FieldFormatter,
    value: AnyValue,
    msg: MsgInSignTx,
    defs: Definitions,
    path_walker: PathWalker,
) -> tuple[str | AboveThreshold | None, EthereumTokenInfo | None, AnyBytes | None]:
    """Format a field value.

    When the field's path resolves to an array (a `list`), the formatter is
    applied to each element and the rendered values are joined with newlines,
    so the field is shown as one value per line - eg. an `amount.[]` field over
    `[1, 2]` renders as "1 token\n2 token". This works for any formatter pointed
    at an array (amount, address, raw, ...). A non-list value is formatted
    directly.

    Only flat arrays of formattable leaves are handled."""
    if not isinstance(value, list):
        return await formatter.format(value, msg, defs, path_walker)

    from trezor.ui.layouts.properties import AboveThreshold

    lines: list[str] = []
    # The same formatter instance is reused for every element, so a
    # `tokenAmount`'s single `token_path` resolves to the same token on each
    # iteration: the token is shared across the array and returned once.
    token: EthereumTokenInfo | None = None
    token_address: AnyBytes | None = None
    for element in value:
        formatted, element_token, element_address = await formatter.format(
            element, msg, defs, path_walker
        )
        if isinstance(formatted, AboveThreshold):
            formatted = formatted.message
        if formatted is None:
            # Raise if any member returns None.
            raise InvalidFormatDefinition
        lines.append(formatted)
        if element_token is not None:
            token = element_token
        if element_address is not None:
            token_address = element_address
    return "\n".join(lines), token, token_address


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
    """A node of an ABI type tree, able to parse its value from raw calldata.

    Encoding reference: the Solidity ABI specification,
    https://docs.soliditylang.org/en/latest/abi-spec.html#formal-specification-of-the-encoding

    Per the spec, every type is either static or dynamic (`is_dynamic`):

    * a static value is encoded in place, occupying `head_size` bytes;
    * a dynamic value's head is a single word holding the offset of its
      body, relative to the start of the enclosing block.

    `parse` implements this head rule once for all types; subclasses only
    describe what their body looks like by implementing `parse_body`.
    """

    is_dynamic = False
    head_size = _EVM_WORD_SIZE

    def parse(
        self, raw_data: memoryview, offset: int, block_start: int = 0
    ) -> tuple[AnyValue, int]:
        """Parse one value whose head is at `offset`.

        `block_start` is where the enclosing block starts; offsets inside
        heads are relative to it. Relevant for arrays, etc.
        Returns the parsed value and the head bytes consumed.
        """
        if offset + self.head_size > len(raw_data):
            raise OutOfBounds
        if self.is_dynamic:
            # the head of any dynamic type is one word: the offset of its body
            # Dynamic types must have a parse_body method.
            pointer = int.from_bytes(raw_data[offset : offset + _EVM_WORD_SIZE], "big")
            return self.parse_body(raw_data, block_start + pointer), self.head_size
        return self.parse_body(raw_data, offset), self.head_size

    def parse_body(self, raw_data: memoryview, pos: int) -> AnyValue:
        """Parse the value body located directly at `pos` (no indirection)."""
        raise NotImplementedError

    @staticmethod
    def from_proto(info: EthereumABIValueInfo) -> "ABIValue":
        if info.atomic is not None:
            return Atomic(_get_parser(info.atomic, is_dynamic=False))
        elif info.dynamic is not None:
            return DynamicLeaf(_get_parser(info.dynamic, is_dynamic=True))
        elif info.tuple is not None:
            return Tuple(
                tuple(_get_leaf_parser(f) for f in info.tuple.fields),
                info.tuple.is_dynamic,
            )
        elif info.array is not None:
            element = info.array
            if element.atomic is not None:
                return Array(Atomic(_get_parser(element.atomic, is_dynamic=False)))
            elif element.dynamic is not None:
                return Array(DynamicLeaf(_get_parser(element.dynamic, is_dynamic=True)))
            elif element.tuple is not None:
                fields = tuple(_get_leaf_parser(f) for f in element.tuple.fields)
                # A non-array (leaf) struct/tuple is dynamic if any of its fields is dynamic.
                # E.g. of dynamic members: bytes, string, uint256[], bytes[], bytes[][] etc.
                # An array (this outer structure) is always* dynamic regardless of its fields.
                # (*Unless it's of fixed length, which generally don't exist.)
                return Array(
                    Tuple(
                        fields,
                        is_dynamic=any(p in DYNAMIC_DATA_PARSERS for p in fields),
                    )
                )
            elif element.array is not None:
                inner = element.array
                if inner.atomic is not None:
                    return Array(
                        Array(Atomic(_get_parser(inner.atomic, is_dynamic=False)))
                    )
                elif inner.dynamic is not None:
                    return Array(
                        Array(DynamicLeaf(_get_parser(inner.dynamic, is_dynamic=True)))
                    )
                raise InvalidFormatDefinition  # deeper nesting not supported
            raise InvalidFormatDefinition
        raise InvalidFormatDefinition


class Atomic(ABIValue):
    """Atomic values, such as integers or addresses, are static types
    always stored on one EVM word."""

    def __init__(self, parser: Parser) -> None:
        self.parser = parser

    def parse_body(self, raw_data: memoryview, pos: int) -> AnyValue:
        # bounds already ensured by `parse`: pos + head_size <= len(raw_data)
        return self.parser(raw_data[pos : pos + _EVM_WORD_SIZE])


def _read_dynamic_data(raw_data: memoryview, pointer: int) -> memoryview:
    """Read a variable-length blob located at `pointer` in `raw_data`,
    encoded as a one-word length prefix followed by `length` bytes of data."""
    if pointer + _EVM_WORD_SIZE > len(raw_data):
        raise OutOfBounds
    length = int.from_bytes(raw_data[pointer : pointer + _EVM_WORD_SIZE], "big")
    body_start = pointer + _EVM_WORD_SIZE
    if body_start + length > len(raw_data):
        raise OutOfBounds
    return raw_data[body_start : body_start + length]


class DynamicLeaf(ABIValue):
    """`strings` or `bytes`. Their body is a
    one-word byte length followed by that many bytes of data."""

    is_dynamic = True

    def __init__(self, parser: Parser) -> None:
        self.parser = parser

    def parse_body(self, raw_data: memoryview, pos: int) -> AnyValue:
        return self.parser(_read_dynamic_data(raw_data, pos))


class Tuple(ABIValue):
    """Tuples (or Structs - the same thing as far as the ABI is concerned)
    contain multiple values of possibly different types. Only leaf fields
    (atomic types, `bytes`, `string`) are supported here i.e. no more nesting; the dynamic
    fields are the ones whose parser is in DYNAMIC_DATA_PARSERS.

    A tuple is a dynamic type iff at least one of its fields is dynamic.
    Its body is the concatenation of its fields' heads: a static field is
    encoded in place, while a dynamic field's head is the offset of its
    length-prefixed data, relative to the body start. A static tuple is
    therefore just its field values back to back - no length prefix and no
    offset words anywhere."""

    def __init__(self, fields: tuple[Parser, ...], is_dynamic: bool) -> None:
        if not fields:
            # Zero-field structs do not exist in Solidity. Rejecting them here
            # also guarantees head_size >= _EVM_WORD_SIZE for every type: a
            # static tuple with head_size == 0 inside an Array would defeat
            # the heads bounds pre-check (array_length * 0) and let an
            # attacker-controlled length word drive an unbounded parse loop.
            raise InvalidFormatDefinition
        self.fields = fields
        self.is_dynamic = is_dynamic
        self.fields_size = len(fields) * _EVM_WORD_SIZE
        if not is_dynamic:
            # a static tuple is encoded in place, so its head is its whole body
            self.head_size = self.fields_size

    def parse_body(self, raw_data: memoryview, pos: int) -> AnyValue:
        if pos + self.fields_size > len(raw_data):
            raise OutOfBounds

        value: list[Value] = [None] * len(self.fields)

        for i, parser in enumerate(self.fields):
            field_head_pos = pos + (i * _EVM_WORD_SIZE)
            raw_field = raw_data[field_head_pos : field_head_pos + _EVM_WORD_SIZE]
            if parser not in DYNAMIC_DATA_PARSERS:
                value[i] = parser(raw_field)
            else:
                field_pointer = pos + int.from_bytes(raw_field, "big")
                value[i] = parser(_read_dynamic_data(raw_data, field_pointer))
        return tuple(value)


class Array(ABIValue):
    """Arrays (`T[]`) are sequences of values of the same type, and are
    always dynamic types themselves. The body is a one-word element count
    followed by the elements' heads - in place values for static element
    types (e.g. `uint256[]`, or an array of static structs, laid out at a
    stride of the element's `head_size`), or one-word body offsets for
    dynamic element types (e.g. `bytes[]`, `uint256[][]`, or an array of
    structs containing a dynamic field)."""

    is_dynamic = True

    def __init__(self, element_definition: ABIValue) -> None:
        self.element_definition = element_definition

    def parse_body(self, raw_data: memoryview, pos: int) -> AnyValue:
        if pos + _EVM_WORD_SIZE > len(raw_data):
            raise OutOfBounds
        array_length = int.from_bytes(raw_data[pos : pos + _EVM_WORD_SIZE], "big")
        element = self.element_definition
        # element heads are laid out right after the length word, and any
        # offsets among them are relative to this position
        elements_start = pos + _EVM_WORD_SIZE
        if elements_start + (array_length * element.head_size) > len(raw_data):
            raise OutOfBounds

        value = []
        element_head_offset = elements_start
        for _ in range(array_length):
            data, consumed = element.parse(
                raw_data, element_head_offset, elements_start
            )
            value.append(data)
            element_head_offset += consumed
        return value


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
            if p.const_value is not None:
                # A literal constant value, resolved by the parser — not walked
                # from calldata. Rendered as-is (typically by the raw formatter).
                return p.const_value
            steps: list[int | tuple[int] | tuple[int, int]] = list(p.path)
            if p.slice_end is not None:
                # `data.[0:20]` or `takerTraits.[:1]` (start defaults to 0)
                steps.append((p.slice_start or 0, p.slice_end))
            elif p.slice_start is not None:
                steps.append((p.slice_start,))  # `token.[-20:]`
            return tuple(steps)

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
            if info.const_token_address is not None:
                formatter_params["const_token_address"] = bytes(
                    info.const_token_address
                )
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
        elif fmt_type == FT.FORMATTER_RAW:
            formatter = RawFormatter
        elif fmt_type == FT.FORMATTER_DATE:
            formatter = DateFormatter
        elif fmt_type == FT.FORMATTER_CALLDATA:
            if info.callee_path is None:
                raise InvalidFormatDefinition
            selector = bytes(info.selector) if info.selector is not None else None
            if selector is not None and len(selector) != SC_FUNC_SIG_BYTES:
                raise InvalidFormatDefinition
            formatter = CalldataFormatter(decode_path(info.callee_path), selector)
        elif fmt_type == FT.FORMATTER_ENUM:
            if not info.enum_values:
                raise InvalidFormatDefinition
            enum_entries: dict[int, str] = {}
            for e in info.enum_values:
                if e.key in enum_entries:
                    raise InvalidFormatDefinition
                enum_entries[e.key] = e.value
            formatter = EnumFormatter(enum_entries)
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
        provider_name: str | None = None,
    ) -> None:
        self.binding_context = binding_context
        self.func_sig = func_sig
        self.intent = intent
        self.parameter_definitions = parameter_definitions
        self.field_definitions = field_definitions
        self.provider_name = provider_name

        self.parameters = []

    def matches_context(self, chain_id: int, address: bytes) -> bool:
        if self.binding_context is None:
            # applies to anything without context verification
            # (for approve and transfer)
            return True

        return self.binding_context.matches(chain_id, address)

    def matches_call(self, func_sig: bytes, chain_id: int, address: bytes) -> bool:
        """Assert the received descriptor is what was requested"""
        return self.func_sig == func_sig and self.matches_context(chain_id, address)

    async def parse_calldata(
        self,
        calldata: memoryview,
        msg: MsgInSignTx,
        defs: Definitions,
        nested: bool = False,
        override_callee: bytes | None = None,
    ) -> tuple[list[AnyValue], list[DisplayedField]]:
        """Parse `calldata` (without the selector) and format the display fields.

        `nested` marks the parse of an embedded subcall's calldata (see
        `_expand_calldata_field`): container paths other than `@.to` are
        unresolvable there, and any further calldata fields render as raw
        hex instead of triggering tertiary lookups. `override_callee` substitutes
        the `@.to` container path (the subcall's callee, not the outer
        transaction's recipient)."""
        parameters: list[AnyValue] = []

        offset = 0
        for parameter_definition in self.parameter_definitions:
            try:
                value, consumed = parameter_definition.parse(calldata, offset)
            except Exception as e:
                if __debug__:
                    from trezor import log

                    log.debug(
                        __name__,
                        "clear signing: failed to parse calldata parameters (%s)",
                        type(e).__name__,
                    )
                raise
            parameters.append(value)
            offset += consumed

        def get_value_for_path(path: Path) -> AnyValue:
            if isinstance(path, str):
                # a literal constant value, not walked from calldata
                return path
            if isinstance(path, int):  # ContainerPath
                # standard container paths like @.from, @.value...
                if path == ContainerPath.To:
                    # `@.to` means "the contract this call goes to". For the
                    # outer transaction that is `msg.to`. When parsing a
                    # subcall, the wrapper (`msg.to`) merely forwards the
                    # call: `override_callee` holds the actual callee, so e.g. a
                    # nested transfer's `token_path=@.to` resolves to the
                    # token contract, not to the wrapper.
                    if override_callee is not None:
                        return override_callee
                    return bytes_from_address(msg.to)
                if nested:
                    # In a subcall, `@.from` is ambiguous - the wrapper
                    # contract if it CALLs the callee, the original signer if
                    # it DELEGATECALLs - and `@.value` is decided by wrapper
                    # logic; neither can be resolved from `msg` without
                    # risking a confidently wrong display.
                    raise InvalidFormatDefinition
                if path == ContainerPath.From:
                    account, _ = get_account_and_path(msg.address_n)
                    return account
                elif path == ContainerPath.Value:
                    return int.from_bytes(msg.value, "big")
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
                    if isinstance(step, tuple):
                        # slices view numeric values as bytes (see _word_bytes)
                        p = _word_bytes(p)
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
                if isinstance(p, tuple):
                    # Array/list makes sense. Not expecting tuples here.
                    raise InvalidFormatDefinition
                return p

        fields: list[DisplayedField] = []
        for field_definition in self.field_definitions:
            try:
                formatter = field_definition.get_formatter()
                if isinstance(formatter, CalldataFormatter):
                    # Expands into multiple rows (the subcall's provider and
                    # intent, then its own fields), so it bypasses the
                    # single-value formatting below.
                    fields.extend(
                        await _expand_calldata_field(
                            field_definition,
                            formatter,
                            get_value_for_path,
                            msg,
                            defs,
                            nested,
                        )
                    )
                    continue
                value = get_value_for_path(field_definition.path)
                formatted, token, token_address = await _format_field_value(
                    formatter, value, msg, defs, get_value_for_path
                )
            except Exception as e:
                if __debug__:
                    from trezor import log

                    log.debug(
                        __name__,
                        'clear signing: failed to display field "%s" (%s)',
                        field_definition.label,
                        type(e).__name__,
                    )
                raise

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
            provider_name=proto.provider_name,
            parameter_definitions=[
                ABIValue.from_proto(p) for p in proto.parameter_definitions
            ],
            field_definitions=[
                FieldDefinition.from_proto(f) for f in proto.field_definitions
            ],
        )


async def request_definitions(
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


async def _find_display_format(
    func_sig: bytes, address_bytes: bytes, msg: MsgInSignTx, nested: bool = False
) -> DisplayFormat | None:
    """Find a display format for calling `func_sig` on the `address_bytes`
    contract, trying built-ins, then the definitions provided in the initial
    request, then a definition request over the wire."""

    from .clear_signing_definitions import all_display_formats

    for f in all_display_formats():
        if f.matches_call(func_sig, msg.chain_id, address_bytes):
            return f

    if not nested and msg.definitions and msg.definitions.encoded_display_format:
        f = DisplayFormat.from_encoded(msg.definitions.encoded_display_format)
        if f.matches_call(func_sig, msg.chain_id, address_bytes):
            return f

    if msg.supports_definition_request:
        _, f = await request_definitions(msg.chain_id, address_bytes, func_sig)
        if f is not None and f.matches_call(func_sig, msg.chain_id, address_bytes):
            return f

    return None


async def _expand_calldata_field(
    field_definition: FieldDefinition,
    formatter: CalldataFormatter,
    path_walker: PathWalker,
    msg: MsgInSignTx,
    defs: Definitions,
    nested: bool,
) -> list[DisplayedField]:
    """Expand one `calldata` field - an embedded subcall - into display rows.

    The field's path resolves to one `bytes` blob of embedded calldata, and
    `callee_path` to the address of the contract it is sent to. On success
    the rows are the subcall's provider and intent, followed by the fields
    of the callee's display format, labels prefixed. Whenever the subcall
    cannot be clear-signed - no display format available, malformed inner
    calldata, unresolvable inner fields - it degrades to two rows, the
    callee and the raw hex blob, instead of failing the outer transaction."""
    from .sc_constants import lookup_known_address

    blob = path_walker(field_definition.path)
    if not isinstance(blob, bytes):
        # Calldata should be a bytes field
        raise InvalidFormatDefinition

    callee = path_walker(formatter.callee_path)
    if not isinstance(callee, bytes) or len(callee) != _ADDRESS_BYTES:
        raise InvalidFormatDefinition

    def callee_str() -> str:
        return lookup_known_address(msg.chain_id, callee) or address_from_bytes(
            callee, defs.network
        )

    def raw_rows() -> list[DisplayedField]:
        """No subparsing. Show the callee and the raw hex blob."""
        from ubinascii import hexlify

        return [
            ((TR.ethereum__subcall_to, callee_str(), None), None, None),
            ((field_definition.label, hexlify(blob).decode(), None), None, None),
        ]

    if nested:
        # already inside a subcall: no tertiary lookups
        return raw_rows()

    if formatter.selector is not None:
        # per ERC-7730, an explicit selector means the blob is args-only
        func_sig = formatter.selector
        body = memoryview(blob)
    elif len(blob) >= SC_FUNC_SIG_BYTES:
        func_sig = bytes(blob[:SC_FUNC_SIG_BYTES])
        body = memoryview(blob)[SC_FUNC_SIG_BYTES:]
    else:
        return raw_rows()

    try:
        inner_format = await _find_display_format(func_sig, callee, msg, nested=True)
        if inner_format is None:
            return raw_rows()
        _, inner_fields = await inner_format.parse_calldata(
            body, msg, defs, nested=True, override_callee=callee
        )
    except (ClearSigningFailed, DataError) as e:
        if __debug__:
            from trezor import log

            log.debug(
                __name__,
                'clear signing: subcall "%s" degraded to raw hex (%s)',
                field_definition.label,
                type(e).__name__,
            )
        return raw_rows()

    subcall = TR.ethereum__subcall
    rows: list[DisplayedField] = [
        (
            (
                f"({subcall}) {TR.words__provider}",
                inner_format.provider_name or callee_str(),
                None,
            ),
            None,
            None,
        ),
        ((f"({subcall}) {TR.words__intent}", inner_format.intent, None), None, None),
    ]
    for (inner_label, formatted, is_mono), token, token_address in inner_fields:
        rows.append(
            ((f"({subcall}) {inner_label}", formatted, is_mono), token, token_address)
        )
    return rows


async def try_confirm(
    data: AnyBytes,
    address_bytes: bytes,
    msg: MsgInSignTx,
    defs: Definitions,
    maximum_fee: str,
    fee_items: Sequence[StrPropertyType],
    payment_request_verifier: PaymentRequestVerifier | None,
) -> bool:
    from .clear_signing_definitions import (
        APPROVE_DISPLAY_FORMAT,
        TRANSFER_DISPLAY_FORMAT,
    )

    if not address_bytes:
        return False

    if len(data) < SC_FUNC_SIG_BYTES:
        return False

    func_sig = bytes(data[0:SC_FUNC_SIG_BYTES])

    display_format = await _find_display_format(func_sig, address_bytes, msg)
    if display_format is None:
        return False

    if (
        payment_request_verifier is not None
        and display_format.func_sig != TRANSFER_DISPLAY_FORMAT.func_sig
    ):
        raise DataError("Payment Requests only supported for ERC-20 transfers.")

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
    from .layout import require_confirm_approve
    from .sc_constants import lookup_known_address
    from .yielding_vaults import UNKNOWN_VAULT, lookup_vault

    # approve() is not payable; surface any native ETH sent along with it.
    native_value = int.from_bytes(msg.value, "big")
    native_amount = (
        format_ethereum_amount(native_value, None, defs.network)
        if native_value
        else None
    )

    args, fields = await display_format.parse_calldata(calldata, msg, defs)

    if len(args) != 2 or len(fields) != 2:
        raise InvalidFormatDefinition

    arg0_raw_value = args[0]
    (field0_name, recipient_addr, _), _, _ = fields[0]
    if field0_name != "Spender":
        raise InvalidFormatDefinition

    assert isinstance(arg0_raw_value, bytes)
    assert isinstance(recipient_addr, str)

    arg1_raw_value = args[1]
    (field1_name, value, _), actual_token, _ = fields[1]
    if field1_name != "Amount":
        raise InvalidFormatDefinition

    assert isinstance(arg1_raw_value, int)

    recipient_str = (
        lookup_known_address(msg.chain_id, arg0_raw_value)
        if display_format.provider_name is None
        else display_format.provider_name
    )

    # Ideally our vault name and definition should also be added in the ERC-7730 registry
    # Until that is verified, we'll keep our vault information hardcoded.
    if recipient_str is None:
        vault = lookup_vault(defs.network, arg0_raw_value)
        if vault is not UNKNOWN_VAULT:
            recipient_str = vault.name

    # In revocation, the approved amount is set to zero:
    is_revoke = arg1_raw_value == 0

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
        native_amount=native_amount,
    )


async def _handle_transfer(
    calldata: memoryview,
    display_format: DisplayFormat,
    address_bytes: bytes,
    msg: MsgInSignTx,
    defs: Definitions,
    maximum_fee: str,
    fee_items: Sequence[StrPropertyType],
    payment_request_verifier: PaymentRequestVerifier | None,
) -> None:
    from .layout import require_confirm_payment_request, require_confirm_tx

    # transfer() is not payable; surface any native ETH sent along with it.
    native_value = int.from_bytes(msg.value, "big")
    native_amount = (
        format_ethereum_amount(native_value, None, defs.network)
        if native_value
        else None
    )

    args, fields = await display_format.parse_calldata(calldata, msg, defs)

    if len(args) != 2 or len(fields) != 2:
        raise InvalidFormatDefinition

    (field0_name, recipient_addr, _), _, _ = fields[0]
    if field0_name != "To":
        raise InvalidFormatDefinition

    assert isinstance(recipient_addr, str)

    arg1_raw_value = args[1]
    (field1_name, value, _), actual_token, _ = fields[1]
    if field1_name != "Amount":
        raise InvalidFormatDefinition

    assert isinstance(arg1_raw_value, int)
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
            native_amount=native_amount,
        )


async def _handle_generic_ui(
    calldata: memoryview,
    display_format: DisplayFormat,
    msg: MsgInSignTx,
    defs: Definitions,
    maximum_fee: str,
) -> None:
    from trezor.ui.layouts.properties import AboveThreshold

    from . import tokens
    from .helpers import bytes_from_address
    from .layout import require_confirm_clear_signing
    from .sc_constants import lookup_known_address

    # Surface the native ETH value in the summary when non-zero - unless the
    # display format already renders it as an `AmountFormatter` field (e.g. a
    # swap's "Amount to Send"). That field shows the same canonical string the
    # summary would, so repeating it there is pure duplication. A `@.value`
    # field formatted any other way still gets its own summary line.
    value = int.from_bytes(msg.value, "big")
    value_shown_as_amount_field = any(
        fd.path == ContainerPath.Value
        and isinstance(fd.get_formatter(), AmountFormatter)
        for fd in display_format.field_definitions
    )
    amount = (
        format_ethereum_amount(value, None, defs.network)
        if value and not value_shown_as_amount_field
        else None
    )

    _, fields = await display_format.parse_calldata(calldata, msg, defs)

    properties_to_confirm = []

    for (label, formatted, is_mono), actual_token, actual_token_address in fields:
        if isinstance(formatted, AboveThreshold):
            formatted = formatted.message
        properties_to_confirm.append((label, formatted, is_mono))
        if actual_token is tokens.UNKNOWN_TOKEN:
            assert actual_token_address is not None
            token_address_str = address_from_bytes(actual_token_address, defs.network)
            token_address_property: StrPropertyType = (
                TR.ethereum__token_contract,
                token_address_str,
                None,
            )
            properties_to_confirm.append(token_address_property)

    recipient_str = (
        (lookup_known_address(msg.chain_id, bytes_from_address(msg.to)) or msg.to)
        if display_format.provider_name is None
        else display_format.provider_name
    )

    await require_confirm_clear_signing(
        recipient_str, display_format.intent, properties_to_confirm, maximum_fee, amount
    )
