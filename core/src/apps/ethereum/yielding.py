from typing import TYPE_CHECKING
from ubinascii import unhexlify

from trezor.utils import BufferReader
from trezor.wire import DataError

if TYPE_CHECKING:
    from typing import Any, Coroutine, Iterable

    from trezor.messages import EthereumNetworkInfo
    from trezor.ui.layouts import StrPropertyType

    from .helpers import ConfirmDataFn
    from .keychain import MsgInSignTx


FUNC_SIG_DEPOSIT = unhexlify("6e553f65")


def get_approver(
    msg: MsgInSignTx,
    network: EthereumNetworkInfo,
    address_bytes: bytes,
    maximum_fee: str,
    fee_items: Iterable[StrPropertyType],
    sender_bytes: bytes,
) -> tuple[ConfirmDataFn, Coroutine[Any, Any, None]] | None:

    from .clear_signing import SC_FUNC_SIG_BYTES
    from .clear_signing_definitions import VAULT_GAUNTLET_USDC
    from .helpers import get_progress_indicator

    if msg.data_length > len(msg.data_initial_chunk):
        return None

    data_reader = BufferReader(msg.data_initial_chunk)
    if data_reader.remaining_count() < SC_FUNC_SIG_BYTES:
        return None

    func_sig = data_reader.read_memoryview(SC_FUNC_SIG_BYTES)
    # We restrict the flow to only the known vault address.
    # Thus, the address won't be required hereafter.
    if address_bytes == VAULT_GAUNTLET_USDC[0] and func_sig == FUNC_SIG_DEPOSIT:
        return get_progress_indicator(msg.data_length), _handle_deposit(
            data_reader,
            msg,
            network,
            maximum_fee,
            fee_items,
            sender_bytes,
        )

    return None


async def _handle_deposit(
    data_reader: BufferReader,
    msg: MsgInSignTx,
    network: EthereumNetworkInfo,
    maximum_fee: str,
    fee_items: Iterable[StrPropertyType],
    sender_bytes: bytes,
) -> None:

    from .layout import require_confirm_deposit

    # deposit(uint256 assets, address receiver)
    # - arg0: uint256 assets (32 bytes, big-endian)
    # - arg1: address receiver (32 bytes, address in last 20 bytes)
    try:
        asset_amount = int.from_bytes(
            data_reader.read_memoryview(32), "big"
        )  # parse arg0
        receiver_bytes = bytes(
            data_reader.read_memoryview(32)[12:]
        )  # parse arg1, last 20 bytes
        if data_reader.remaining_count() != 0:
            raise ValueError  # wrong number of arguments
    except (ValueError, EOFError):
        raise DataError("Invalid data for deposit transaction")

    if asset_amount == 0:
        raise DataError("Invalid assets amount for deposit")
    if receiver_bytes != sender_bytes:
        raise DataError("Receiver must equal sender for deposit")

    await require_confirm_deposit(
        asset_amount,
        msg.address_n,
        maximum_fee,
        fee_items,
        network,
    )
