from micropython import const
from typing import TYPE_CHECKING

from trezor import TR
from trezor.wire import DataError
from trezor.wire.context import UnexpectedMessageException

from .definitions import Definitions
from .helpers import (
    address_from_bytes,
    bytes_from_address,
    format_ethereum_amount,
    get_account_and_path,
    lookup_known_address,
    request_definitions,
)

if TYPE_CHECKING:
    from buffer_types import AnyBytes
    from collections.abc import Callable, Iterable, Sequence

    from trezor.messages import (
        EthereumABIValueInfo,
        EthereumDisplayFormatInfo,
        EthereumERC7730FieldInfo,
        EthereumTokenInfo,
    )
    from trezor.ui.layouts.properties import AboveThreshold
    from trezorui_api import StrPropertyType
    from typing_extensions import Self

    from apps.common.payment_request import PaymentRequestVerifier

    from .keychain import MsgInSignTx

    # Represents values that have been parsed from the calldata
    # into our internal representation.
    # TODO: Revisit simplifying this.
    Value = int | bytes | bool | str | None | list["Value"]
    # a tuple field may itself be a tuple or an array, so its elements are
    # the full `AnyValue`, not just leaf `Value`s
    TupleValue = tuple["AnyValue", ...]
    ListValue = list[TupleValue]
    AnyValue = Value | TupleValue | list["AnyValue"]

    # A data path (tuple of steps), a container path (int enum), or a literal
    # constant value (str, resolved by the parser — not walked from calldata).
    Path = tuple[int | tuple[int] | tuple[int, int], ...] | int | str
    PathWalker = Callable[[Path], AnyValue]

    # Parses a Value from a slice of the calldata.
    # Assumes that the memoryview contains just that value.
    Parser = Callable[[memoryview], Value]

    # Output of a `FieldFormatter.format`
    # (formatted value, token, token_address)
    FormattedValue = tuple[
        str | AboveThreshold | None,
        EthereumTokenInfo | None,
        AnyBytes | None,
    ]

    # Rendered value. 1st member is essentially StrPropertyType
    # ((label, formatted value, is_mono), token, token_address)
    RenderedField = tuple[
        tuple[str, str | AboveThreshold | None, bool | None],
        EthereumTokenInfo | None,
        AnyBytes | None,
    ]


SC_FUNC_SIG_BYTES = const(4)
_EVM_WORD_SIZE = const(32)  # in bytes
_EVM_WORD_BITS = const(8 * _EVM_WORD_SIZE)
_ADDRESS_BYTES = const(20)

# To be kept in sync in the definitions repo (definitions/ethereum/erc7730/erc7730.py)
# Recursion depth for raw decoding (ABIValue.from_proto)
_MAX_ABI_NESTING = const(8)
# Encoding depth counting just array nesting. To be increased cautiously.
_MAX_NESTED_ARRAYS = const(2)


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


class MustMatchViolation(ValueError):
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


def _to_bytes(value: AnyValue) -> bytes:
    """Byte form of a decoded value as compared against `ifNotIn` /
    `mustMatch`: ints (uint/int/bool/@.value) as a 32-byte two's-complement
    word, strings as UTF-8, address/bytesN/bytes/slices as-is. Anything else
    (None, arrays) is rejected."""
    # bool listed explicitly: in MicroPython it is not an int subclass
    if isinstance(value, (int, bool)):
        return (value % (1 << _EVM_WORD_BITS)).to_bytes(_EVM_WORD_SIZE, "big")
    if isinstance(value, str):
        return value.encode()
    if isinstance(value, (bytes, bytearray)):
        return bytes(value)
    raise InvalidFormatDefinition  # Arrays not expected.


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
    elif t == T.ABI_UINT216:
        return make_uint_parser(216)
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
    elif t == T.ABI_INT256:
        return make_int_parser(256)
    elif t == T.ABI_INT160:
        return make_int_parser(160)
    elif t == T.ABI_INT128:
        return make_int_parser(128)
    elif t == T.ABI_INT64:
        return make_int_parser(64)
    elif t == T.ABI_INT32:
        return make_int_parser(32)
    elif t == T.ABI_INT24:
        return make_int_parser(24)
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


# Field formatters: https://eips.ethereum.org/EIPS/eip-7730#field-formats


class FieldFormatter:
    async def format(
        self,
        value: AnyValue,
        msg: MsgInSignTx,
        defs: Definitions,
        path_walker: PathWalker,
    ) -> FormattedValue:
        """
        Format a field using the current formatter.
        Return the formatted value and optionally a token and a token address,
        if formatting this value implied dealing with a new token
        (like getting a token from parameters using `token_path`).
        """
        raise InvalidFormatDefinition


def _validate_chain_id(chain_id: AnyValue) -> int:
    # EthereumDefinitionRequest.chain_id is a uint64
    if not isinstance(chain_id, int) or not 0 < chain_id < 1 << 64:
        raise InvalidFormatDefinition
    return chain_id


class PathOrConst:
    """An ERC-7730 formatter param, given either as `<param>Path` (walked
    from the calldata or the container) or as a constant `<param>`. Exactly
    one of the two is set; an absent param is `None` instead of an instance."""

    def __init__(self, path: Path | None = None, const: AnyValue = None) -> None:
        if (path is None) == (const is None):
            raise InvalidFormatDefinition
        self.path = path
        self.const = const

    def resolve(self, path_walker: PathWalker) -> AnyValue:
        if self.path is None:
            return self.const
        value = path_walker(self.path)
        if value is None:
            # a set param must not silently fall back to its default
            raise InvalidFormatDefinition
        return value


def _resolve_other_chain_id(
    chain_id: PathOrConst | None, path_walker: PathWalker
) -> int | None:
    """Return the chain ID given by the `chainId` / `chainIdPath` params, or
    None if they are absent or name the chain of the call being displayed
    (`@.chainId`: the transaction's, or an embedded call's)."""
    if chain_id is None:
        return None
    other = _validate_chain_id(chain_id.resolve(path_walker))
    return (
        None
        if other == _validate_chain_id(path_walker(ContainerPath.ChainId))
        else other
    )


async def _definitions_for_another_chain(
    chain_id: int, token_address: bytes, native: bool, msg: MsgInSignTx
) -> Definitions:

    from .definitions import Definitions
    from .networks import UNKNOWN_NETWORK
    from .tokens import UNKNOWN_TOKEN

    defs = Definitions.from_encoded(None, None, chain_id)
    missing = defs.network is UNKNOWN_NETWORK or (
        not native and defs.get_token(token_address) is UNKNOWN_TOKEN
    )
    if missing and msg.supports_definition_request:
        received, _ = await request_definitions(chain_id, token_address, None)
        if received is not None:
            defs = received
    return defs


def _unknown_token_on_chain(chain_id: int) -> EthereumTokenInfo:
    """Needed to embed the foreign chain ID into the token info class.
    address being empty is a key signal of the token being unknown (but the chain being known occassionally)."""

    from trezor.messages import EthereumTokenInfo

    from .tokens import UNKNOWN_TOKEN

    return EthereumTokenInfo(
        symbol=UNKNOWN_TOKEN.symbol,
        decimals=UNKNOWN_TOKEN.decimals,
        address=UNKNOWN_TOKEN.address,  # Empty address
        chain_id=chain_id,
        name=UNKNOWN_TOKEN.name,
    )


class AddressNameFormatter(FieldFormatter):
    def __init__(
        self, lookup_address: bool = False, chain_id: PathOrConst | None = None
    ) -> None:
        self.lookup_address = lookup_address
        self.chain_id = chain_id

    async def format(
        self,
        address: AnyValue,
        msg: MsgInSignTx,
        defs: Definitions,
        path_walker: PathWalker,
    ) -> FormattedValue:
        if address is None:
            return None, None, None
        elif isinstance(address, str):
            return address, None, None
        else:
            if not isinstance(address, bytes):
                raise InvalidFormatDefinition
            other_chain_id = _resolve_other_chain_id(self.chain_id, path_walker)
            if self.lookup_address:
                try:
                    address_name = await lookup_known_address(
                        (
                            _validate_chain_id(path_walker(ContainerPath.ChainId))
                            if other_chain_id is None
                            else other_chain_id
                        ),
                        address,
                        msg,
                    )
                except UnexpectedMessageException:
                    # the host may abort the workflow by sending a new message
                    raise
                except Exception:
                    address_name = None
                if address_name is not None:
                    return address_name, None, None
            return address_from_bytes(address, defs.network), None, None


class AmountFormatter(FieldFormatter):
    async def format(
        self,
        amount: AnyValue,
        _msg: MsgInSignTx,
        defs: Definitions,
        _path_walker: PathWalker,
    ) -> FormattedValue:
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
        token: PathOrConst | None = None,
        native_currency_address: list[bytes] | None = None,
        threshold: int | None = None,
        threshold_message: str | None = None,
        chain_id: PathOrConst | None = None,
    ) -> None:
        self.token = token
        self.native_currency_address = native_currency_address
        self.threshold = threshold
        self.threshold_message = threshold_message
        self.chain_id = chain_id

    async def format(
        self,
        amount: AnyValue,
        msg: MsgInSignTx,
        defs: Definitions,
        path_walker: PathWalker,
    ) -> FormattedValue:
        """Returns (formatted_value, token, token_address)"""
        from trezor.ui.layouts.properties import AboveThreshold

        from .tokens import UNKNOWN_TOKEN

        if amount is None:
            return None, None, None

        if not isinstance(amount, int):
            raise InvalidFormatDefinition

        token_address: AnyBytes | None = None
        if self.token is not None:
            resolved = self.token.resolve(path_walker)
            if not isinstance(resolved, bytes):
                raise InvalidFormatDefinition
            token_address = resolved

        other_chain_id = _resolve_other_chain_id(self.chain_id, path_walker)
        token_defs = defs

        token: EthereumTokenInfo | None
        if token_address is None:
            token = UNKNOWN_TOKEN
        elif (
            # NATIVE CURRENCY CASE
            self.native_currency_address is not None
            and token_address in self.native_currency_address
        ):
            token = None
            if other_chain_id is not None:
                from .networks import UNKNOWN_NETWORK

                # the other chain's native currency
                token_defs = await _definitions_for_another_chain(
                    other_chain_id, token_address, True, msg
                )
                if token_defs.network is UNKNOWN_NETWORK:
                    # its symbol is unknown: show the raw value instead
                    token = UNKNOWN_TOKEN
            token_address = None
        elif other_chain_id is not None:
            token_defs = await _definitions_for_another_chain(
                other_chain_id, token_address, False, msg
            )
            token = token_defs.get_token(token_address)
        else:
            token = defs.get_token(token_address)
            if token is UNKNOWN_TOKEN:
                if msg.supports_definition_request:
                    received_definitions, _ = await request_definitions(
                        _validate_chain_id(path_walker(ContainerPath.ChainId)),
                        token_address,
                        func_sig=None,
                    )
                    if received_definitions is not None:
                        token = received_definitions.get_token(token_address)

        if other_chain_id is not None and token is UNKNOWN_TOKEN:
            # remember the chain, so that it can be shown next to the token
            token = _unknown_token_on_chain(other_chain_id)

        if self.threshold is not None and amount >= self.threshold:
            formatted = AboveThreshold(self.threshold_message or TR.words__unlimited)
        else:
            formatted = format_ethereum_amount(amount, token, token_defs.network)
        return formatted, token, token_address


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
    ) -> FormattedValue:
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
    ) -> FormattedValue:
        if value is None:
            return None, None, None
        elif isinstance(value, str):
            return value, None, None
        elif isinstance(value, (bytes, bytearray)):
            return value.hex(), None, None
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
    ) -> FormattedValue:
        from trezor.strings import format_timestamp

        if value is None:
            return None, None, None
        if isinstance(value, (bytes, bytearray)):
            # a sliced word, e.g. `goodUntil.[-4:]`: big-endian seconds
            value = int.from_bytes(value, "big")
        if isinstance(value, int):
            return format_timestamp(value), None, None
        raise InvalidFormatDefinition


class DurationFormatter(FieldFormatter):
    """Duration in seconds. Formatted as HH:MM:ss"""

    async def format(
        self,
        value: AnyValue,
        _msg: MsgInSignTx,
        _definitions: Definitions,
        _path_walker: PathWalker,
    ) -> FormattedValue:
        if value is None:
            return None, None, None
        if isinstance(value, bytes):
            # a sliced word, e.g. `deadline.[-4:]`: big-endian seconds
            value = int.from_bytes(value, "big")
        if isinstance(value, int):
            if value < 0:
                # a negative duration has no sensible rendering
                raise InvalidFormatDefinition
            minutes, seconds = divmod(value, 60)
            hours, minutes = divmod(minutes, 60)
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}", None, None
        raise InvalidFormatDefinition


class CalldataFormatter(RawFormatter):
    """ERC-7730 `calldata` format: the field's value is the embedded calldata
    of a nested call, rendered with the display format of the called contract
    (resolved from `callee`). Unlike every other formatter it expands
    into multiple display rows, so `DisplayFormat.parse_calldata` handles it
    directly (see `_expand_calldata_field`) instead of going through the
    single-value `format` interface. Subclassing `RawFormatter` is defense
    in depth: should a code path ever fail to special-case this formatter,
    the inherited `format` renders the blob as raw hex instead of failing
    clear signing.

    Each param is a `PathOrConst`. The params set the embedded call's
    container values (see `EmbeddedContainer`):
      * callee (required): the called contract, the inner `@.to`
      * selector: the inner function selector; when set the blob is
        args-only, otherwise its first 4 bytes are the selector
      * amount: the native currency sent along, the inner `@.value`
      * spender: the sender of the embedded call, the inner `@.from`
      * chain ID: the chain of the embedded call, the inner `@.chainId`;
        defaults to the chain of the call holding the `calldata` field
    """

    def __init__(
        self,
        callee: PathOrConst,
        selector: PathOrConst | None = None,
        amount: PathOrConst | None = None,
        spender: PathOrConst | None = None,
        chain_id: PathOrConst | None = None,
    ) -> None:
        self.callee = callee
        self.selector = selector
        self.amount = amount
        self.spender = spender
        self.chain_id = chain_id


class EmbeddedContainer:
    """Container values of an embedded call (ERC-7730 `calldata` format),
    resolved from the `CalldataFormatter` params in the context of the call
    holding the `calldata` field. `@.from` and `@.value` are only known when
    the descriptor sets the `spender` / `amount` params: the device cannot
    tell whether the wrapper CALLs (`@.from` = the wrapper) or DELEGATECALLs
    (`@.from` = the signer) the callee, and the forwarded value is decided by
    wrapper logic. None = unresolvable in the embedded call. `from_` may be
    the signer's account label, like the transaction's `@.from`."""

    def __init__(
        self,
        to: bytes,
        chain_id: int,
        from_: bytes | str | None = None,
        value: int | None = None,
    ) -> None:
        self.to = to
        self.chain_id = chain_id
        self.from_ = from_
        self.value = value


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
    ) -> FormattedValue:
        if value is None:
            return None, None, None
        if isinstance(value, (bytes, bytearray)):
            # byte sliced to be read as an int
            value = int.from_bytes(value, "big")
        if isinstance(value, bool):
            value = int(value)
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
) -> FormattedValue:
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
        raise InvalidFormatDefinition

    @staticmethod
    def from_proto(
        info: EthereumABIValueInfo, depth: int = 0, arrays: int = 0
    ) -> "ABIValue":
        """Build the parser tree for one wire descriptor node.

        `depth` bounds recursion; `arrays` counts only the
        `Array` levels on this "root-to-leaf" path.
        Array lengths come from calldata and element bodies can alias, so nested
        arrays multiply; tuple fan-out is bounded by the definition."""
        if depth > _MAX_ABI_NESTING or arrays > _MAX_NESTED_ARRAYS:
            raise InvalidFormatDefinition
        if info.skip_item:
            # TODO: skippable parameters are not implemented yet.
            raise InvalidFormatDefinition
        if info.atomic is not None:
            return Atomic(_get_parser(info.atomic, is_dynamic=False))
        elif info.dynamic is not None:
            return DynamicLeaf(_get_parser(info.dynamic, is_dynamic=True))
        elif info.tuple is not None:
            return Tuple(
                tuple(
                    ABIValue.from_proto(f, depth + 1, arrays) for f in info.tuple.fields
                )
            )
        elif info.array is not None:
            return Array(ABIValue.from_proto(info.array, depth + 1, arrays + 1))
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
    contain multiple values of possibly different types.

    A tuple is a dynamic type iff at least one of its fields is dynamic.
    Its body is the concatenation of its fields' heads: a static field is
    encoded in place, while a dynamic field's head is the offset of its
    length-prefixed data, relative to the body start. A static tuple is
    therefore just its field values back to back - no length prefix and no
    offset words anywhere."""

    def __init__(self, fields: tuple[ABIValue, ...]) -> None:
        if not fields:
            raise InvalidFormatDefinition
        self.fields = fields
        # `head_size` is already the head *span* of any node: one word for
        # dynamic types, the full in-place size for static ones.
        self.fields_size = sum(f.head_size for f in fields)
        self.is_dynamic = any(f.is_dynamic for f in fields)
        if not self.is_dynamic:
            self.head_size = self.fields_size

    def parse_body(self, raw_data: memoryview, pos: int) -> AnyValue:
        if pos + self.fields_size > len(raw_data):
            raise OutOfBounds
        value: list[AnyValue] = []
        head_offset = pos
        for field in self.fields:
            data, consumed = field.parse(raw_data, head_offset, pos)
            value.append(data)
            head_offset += consumed
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
    ChainId = 4


class FieldDefinition:
    def __init__(
        self,
        path: Path,
        label: str,
        formatter: FieldFormatter | type[FieldFormatter],
        if_not_in: list[bytes] | None = None,
        must_match: list[bytes] | None = None,
    ) -> None:
        self.path = path
        self.label = label
        self.formatter = formatter
        self.if_not_in = if_not_in
        self.must_match = must_match

    def is_hidden(self, value: AnyValue) -> bool:
        """Raise if mustMatch is violated, return True if ifNotIn suggests hiding"""
        if self.must_match:
            if _to_bytes(value) not in self.must_match:
                raise MustMatchViolation
            return True
        if self.if_not_in:
            return _to_bytes(value) in self.if_not_in
        return False

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

        def param(
            path: EthereumERC7730Path | None,
            const: AnyBytes | int | None,
            const_len: int | None = None,
        ) -> PathOrConst | None:
            """`<param>Path` / `<param>` pair; None if neither is set. A bytes
            constant is copied and, given `const_len`, its length checked."""
            if path is None and const is None:
                return None
            if const is not None and not isinstance(const, int):
                const = bytes(const)
                if const_len is not None and len(const) != const_len:
                    raise InvalidFormatDefinition
            return PathOrConst(decode_path(path) if path is not None else None, const)

        path = decode_path(info.path)
        if isinstance(path, str) and (info.if_not_in or info.must_match):
            # Constant path = metadata stuff. No validation required.
            # Definitions should drop it already
            # https://github.com/trezor/definitions/pull/156
            raise InvalidFormatDefinition

        chain_id = param(info.chain_id_path, info.const_chain_id)

        fmt_type = info.formatter
        if chain_id is not None and (
            fmt_type
            not in (
                FT.FORMATTER_ADDRESS_NAME,
                FT.FORMATTER_TOKEN_AMOUNT,
                FT.FORMATTER_CALLDATA,
            )
        ):
            raise InvalidFormatDefinition

        if fmt_type == FT.FORMATTER_ADDRESS_NAME:
            formatter = AddressNameFormatter(info.lookup_address, chain_id)
        elif fmt_type == FT.FORMATTER_AMOUNT:
            formatter = AmountFormatter
        elif fmt_type == FT.FORMATTER_TOKEN_AMOUNT:
            formatter_params = {}
            if info.threshold is not None:
                formatter_params["threshold"] = int.from_bytes(info.threshold, "big")
            if info.threshold_message is not None:
                formatter_params["threshold_message"] = info.threshold_message
            if info.native_currency_address:
                formatter_params["native_currency_address"] = [
                    bytes(addr) for addr in info.native_currency_address
                ]
            formatter = TokenAmountFormatter(
                token=param(info.token_path, info.const_token_address),
                chain_id=chain_id,
                **formatter_params,
            )
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
        elif fmt_type == FT.FORMATTER_DURATION:
            formatter = DurationFormatter
        elif fmt_type == FT.FORMATTER_CALLDATA:
            callee = param(info.callee_path, info.const_callee, _ADDRESS_BYTES)
            if callee is None:
                # the callee is required
                raise InvalidFormatDefinition
            const_amount = info.const_amount
            if const_amount is not None:
                if len(const_amount) > _EVM_WORD_SIZE:
                    # a uint256
                    raise InvalidFormatDefinition
                const_amount = int.from_bytes(const_amount, "big")
            formatter = CalldataFormatter(
                callee=callee,
                selector=param(info.selector_path, info.selector, SC_FUNC_SIG_BYTES),
                amount=param(info.amount_path, const_amount),
                spender=param(info.spender_path, info.const_spender, _ADDRESS_BYTES),
                chain_id=chain_id,
            )
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

        return FieldDefinition(
            path=path,
            label=info.label,
            formatter=formatter,
            if_not_in=[bytes(b) for b in info.if_not_in],
            must_match=[bytes(b) for b in info.must_match],
        )

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
        container: EmbeddedContainer | None = None,
    ) -> tuple[list[AnyValue], list[RenderedField]]:
        """Parse `calldata` (without the selector) and format the display fields.

        Loosely speaking, it returns ([parameter = parsed value], [formatted value])

        `container` marks the parse of an embedded subcall's calldata (see
        `_expand_calldata_field`) and supplies its container paths (`@.to`
        is the subcall's callee, not the outer transaction's recipient, ...).
        `defs` are then the definitions of the subcall's chain. Any further
        calldata fields render as raw hex instead of triggering tertiary
        lookups."""
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
                # standard container (transaction) paths like @.from, @.value...
                if container is not None:
                    # A subcall: the wrapper (`msg.to`) merely forwards the
                    # call, so e.g. a nested transfer's `token_path=@.to`
                    # resolves to the token contract, not to the wrapper.
                    # `@.from` / `@.value` are only known when the outer
                    # descriptor sets them (`spender` / `amount` params):
                    # guessing would risk a confidently wrong display.
                    if path == ContainerPath.To:
                        value = container.to
                    elif path == ContainerPath.ChainId:
                        value = container.chain_id
                    elif path == ContainerPath.From:
                        value = container.from_
                    elif path == ContainerPath.Value:
                        value = container.value
                    else:
                        value = None
                    if value is None:
                        raise InvalidFormatDefinition
                    return value
                if path == ContainerPath.ChainId:
                    return msg.chain_id
                if path == ContainerPath.To:
                    return bytes_from_address(msg.to)
                if path == ContainerPath.From:
                    # Conditional visibility check not required.
                    # Sending account label is fine.
                    account, _ = get_account_and_path(msg.address_n)
                    return account
                elif path == ContainerPath.Value:
                    return int.from_bytes(msg.value, "big")
                else:
                    raise InvalidFormatDefinition  # TODO
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

        fields: list[RenderedField] = []
        for field_definition in self.field_definitions:
            try:
                value = get_value_for_path(field_definition.path)
                if field_definition.is_hidden(value):
                    continue
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
                            container is not None,  # nested
                        )
                    )
                    continue
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

        return cls.from_proto(decode_definition(encoded, EthereumDisplayFormatInfo))

    @classmethod
    def from_proto(cls, proto: EthereumDisplayFormatInfo) -> Self:
        # Clear signing needs a 4-byte selector. Name-only definitions (see
        # `lookup_known_address`) use a longer one and must not be used for clear signing.
        if len(proto.func_sig) != SC_FUNC_SIG_BYTES:
            raise DataError("Invalid display format")
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


async def find_display_format(
    func_sig: bytes,
    contract_address: bytes,
    msg: MsgInSignTx,
    nested: bool = False,
    chain_id: int | None = None,
) -> DisplayFormat | None:
    """Find a display format for calling `func_sig` on the `contract_address`
    contract on `chain_id` (default: the transaction's chain), trying
    built-ins, then the definitions provided in the initial request, then a
    definition request over the wire."""

    from .clear_signing_definitions import all_display_formats

    if chain_id is None:
        chain_id = msg.chain_id

    for display_format in all_display_formats():
        if display_format.matches_call(func_sig, chain_id, contract_address):
            return display_format

    if not nested and msg.definitions and msg.definitions.encoded_display_format:
        display_format = DisplayFormat.from_encoded(
            msg.definitions.encoded_display_format
        )
        if display_format.matches_call(func_sig, chain_id, contract_address):
            return display_format

    if msg.supports_definition_request:
        _, proto = await request_definitions(chain_id, contract_address, func_sig)
        display_format = DisplayFormat.from_proto(proto) if proto is not None else None
        if display_format is not None and display_format.matches_call(
            func_sig, chain_id, contract_address
        ):
            return display_format

    return None


def _embedded_container(
    callee: AnyValue,
    amount: AnyValue,
    spender: AnyValue,
    chain_id: AnyValue,
    current_chain_id: int,
) -> EmbeddedContainer:
    """Validate the resolved `calldata` params of one subcall."""
    if not isinstance(callee, bytes) or len(callee) != _ADDRESS_BYTES:
        raise InvalidFormatDefinition
    if amount is not None and (
        isinstance(amount, bool) or not isinstance(amount, int) or amount < 0
    ):
        raise InvalidFormatDefinition
    if spender is not None and not (
        # an address, or the signer's account label (an outer `@.from`)
        isinstance(spender, str)
        or (isinstance(spender, bytes) and len(spender) == _ADDRESS_BYTES)
    ):
        raise InvalidFormatDefinition
    return EmbeddedContainer(
        to=callee,
        chain_id=(
            current_chain_id if chain_id is None else _validate_chain_id(chain_id)
        ),
        from_=spender,
        value=amount,
    )


async def _expand_calldata_field(
    field_definition: FieldDefinition,
    formatter: CalldataFormatter,
    path_walker: PathWalker,
    msg: MsgInSignTx,
    defs: Definitions,
    nested: bool,
) -> list[RenderedField]:
    """Expand one `calldata` field into display rows.

    The field's path resolves either to one `bytes` blob of embedded calldata
    (a single subcall), or to an array of such blobs (e.g. a multicall's
    `bytes[] data`). In the array case each element is expanded as its own
    subcall and its rows are labeled "(Subcall #1)", "(Subcall #2)", ...;
    each param (callee, selector, ...) then resolves either to a single value
    shared by all subcalls or, from a path, to a parallel array of the same
    length."""
    blobs = path_walker(field_definition.path)
    single = not isinstance(blobs, list)
    blobs = [blobs] if single else blobs
    count = len(blobs)

    def per_subcall(param: PathOrConst | None) -> Sequence[AnyValue]:
        value = param.resolve(path_walker) if param is not None else None
        if isinstance(value, list):
            if single or len(value) != count:
                raise InvalidFormatDefinition
            return value
        # shared by all subcalls
        return [value] * count

    callees = per_subcall(formatter.callee)
    selectors = per_subcall(formatter.selector)
    amounts = per_subcall(formatter.amount)
    spenders = per_subcall(formatter.spender)
    chain_ids = per_subcall(formatter.chain_id)
    # the chain of the call holding the `calldata` field
    current_chain_id = _validate_chain_id(path_walker(ContainerPath.ChainId))

    rows: list[RenderedField] = []
    for i in range(count):
        blob, selector = blobs[i], selectors[i]
        if not isinstance(blob, bytes):
            # Calldata should be a bytes field
            raise InvalidFormatDefinition
        if selector is not None and (
            not isinstance(selector, bytes) or len(selector) != SC_FUNC_SIG_BYTES
        ):
            raise InvalidFormatDefinition
        container = _embedded_container(
            callees[i], amounts[i], spenders[i], chain_ids[i], current_chain_id
        )
        rows.extend(
            await _expand_one_subcall(
                field_definition,
                blob,
                selector,
                container,
                current_chain_id,
                msg,
                defs,
                nested,
                index=None if single else i + 1,
            )
        )
    return rows


async def _expand_one_subcall(
    field_definition: FieldDefinition,
    blob: bytes,
    selector: bytes | None,
    container: EmbeddedContainer,
    current_chain_id: int,
    msg: MsgInSignTx,
    defs: Definitions,
    nested: bool,
    index: int | None = None,
) -> list[RenderedField]:
    """Expand one embedded subcall into display rows.

    On success the rows are the subcall's provider and intent, followed by
    the fields of the callee's display format, labels prefixed. Whenever the
    subcall cannot be clear-signed - no display format available, malformed
    inner calldata, unresolvable inner fields - it degrades to two rows, the
    callee and the raw hex blob, instead of failing the outer transaction.
    A subcall on a chain other than `current_chain_id` (the chain of the call
    holding the `calldata` field) adds a row naming its chain, after the
    intent / callee row.
    `index` is the subcall's 1-based position when it comes from an array of
    subcalls, reflected in the label prefix: "(Subcall #<index>)"."""
    from .networks import UNKNOWN_NETWORK
    from .tokens import UNKNOWN_TOKEN

    callee = container.to
    chain_id = container.chain_id
    other_chain = chain_id != current_chain_id

    if not other_chain:
        inner_defs = defs
    elif nested:
        # already inside a subcall: no tertiary lookups
        inner_defs = Definitions.from_encoded(None, None, chain_id)
    else:
        inner_defs = await _definitions_for_another_chain(chain_id, callee, True, msg)

    subcall = TR.ethereum__subcall
    if index is not None:
        subcall = f"{subcall} #{index}"

    async def callee_str() -> str:
        # already inside a subcall: no tertiary lookups
        known = await lookup_known_address(chain_id, callee, None if nested else msg)
        return known or address_from_bytes(callee, inner_defs.network)

    def chain_rows() -> list[RenderedField]:
        if not other_chain:
            return []
        if inner_defs.network is UNKNOWN_NETWORK:
            row = (TR.ethereum__approve_chain_id, str(chain_id))
        else:
            row = (TR.words__network, inner_defs.network.name)
        return [((f"({subcall}) {row[0]}", row[1], None), None, None)]

    async def raw_rows() -> list[RenderedField]:
        """No subparsing. Show the callee and the raw hex blob."""
        to_label = TR.ethereum__subcall_to
        blob_label = field_definition.label
        if index is not None:
            to_label = f"({subcall}) {TR.ethereum__to}"
            blob_label = f"({subcall}) {blob_label}"
        rows: list[RenderedField] = [((to_label, await callee_str(), None), None, None)]
        rows.extend(chain_rows())
        rows.append(((blob_label, blob.hex(), None), None, None))
        return rows

    if nested:
        # already inside a subcall: no tertiary lookups
        return await raw_rows()

    if selector is not None:
        # per ERC-7730, an explicit selector means the blob is args-only
        func_sig = selector
        body = memoryview(blob)
    elif len(blob) >= SC_FUNC_SIG_BYTES:
        func_sig = bytes(blob[:SC_FUNC_SIG_BYTES])
        body = memoryview(blob)[SC_FUNC_SIG_BYTES:]
    else:
        return await raw_rows()

    try:
        inner_format = await find_display_format(
            func_sig, callee, msg, nested=True, chain_id=chain_id
        )
        if inner_format is None:
            return await raw_rows()
        _, inner_fields = await inner_format.parse_calldata(
            body, msg, inner_defs, container
        )
    except (ClearSigningFailed, DataError) as e:
        return await raw_rows()

    rows: list[RenderedField] = [
        (
            (
                f"({subcall}) {TR.words__provider}",
                inner_format.provider_name or await callee_str(),
                None,
            ),
            None,
            None,
        ),
        ((f"({subcall}) {TR.words__intent}", inner_format.intent, None), None, None),
    ]
    rows.extend(chain_rows())
    for (inner_label, formatted, is_mono), token, token_address in inner_fields:
        if token is UNKNOWN_TOKEN and chain_id != msg.chain_id:
            # remember the chain, so that it can be shown next to the token
            token = _unknown_token_on_chain(chain_id)
        rows.append(
            ((f"({subcall}) {inner_label}", formatted, is_mono), token, token_address)
        )
    return rows


async def try_confirm(
    data: AnyBytes,
    contract_address: bytes,
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

    if not contract_address:
        return False

    if len(data) < SC_FUNC_SIG_BYTES:
        return False

    func_sig = bytes(data[:SC_FUNC_SIG_BYTES])

    display_format = await find_display_format(func_sig, contract_address, msg)
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
            contract_address,
            msg,
            defs,
            maximum_fee,
            fee_items,
        )
    elif display_format.func_sig == TRANSFER_DISPLAY_FORMAT.func_sig:
        await _handle_transfer(
            calldata,
            display_format,
            contract_address,
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
            contract_address,
            msg,
            defs,
            maximum_fee,
        )
    return True


async def _handle_approve(
    calldata: memoryview,
    display_format: DisplayFormat,
    contract_address: bytes,
    msg: MsgInSignTx,
    defs: Definitions,
    maximum_fee: str,
    fee_items: Iterable[StrPropertyType],
) -> None:
    from .layout import require_confirm_approve

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

    recipient_str = display_format.provider_name

    if recipient_str is None:
        recipient_str = await lookup_known_address(msg.chain_id, arg0_raw_value, msg)

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
        actual_token or defs.get_token(contract_address),
        contract_address,
        is_revoke,
        bool(msg.chunkify),
        native_amount=native_amount,
    )


async def _handle_transfer(
    calldata: memoryview,
    display_format: DisplayFormat,
    contract_address: bytes,
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
        if native_value:
            raise DataError("Non-zero ETH value")

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
            actual_token or defs.get_token(contract_address),
            address_from_bytes(contract_address, defs.network),
        )
    else:
        await require_confirm_tx(
            recipient_addr,
            value,
            contract_address,
            msg.address_n,
            maximum_fee,
            fee_items,
            actual_token or defs.get_token(contract_address),
            is_send=True,
            chunkify=bool(msg.chunkify),
            native_amount=native_amount,
        )


async def _handle_generic_ui(
    calldata: memoryview,
    display_format: DisplayFormat,
    address_bytes: bytes,
    msg: MsgInSignTx,
    defs: Definitions,
    maximum_fee: str,
) -> None:
    from trezor.ui.layouts.properties import AboveThreshold

    from .helpers import bytes_from_address
    from .layout import require_confirm_clear_signing
    from .networks import UNKNOWN_NETWORK

    # Surface the native ETH value in the summary when non-zero - unless one of
    # the display format's own fields already renders it (e.g. a swap's "Amount
    # to Send"), in which case repeating it in the summary is pure duplication.

    value = int.from_bytes(msg.value, "big")
    amount = format_ethereum_amount(value, None, defs.network) if value else None

    _, fields = await display_format.parse_calldata(calldata, msg, defs)

    properties_to_confirm = []
    value_shown_as_field = False

    for (label, formatted, is_mono), actual_token, actual_token_address in fields:
        if isinstance(formatted, AboveThreshold):
            formatted = formatted.message
        if amount is not None and formatted == amount:
            value_shown_as_field = True
        properties_to_confirm.append((label, formatted, is_mono))

        # Not a token field OR known token (address is not empty) so no additional property addition.
        # TODO: This extra "unknown token" property can be moved to the menu, when this field is being displayed.
        # That would need to call `confirm_properties` separately. Also a tiny design issue that the user is not prompted to know that they can know more info about this unknown token.
        # The spec does ask (rightly so) to warn for unknown tokens. We can consider chaning the colour to yellow for whenever we have an unknown token.
        if actual_token is None or actual_token.address:
            continue

        token_chain_id = (
            actual_token.chain_id if actual_token.chain_id else msg.chain_id
        )  # actual_token.chain_id is 0 for UNKNOWN_TOKEN (_unknown_token_on_chain)

        # Unknown token, show its address
        if actual_token_address is not None:
            token_address_property: StrPropertyType = (
                f"{TR.words__address} ({TR.ethereum__unknown_token})",
                address_from_bytes(actual_token_address, defs.network),
                None,
            )
            properties_to_confirm.append(token_address_property)

        # Show when chain_id is different and token unknown
        if token_chain_id != msg.chain_id:
            properties_to_confirm.append(
                (
                    f"{TR.ethereum__approve_chain_id} ({TR.ethereum__unknown_token})",
                    str(token_chain_id),
                    None,
                )
            )

    contract_name = (
        (
            await lookup_known_address(msg.chain_id, bytes_from_address(msg.to), msg)
            or msg.to
        )
        if display_format.provider_name is None
        else display_format.provider_name
    )

    account, account_path = get_account_and_path(msg.address_n)

    # Name the chain when we recognize it, otherwise fall back to the bare chain ID.
    chain_info: StrPropertyType = (
        (TR.ethereum__approve_chain_id, str(msg.chain_id), None)
        if defs.network is UNKNOWN_NETWORK
        else (TR.words__chain, defs.network.name, None)
    )

    await require_confirm_clear_signing(
        contract_name=contract_name,
        intent=display_format.intent,
        properties=properties_to_confirm,
        maximum_fee=maximum_fee,
        contract_address=address_from_bytes(address_bytes, defs.network),
        chain_info=chain_info,
        amount=None if value_shown_as_field else amount,
        account=account,
        account_path=account_path,
    )
