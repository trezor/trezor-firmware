from typing import TYPE_CHECKING

from trezor.utils import BufferReader
from trezor.wire import DataError

if TYPE_CHECKING:
    from buffer_types import AnyBytes
    from typing import Any, Coroutine, Iterable

    from trezor.messages import EthereumNetworkInfo
    from trezor.ui.layouts import StrPropertyType

    from .helpers import ConfirmDataFn
    from .keychain import MsgInSignTx


def get_approver(
    msg: MsgInSignTx,
    network: EthereumNetworkInfo,
    address_bytes: AnyBytes,
    maximum_fee: str,
    fee_items: Iterable[StrPropertyType],
    sender_bytes: AnyBytes,
) -> tuple[ConfirmDataFn, Coroutine[Any, Any, None]] | None:

    from .clear_signing import SC_FUNC_SIG_BYTES
    from .helpers import get_progress_indicator

    # https://ethereum.org/developers/docs/standards/tokens/erc-4626/#deposit
    # keccak256("deposit(uint256,address)")[:4]
    FUNC_SIG_DEPOSIT = b"\x6e\x55\x3f\x65"

    if msg.data_length > len(msg.data_initial_chunk):
        return None

    data_reader = BufferReader(msg.data_initial_chunk)
    if data_reader.remaining_count() < SC_FUNC_SIG_BYTES:
        return None

    func_sig = data_reader.read_memoryview(SC_FUNC_SIG_BYTES)
    if func_sig == FUNC_SIG_DEPOSIT:
        return get_progress_indicator(msg.data_length), _handle_deposit(
            data_reader,
            msg,
            network,
            maximum_fee,
            fee_items,
            address_bytes,
            sender_bytes,
        )

    return None


async def _handle_deposit(
    data_reader: BufferReader,
    msg: MsgInSignTx,
    network: EthereumNetworkInfo,
    maximum_fee: str,
    fee_items: Iterable[StrPropertyType],
    vault_addr: AnyBytes,
    sender_bytes: AnyBytes,
) -> None:

    from .clear_signing import InvalidFunctionCall, parse_address, parse_uint256
    from .layout import require_confirm_deposit

    # deposit(uint256 assets, address receiver)
    # - arg0: asset(USDC) quantity
    # - arg1: user address
    try:
        asset_amount = parse_uint256(data_reader.read_memoryview(32))
        receiver_bytes = parse_address(data_reader.read_memoryview(32))
        if (
            data_reader.remaining_count() != 0
            or not isinstance(asset_amount, int)
            or not isinstance(receiver_bytes, bytes)
            or int.from_bytes(msg.value, "big") != 0
        ):
            raise ValueError
    except (ValueError, EOFError, InvalidFunctionCall):
        raise DataError("Invalid data for vault deposit")

    if asset_amount == 0:
        raise DataError("Invalid asset amount for vault deposit")

    if receiver_bytes != sender_bytes:
        raise DataError("Receiver must equal sender for vault deposit")

    await require_confirm_deposit(
        asset_amount,
        msg.address_n,
        maximum_fee,
        fee_items,
        network,
        vault_addr,
    )
