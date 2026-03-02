from micropython import const
from typing import TYPE_CHECKING

from trezor import TR
from trezor.crypto import base58
from trezor.utils import BufferReader

from apps.ethereum import clear_signing_constants as constants

from .helpers import address_from_bytes, format_ethereum_amount

if TYPE_CHECKING:
    from typing import Any, Callable, Coroutine, Iterable

    from trezor.messages import EthereumNetworkInfo, EthereumTokenInfo
    from trezor.ui.layouts import StrPropertyType

    from .definitions import Definitions
    from .keychain import MsgInSignTx

    Value = int | bytes | None
    FieldParser = Callable[[memoryview], Value]
    FieldFormatter = Callable[
        [Value, EthereumNetworkInfo, EthereumTokenInfo], str | None
    ]


class InvalidFunctionCall(Exception):
    pass


# field types - can be any Solidity type - currently just address and uint256


def parse_address(arg: memoryview) -> Value:
    from .sc_constants import SC_ARGUMENT_ADDRESS_BYTES, SC_ARGUMENT_BYTES

    if any(byte != 0 for byte in arg[: SC_ARGUMENT_BYTES - SC_ARGUMENT_ADDRESS_BYTES]):
        raise InvalidFunctionCall

    return bytes(arg[SC_ARGUMENT_BYTES - SC_ARGUMENT_ADDRESS_BYTES :])


def parse_uint256(arg: memoryview) -> Value:
    return int.from_bytes(arg, "big")


# field formatters: https://eips.ethereum.org/EIPS/eip-7730#field-formats


def format_address_name(
    address: Value, network: EthereumNetworkInfo, _token: EthereumTokenInfo
) -> str | None:
    if address is None:
        return None
    else:
        assert isinstance(address, bytes)
        return address_from_bytes(address, network)


def get_token_amount_formatter(threshold: int | None = None) -> FieldFormatter:
    def format_token_amount(
        amount: Value, network: EthereumNetworkInfo, token: EthereumTokenInfo
    ) -> str | None:
        if amount is None:
            return None
        else:
            assert isinstance(amount, int)
            if threshold is not None and amount > threshold:
                # TODO: figure out a way for the formatter to signal that the amount was above the threshold.
                # For now we return None and `confirm_ethereum_approve` shows the "Unlimited amount" warning,
                # but the `tokenAmount` spec allows this message to be customized in which case
                # being above the threshold could mean something else, not just "Unlimited".
                return None
            return format_ethereum_amount(amount, token, network)

    return format_token_amount


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


class Field:
    def __init__(
        self,
        label: str | None,
        parser: FieldParser,
        formatter: FieldFormatter,
    ) -> None:
        self.label = label
        self.parser = parser
        self.formatter = formatter


class DisplayFormat:
    def __init__(
        self,
        binding_context: BindingContext | None,
        func_sig: bytes,
        intent: str,
        interpolated_intent: str | None,
        fields: list[Field],
    ) -> None:
        self.binding_context = binding_context
        self.func_sig = func_sig
        self.intent = intent
        self.interpolated_intent = interpolated_intent
        self.fields = fields

    def parse_fields(
        self,
        data_reader: BufferReader,
        network: EthereumNetworkInfo,
        token: EthereumTokenInfo,
    ) -> Iterable[tuple[Value, StrPropertyType]]:
        from .sc_constants import SC_ARGUMENT_BYTES

        for field in self.fields:
            if data_reader.remaining_count() < SC_ARGUMENT_BYTES:
                raise InvalidFunctionCall
            arg = data_reader.read_memoryview(SC_ARGUMENT_BYTES)
            value = field.parser(arg)
            yield (
                value,
                (
                    field.label,
                    field.formatter(value, network, token),
                    None,
                ),
            )
        if data_reader.remaining_count() > 0:
            raise InvalidFunctionCall

    def matches_context(self, chain_id: int, address: bytes) -> bool:
        if self.binding_context is None:
            return True

        return self.binding_context.matches(chain_id, address)


def get_approver(
    msg: MsgInSignTx,
    definitions: Definitions,
    address_bytes: bytes,
    value: int,
    maximum_fee: str,
    fee_items: Iterable[StrPropertyType],
) -> Coroutine[Any, Any, None] | None:
    from .sc_constants import SC_FUNC_SIG_BYTES

    # local_cache_attribute
    network = definitions.network
    chain_id = msg.chain_id

    if not address_bytes or value != 0:
        return None

    # only parse the initial chunk for now
    if msg.data_length != len(msg.data_initial_chunk):
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

    try:
        args = list(display_format.parse_fields(data_reader, network, token))
    except InvalidFunctionCall:
        return None

    # custom treatment of certain functions (APPROVE, TRANSFER)

    if func_sig == APPROVE_DISPLAY_FORMAT.func_sig:
        assert len(args) == 2

        (arg0_raw_value, (arg0_name, arg0_formatted_value, _)) = args[0]
        assert arg0_name == "Spender"
        assert isinstance(arg0_raw_value, bytes)
        assert isinstance(arg0_formatted_value, str)

        (arg1_raw_value, (arg1_name, arg1_formatted_value, _)) = args[1]
        assert arg1_name == "Amount"
        assert isinstance(arg1_raw_value, int)

        return _get_approve_handler(
            arg0_formatted_value,
            constants.KNOWN_ADDRESSES.get(arg0_raw_value),
            arg1_formatted_value,
            arg1_raw_value == SC_FUNC_APPROVE_REVOKE_AMOUNT,
            address_bytes,
            msg,
            network,
            token,
            maximum_fee,
            fee_items,
        )
    elif func_sig == TRANSFER_DISPLAY_FORMAT.func_sig:
        assert len(args) == 2
        (_, (arg0_name, arg0_formatted_value, _)) = args[0]
        assert arg0_name == "To"
        assert isinstance(arg0_formatted_value, str)

        (_, (arg1_name, arg1_formatted_value, _)) = args[1]
        assert arg1_name == "Amount"
        assert isinstance(arg1_formatted_value, str)

        return _get_transfer_handler(
            arg0_formatted_value,
            arg1_formatted_value,
            address_bytes,
            msg,
            token,
            maximum_fee,
            fee_items,
        )

    # generic UI for any function that has a `DisplayFormat`

    return _handle_generic_ui(display_format, args, address_bytes, token)


def _get_approve_handler(
    recipient_addr: str,
    recipient_str: str | None,
    value: str | None,
    is_revoke: bool,
    address_bytes: bytes,
    msg: MsgInSignTx,
    network: EthereumNetworkInfo,
    token: EthereumTokenInfo,
    maximum_fee: str,
    fee_items: Iterable[StrPropertyType],
) -> Coroutine[Any, Any, None] | None:
    from .layout import require_confirm_approve

    return require_confirm_approve(
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


def _get_transfer_handler(
    recipient_addr: str,
    value: str,
    address_bytes: bytes,
    msg: MsgInSignTx,
    token: EthereumTokenInfo,
    maximum_fee: str,
    fee_items: Iterable[StrPropertyType],
) -> Coroutine[Any, Any, None] | None:
    from .layout import require_confirm_tx

    return require_confirm_tx(
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
    f: DisplayFormat,
    args: list[tuple[Value, StrPropertyType]],
    address_bytes: bytes,
    token: EthereumTokenInfo,
) -> None:
    from trezor.ui.layouts import (
        confirm_action,
        confirm_properties,
        ethereum_address_title,
    )

    from . import tokens
    from .layout import require_confirm_address, require_confirm_unknown_token

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

    await confirm_action("confirm_contract", "Intent", f.intent)
    await confirm_properties(
        "confirm_contract",
        "Confirm contract",
        (field_display for (_, field_display) in args),
    )


# https://github.com/LedgerHQ/clear-signing-erc7730-registry/blob/master/ercs/calldata-erc20-tokens.json#L27

APPROVE_DISPLAY_FORMAT = DisplayFormat(
    binding_context=None,
    func_sig=base58.keccak_32(b"approve(address,uint256)"),
    intent="Approve",
    interpolated_intent=None,
    fields=[
        Field("Spender", parse_address, format_address_name),  # _spender
        Field(
            "Amount",
            parse_uint256,
            get_token_amount_formatter(
                threshold=0x8000000000000000000000000000000000000000000000000000000000000000
            ),  # _value
        ),
    ],
)
SC_FUNC_APPROVE_REVOKE_AMOUNT = const(0)

TRANSFER_DISPLAY_FORMAT = DisplayFormat(
    binding_context=None,
    func_sig=base58.keccak_32(b"transfer(address,uint256)"),
    intent="Send",
    interpolated_intent=None,
    fields=[
        Field("To", parse_address, format_address_name),  # _to
        Field("Amount", parse_uint256, get_token_amount_formatter()),  # _value
    ],
)

ALL_DISPLAY_FORMATS = [APPROVE_DISPLAY_FORMAT, TRANSFER_DISPLAY_FORMAT]
