from micropython import const
from typing import TYPE_CHECKING

from trezor import TR

from .helpers import address_from_bytes, format_ethereum_amount, get_account_and_path

if TYPE_CHECKING:
    from buffer_types import AnyBytes
    from typing import Callable, Iterable

    from trezor.messages import EthereumTokenInfo
    from trezor.ui.layouts import StrPropertyType

    from apps.common.payment_request import PaymentRequestVerifier

    from .definitions import Definitions
    from .keychain import MsgInSignTx

    # Represents values that have been parsed from the calldata
    # into our internal representation.
    Value = int | bytes | bool | str | None | list["Value"]
    StructValue = tuple[Value, ...]
    ListValue = list[StructValue]
    AnyValue = Value | StructValue | ListValue | list[Value | StructValue | ListValue]

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
        self,
        value: AnyValue,
        definitions: Definitions,
        token: EthereumTokenInfo,
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
    def format(
        self,
        address: AnyValue,
        definitions: Definitions,
        _token: EthereumTokenInfo,
        _path_walker: PathWalker,
    ) -> tuple[str | None, EthereumTokenInfo | None, AnyBytes | None]:
        if address is None:
            return None, None, None
        elif isinstance(address, str):
            return address, None, None
        else:
            if not isinstance(address, bytes):
                raise InvalidFormatDefinition
            return address_from_bytes(address, definitions.network), None, None


class AmountFormatter(FieldFormatter):
    def format(
        self,
        amount: AnyValue,
        definitions: Definitions,
        _token: EthereumTokenInfo,
        _path_Walker: PathWalker,
    ) -> tuple[str | None, EthereumTokenInfo | None, AnyBytes | None]:
        if amount is None:
            return None, None, None
        else:
            if not isinstance(amount, int):
                raise InvalidFormatDefinition

            # Note: we are passing None rather than `_token`
            # to `format_ethereum_amount` because this formatter
            # is meant to be used with native ETH amounts
            return format_ethereum_amount(amount, None, definitions.network), None, None


class TokenAmountFormatter(FieldFormatter):
    def __init__(
        self,
        token_path: Path | None = None,
        native_currency_address: list[bytes] | None = None,
        threshold: int | None = None,
    ) -> None:
        self.token_path = token_path
        self.native_currency_address = native_currency_address
        self.threshold = threshold

    def format(
        self,
        amount: AnyValue,
        definitions: Definitions,
        token: EthereumTokenInfo | None,
        path_walker: PathWalker,
    ) -> tuple[str | None, EthereumTokenInfo | None, AnyBytes | None]:
        if amount is None:
            return None, None, None
        else:
            if not isinstance(amount, int):
                raise InvalidFormatDefinition
            if self.threshold is not None and amount > self.threshold:
                # TODO: figure out a way for the formatter to signal that the amount was above the threshold.
                # For now we return None and `confirm_ethereum_approve` shows the "Unlimited amount" warning,
                # but the `tokenAmount` spec allows this message to be customized in which case
                # being above the threshold could mean something else, not just "Unlimited".
                return None, None, None
            if self.token_path is not None:
                token_address = path_walker(self.token_path)
                if not isinstance(token_address, bytes):
                    raise InvalidFormatDefinition
                is_native_currency = False
                if self.native_currency_address is not None:
                    if token_address in self.native_currency_address:
                        is_native_currency = True
                token = (
                    definitions.get_token(token_address)
                    if not is_native_currency
                    else None
                )
                return (
                    format_ethereum_amount(amount, token, definitions.network),
                    token,
                    token_address if not is_native_currency else None,
                )
            return (
                format_ethereum_amount(amount, token, definitions.network),
                token,
                token.address if token else None,
            )


class UnitFormatter(FieldFormatter):
    def __init__(self, decimals: int = 0, base: str = "", prefix: bool = False) -> None:
        self.decimals = decimals
        self.base = base
        self.prefix = prefix

    def format(
        self,
        value: AnyValue,
        _definitions: Definitions,
        _token: EthereumTokenInfo,
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
        path: Path,
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

    def parse(
        self,
        calldata: memoryview,
        address_n: list[int],
        tx_value: AnyBytes,
        definitions: Definitions,
        token: EthereumTokenInfo,
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
                    account, _ = get_account_and_path(address_n)
                    return account
                elif path == ContainerPath.Value:
                    return int.from_bytes(tx_value, "big")
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
                        # walk inside Arrays or Structs
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
                    # ie. not on an Array or Struct
                    raise InvalidFormatDefinition
                return p

        fields: list[
            tuple[StrPropertyType, EthereumTokenInfo | None, AnyBytes | None]
        ] = []
        for field_definition in self.field_definitions:
            (
                formatted_value,
                actual_token,
                actual_token_address,
            ) = field_definition.get_formatter().format(
                get_value_for_path(field_definition.path),
                definitions,
                token,
                get_value_for_path,
            )
            fields.append(
                (
                    (
                        field_definition.label,
                        formatted_value,
                        None,
                    ),
                    actual_token,
                    actual_token_address,
                )
            )

        return parameters, fields


async def try_parse(
    data: AnyBytes,
    address_bytes: bytes,
    msg: MsgInSignTx,
    definitions: Definitions,
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

    func_sig = data[0:SC_FUNC_SIG_BYTES]

    display_format = None
    for f in ALL_DISPLAY_FORMATS:
        if f.func_sig == func_sig:
            display_format = f
            break
    else:
        return False

    if not display_format.matches_context(msg.chain_id, address_bytes):
        return False

    calldata = memoryview(data)[SC_FUNC_SIG_BYTES:]
    token = definitions.get_token(address_bytes)

    # custom treatment of certain functions (APPROVE, TRANSFER)
    if display_format.func_sig == APPROVE_DISPLAY_FORMAT.func_sig:
        await _handle_approve(
            calldata,
            display_format,
            address_bytes,
            msg,
            definitions,
            token,
            maximum_fee,
            fee_items,
        )
    elif display_format.func_sig == TRANSFER_DISPLAY_FORMAT.func_sig:
        await _handle_transfer(
            calldata,
            display_format,
            address_bytes,
            msg,
            definitions,
            token,
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
            definitions,
            token,
            maximum_fee,
        )
    return True


async def _handle_approve(
    calldata: memoryview,
    display_format: DisplayFormat,
    address_bytes: bytes,
    msg: MsgInSignTx,
    definitions: Definitions,
    token: EthereumTokenInfo,
    maximum_fee: str,
    fee_items: Iterable[StrPropertyType],
) -> None:
    from .clear_signing_definitions import SC_FUNC_APPROVE_REVOKE_AMOUNT
    from .layout import require_confirm_approve
    from .sc_constants import KNOWN_ADDRESSES

    args, fields = display_format.parse(
        calldata, msg.address_n, msg.value, definitions, token
    )

    assert len(args) == 2
    assert len(fields) == 2

    arg0_raw_value = args[0]
    (field0_name, recipient_addr, _), _, _ = fields[0]
    assert field0_name == "Spender"
    assert isinstance(arg0_raw_value, bytes)
    assert isinstance(recipient_addr, str)

    arg1_raw_value = args[1]
    (field1_name, value, _), _, _ = fields[1]
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
        definitions.network,
        token,
        address_bytes,
        is_revoke,
        bool(msg.chunkify),
    )


async def _handle_transfer(
    calldata: memoryview,
    display_format: DisplayFormat,
    address_bytes: bytes,
    msg: MsgInSignTx,
    definitions: Definitions,
    token: EthereumTokenInfo,
    maximum_fee: str,
    fee_items: Iterable[StrPropertyType],
    payment_request_verifier: PaymentRequestVerifier | None,
) -> None:
    from .layout import require_confirm_payment_request, require_confirm_tx

    args, fields = display_format.parse(
        calldata, msg.address_n, msg.value, definitions, token
    )

    assert len(args) == 2
    assert len(fields) == 2

    (arg0_name, recipient_addr, _), _, _ = fields[0]
    assert arg0_name == "To"
    assert isinstance(recipient_addr, str)

    arg1_raw_value = args[1]
    assert isinstance(arg1_raw_value, int)
    (arg1_name, value, _), _, _ = fields[1]
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
            definitions.network,
            token,
            address_from_bytes(address_bytes, definitions.network),
        )
    else:
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
    calldata: memoryview,
    display_format: DisplayFormat,
    msg: MsgInSignTx,
    definitions: Definitions,
    token: EthereumTokenInfo,
    maximum_fee: str,
) -> None:
    from . import tokens
    from .helpers import bytes_from_address
    from .layout import require_confirm_clear_signing
    from .sc_constants import KNOWN_ADDRESSES

    _, fields = display_format.parse(
        calldata, msg.address_n, msg.value, definitions, token
    )

    properties_to_confirm = []

    for field, actual_token, actual_token_address in fields:
        properties_to_confirm.append(field)
        if actual_token is tokens.UNKNOWN_TOKEN:
            assert actual_token_address is not None
            token_address_str = address_from_bytes(
                actual_token_address, definitions.network
            )
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
