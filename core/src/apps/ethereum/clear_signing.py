from micropython import const
from typing import TYPE_CHECKING

from trezor import TR
from trezor.utils import BufferReader

from .helpers import address_from_bytes, format_ethereum_amount, get_account_and_path

if TYPE_CHECKING:
    from buffer_types import AnyBytes
    from typing import Any, Callable, Coroutine, Iterable

    from trezor.messages import EthereumNetworkInfo, EthereumTokenInfo
    from trezor.ui.layouts import StrPropertyType

    from .definitions import Definitions
    from .helpers import ConfirmDataFn
    from .keychain import MsgInSignTx

    # Represents values that have been parsed from the calldata
    # into our internal representation.
    Value = int | bytes | bool | str | None | list["Value"]
    StructValue = tuple[Value, ...]
    ListValue = list[StructValue]
    AnyValue = Value | StructValue | ListValue | list[Value | StructValue | ListValue]

    # Parses a Value from a slice of the calldata.
    # Assumes that the memoryview contains just that value.
    Parser = Callable[[memoryview], AnyValue]


SC_FUNC_SIG_BYTES = const(4)
MAX_CALLDATA_STORED = const(4096)


class InvalidFunctionCall(Exception):
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


class InvalidFormatDefinition(Exception):
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


def parse_uint256(raw_data: memoryview) -> Value:
    if len(raw_data) < 32:
        raise OutOfBounds
    return int.from_bytes(raw_data, "big")


def parse_uint160(raw_data: memoryview) -> Value:
    if len(raw_data) < 32:
        raise OutOfBounds
    _check_padding_zero(raw_data, 160 // 8)
    return parse_uint256(raw_data)


def parse_uint24(raw_data: memoryview) -> Value:
    if len(raw_data) < 32:
        raise OutOfBounds
    _check_padding_zero(raw_data, 24 // 8)
    return parse_uint256(raw_data)


def parse_bool(raw_data: memoryview) -> Value:
    if len(raw_data) < 32:
        raise OutOfBounds
    uint_value = parse_uint256(raw_data)
    if uint_value not in (0, 1):
        raise ValueOverflow
    return uint_value == 1


def parse_address(raw_data: memoryview) -> Value:
    if len(raw_data) < 32:
        raise OutOfBounds
    _check_padding_zero(raw_data, 20, DirtyAddress)
    return bytes(raw_data[32 - 20 :])


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

# Field formatters: https://eips.ethereum.org/EIPS/eip-7730#field-formats


class FieldFormatter:
    def format(
        self, value: AnyValue, network: EthereumNetworkInfo, token: EthereumTokenInfo
    ) -> str | None:
        raise NotImplementedError


class AddressNameFormatter(FieldFormatter):
    def format(
        self, address: AnyValue, network: EthereumNetworkInfo, _token: EthereumTokenInfo
    ) -> str | None:
        if address is None:
            return "(None)"
        elif isinstance(address, str):
            return address
        else:
            if not isinstance(address, bytes):
                raise InvalidFormatDefinition
            return address_from_bytes(address, network)


class AmountFormatter(FieldFormatter):
    def format(
        self, amount: AnyValue, network: EthereumNetworkInfo, _token: EthereumTokenInfo
    ) -> str | None:
        if amount is None:
            return None
        else:
            if not isinstance(amount, int):
                raise InvalidFormatDefinition

            # Note: we are passing None rather than `_token`
            # to `format_ethereum_amount` because this formatter
            # is meant to be used with native ETH amounts
            return format_ethereum_amount(amount, None, network)


class TokenAmountFormatter(FieldFormatter):
    def __init__(self, threshold: int | None = None) -> None:
        self.threshold = threshold

    def format(
        self, amount: AnyValue, network: EthereumNetworkInfo, token: EthereumTokenInfo
    ) -> str | None:
        if amount is None:
            return None
        else:
            if not isinstance(amount, int):
                raise InvalidFormatDefinition
            if self.threshold is not None and amount > self.threshold:
                # TODO: figure out a way for the formatter to signal that the amount was above the threshold.
                # For now we return None and `confirm_ethereum_approve` shows the "Unlimited amount" warning,
                # but the `tokenAmount` spec allows this message to be customized in which case
                # being above the threshold could mean something else, not just "Unlimited".
                return None
            return format_ethereum_amount(amount, token, network)


class UnitFormatter(FieldFormatter):
    def __init__(self, decimals: int = 0, base: str = "", prefix: bool = False) -> None:
        self.decimals = decimals
        self.base = base
        self.prefix = prefix

    def format(
        self, value: AnyValue, network: EthereumNetworkInfo, token: EthereumTokenInfo
    ) -> str | None:
        if value is None:
            return None
        else:
            if not isinstance(value, int):
                raise InvalidFormatDefinition

            scaled_value = value / (10**self.decimals)

            if not self.prefix or scaled_value == 0:
                return f"{scaled_value:g}{self.base}"

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

            return f"{significand:g}{prefix_symbol}{self.base}"


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


class Struct(ABIValue):
    """Structs (or Tuples, which are essentially the same thing as far as ABI is concerned)
    contain multiple values of different types.
    A Struct is "dynamic" if at least one of the values is dynamic.
    However, dynamic structs inside arrays behave as static structs,
    hence we cannot guess if the Struct is dynamic by looking at just its fields."""

    def __init__(self, fields: tuple[Parser, ...], is_dynamic: bool) -> None:
        self.fields = fields
        self.is_dynamic = is_dynamic
        self.static_size = len(fields) * 32

    def parse(self, raw_data: memoryview, offset: int) -> tuple[StructValue, int]:
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
                    # Struct or Array inside a Struct
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
                    # Struct or Array inside a Struct
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


class ContainerPath:
    From = 1
    Value = 2
    To = 3
    ChainID = 4


class FieldDefinition:
    def __init__(
        self,
        path: tuple[int, ...] | int,
        label: str,
        formatter: FieldFormatter | type[FieldFormatter],
    ) -> None:
        self.path = path
        self.label = label
        self.formatter = formatter

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


class ParsingContext:
    def __init__(self, display_format: DisplayFormat) -> None:
        self.data = bytes()
        self.display_format = display_format
        self.truncated = False

    def process_data_chunk(self, offset: int, chunk: memoryview) -> None:
        if offset == 0:
            # skip function signature
            chunk = chunk[SC_FUNC_SIG_BYTES:]

        if not chunk:
            # nothing to process after skipping function signature
            return

        current_len = len(self.data)
        if current_len >= MAX_CALLDATA_STORED:
            self.truncated = True
            # reached the storage limit. ignore further chunks.
            return

        remaining = MAX_CALLDATA_STORED - current_len
        if len(chunk) > remaining:
            self.truncated = True
            chunk = chunk[:remaining]
        if chunk:
            self.data += bytes(chunk)

    def get_parameters_and_fields(
        self,
        address_n: list[int],
        tx_value: AnyBytes,
        network: EthereumNetworkInfo,
        token: EthereumTokenInfo,
    ) -> tuple[list[AnyValue], list[StrPropertyType]]:
        if self.truncated:
            # this will not happen, because we already checked the data_length
            # in the very beginning and bailed from clear signing
            raise OutOfBounds

        parameters: list[AnyValue] = []

        data = memoryview(self.data)
        offset = 0
        for parameter_definition in self.display_format.parameter_definitions:
            value, consumed = parameter_definition.parse(data, offset)
            parameters.append(value)
            offset += consumed

        fields = []
        for field_definition in self.display_format.field_definitions:
            path = field_definition.path
            if isinstance(path, int):  # ContainerPath
                # standard container paths like @.from, @.value...
                if path == ContainerPath.From:
                    account, _ = get_account_and_path(address_n)
                    p = account
                elif path == ContainerPath.Value:
                    p = int.from_bytes(tx_value, "big")
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
                    if isinstance(p, (list, tuple)):
                        # walk inside Arrays or Structs
                        try:
                            p = p[step]
                        except (IndexError, TypeError):
                            raise InvalidFormatDefinition
                    else:
                        # can't walk inside basic types
                        raise InvalidFormatDefinition
                if isinstance(p, (list, tuple)):
                    # at the end of the path, we must have arrived somewhere
                    # ie. not on an Array or Struct
                    raise InvalidFormatDefinition
            fields.append(
                (
                    field_definition.label,
                    field_definition.get_formatter().format(p, network, token),
                    None,
                )
            )

        return parameters, fields


def get_approver(
    msg: MsgInSignTx,
    definitions: Definitions,
    address_bytes: bytes,
    value: int,
    maximum_fee: str,
    fee_items: Iterable[StrPropertyType],
) -> tuple[ConfirmDataFn, Coroutine[Any, Any, None]] | None:
    from .clear_signing_definitions import ALL_DISPLAY_FORMATS

    # local_cache_attribute
    chain_id = msg.chain_id
    network = definitions.network

    if not address_bytes:
        return None

    if msg.data_length > MAX_CALLDATA_STORED:
        # skip clear signing if the calldata is longer than what we can process
        return None

    data_reader = BufferReader(msg.data_initial_chunk)
    if data_reader.remaining_count() < SC_FUNC_SIG_BYTES:
        return None

    token = definitions.get_token(address_bytes)

    func_sig = data_reader.read_memoryview(SC_FUNC_SIG_BYTES)

    display_format = None
    for f in ALL_DISPLAY_FORMATS:
        if f.func_sig == func_sig:
            display_format = f
            break
    else:
        return None

    if not display_format.matches_context(chain_id, address_bytes):
        return None
    parser, parsing_context = _get_data_chunk_parser(display_format)

    return parser, _get_summary_handler(
        parsing_context, address_bytes, msg, network, token, maximum_fee, fee_items
    )


def _get_data_chunk_parser(
    display_format: DisplayFormat,
) -> tuple[ConfirmDataFn, ParsingContext]:
    offset = 0
    context = ParsingContext(display_format)

    async def confirm_fn(chunk: AnyBytes) -> None:
        nonlocal offset
        context.process_data_chunk(offset, memoryview(chunk))
        offset += len(chunk)

    return confirm_fn, context


def _get_summary_handler(
    context: ParsingContext,
    address_bytes: bytes,
    msg: MsgInSignTx,
    network: EthereumNetworkInfo,
    token: EthereumTokenInfo,
    maximum_fee: str,
    fee_items: Iterable[StrPropertyType],
) -> Coroutine[Any, Any, None]:
    from .clear_signing_definitions import (
        APPROVE_DISPLAY_FORMAT,
        TRANSFER_DISPLAY_FORMAT,
    )

    # custom treatment of certain functions (APPROVE, TRANSFER)

    if context.display_format.func_sig == APPROVE_DISPLAY_FORMAT.func_sig:
        return _handle_approve(
            context,
            address_bytes,
            msg,
            network,
            token,
            maximum_fee,
            fee_items,
        )
    elif context.display_format.func_sig == TRANSFER_DISPLAY_FORMAT.func_sig:
        return _handle_transfer(
            context,
            address_bytes,
            msg,
            network,
            token,
            maximum_fee,
            fee_items,
        )

    # generic UI for any function that has a `DisplayFormat`

    return _handle_generic_ui(context, msg, network, address_bytes, token)


async def _handle_approve(
    context: ParsingContext,
    address_bytes: bytes,
    msg: MsgInSignTx,
    network: EthereumNetworkInfo,
    token: EthereumTokenInfo,
    maximum_fee: str,
    fee_items: Iterable[StrPropertyType],
) -> None:
    from .clear_signing_definitions import (
        KNOWN_ADDRESSES,
        SC_FUNC_APPROVE_REVOKE_AMOUNT,
    )
    from .layout import require_confirm_approve

    args, fields = context.get_parameters_and_fields(
        msg.address_n, msg.value, network, token
    )

    assert len(args) == 2
    assert len(fields) == 2

    arg0_raw_value = args[0]
    (field0_name, recipient_addr, _) = fields[0]
    assert field0_name == "Spender"
    assert isinstance(arg0_raw_value, bytes)
    assert isinstance(recipient_addr, str)

    arg1_raw_value = args[1]
    (field1_name, value, _) = fields[1]
    assert field1_name == "Amount"
    assert isinstance(arg1_raw_value, int)

    recipient_str = KNOWN_ADDRESSES.get(arg0_raw_value)

    is_revoke = arg1_raw_value == SC_FUNC_APPROVE_REVOKE_AMOUNT

    await require_confirm_approve(
        recipient_addr,
        value,
        recipient_str,
        msg.address_n,
        maximum_fee,
        fee_items,
        msg.chain_id,
        network,
        token,
        address_bytes,
        is_revoke,
        bool(msg.chunkify),
    )


async def _handle_transfer(
    context: ParsingContext,
    address_bytes: bytes,
    msg: MsgInSignTx,
    network: EthereumNetworkInfo,
    token: EthereumTokenInfo,
    maximum_fee: str,
    fee_items: Iterable[StrPropertyType],
) -> None:
    from .layout import require_confirm_tx

    args, fields = context.get_parameters_and_fields(
        msg.address_n, msg.value, network, token
    )

    assert len(args) == 2
    assert len(fields) == 2

    (arg0_name, recipient_addr, _) = fields[0]
    assert arg0_name == "To"
    assert isinstance(recipient_addr, str)

    (arg1_name, value, _) = fields[1]
    assert arg1_name == "Amount"
    assert isinstance(value, str)

    await require_confirm_tx(
        recipient_addr,
        value,
        address_bytes,
        msg.address_n,
        maximum_fee,
        fee_items,
        token,
        is_send=True,
        chunkify=bool(msg.chunkify),
    )


async def _handle_generic_ui(
    context: ParsingContext,
    msg: MsgInSignTx,
    network: EthereumNetworkInfo,
    address_bytes: bytes,
    token: EthereumTokenInfo,
) -> None:
    from trezor.ui.layouts import (
        confirm_action,
        confirm_properties,
        ethereum_address_title,
    )

    from . import tokens
    from .clear_signing_definitions import KNOWN_ADDRESSES
    from .helpers import bytes_from_address
    from .layout import require_confirm_address, require_confirm_unknown_token

    _, fields = context.get_parameters_and_fields(
        msg.address_n, msg.value, network, token
    )
    if token is tokens.UNKNOWN_TOKEN:
        title = ethereum_address_title()
        await require_confirm_unknown_token(title)
        await require_confirm_address(
            address_bytes,
            title,
            TR.ethereum__token_contract,
            TR.buttons__continue,
            "unknown_token",
            TR.ethereum__unknown_contract_address,
        )

    # TODO ??
    recipient_str = KNOWN_ADDRESSES.get(bytes_from_address(msg.to))

    await confirm_action("confirm_contract", "Provider", recipient_str)
    await confirm_action("confirm_contract", "Intent", context.display_format.intent)
    await confirm_properties(
        "confirm_contract",
        "Confirm contract",
        fields,
    )
