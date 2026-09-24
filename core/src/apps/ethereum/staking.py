from typing import TYPE_CHECKING

from trezor.utils import BufferReader
from trezor.wire import DataError

from .sc_constants import STAKING_ADDRESSES_ACCOUNTING, STAKING_ADDRESSES_POOL

if TYPE_CHECKING:
    from collections.abc import Coroutine, Iterable
    from typing import Any

    from trezor.messages import EthereumNetworkInfo
    from trezor.ui.layouts import StrPropertyType

    from .keychain import MsgInSignTx


FUNC_SIG_STAKE = b"\x3a\x29\xdb\xae"
FUNC_SIG_UNSTAKE = b"\x76\xec\x87\x1c"
FUNC_SIG_CLAIM = b"\x33\x98\x6f\xfa"


def get_approver(
    msg: MsgInSignTx,
    network: EthereumNetworkInfo,
    address_bytes: bytes,
    maximum_fee: str,
    fee_items: Iterable[StrPropertyType],
) -> Coroutine[Any, Any, None] | None:
    """
    Returns a awaitable confirmation for ETH staking approval.

    `None` is returned for non-staking related transactions.
    """

    from .clear_signing import SC_FUNC_SIG_BYTES

    # local_cache_attribute
    data_length = msg.data_length

    if data_length > len(msg.data_initial_chunk):
        return None

    # No more data should be loaded from host:
    data_reader = BufferReader(msg.data_initial_chunk)
    if data_reader.remaining_count() < SC_FUNC_SIG_BYTES:
        return None

    func_sig = data_reader.read_memoryview(SC_FUNC_SIG_BYTES)
    if (network.chain_id, address_bytes) in STAKING_ADDRESSES_POOL:
        if func_sig == FUNC_SIG_STAKE:
            return _handle_staking_tx_stake(
                data_reader, msg, network, address_bytes, maximum_fee, fee_items
            )
        if func_sig == FUNC_SIG_UNSTAKE:
            return _handle_staking_tx_unstake(
                data_reader, msg, network, address_bytes, maximum_fee, fee_items
            )

    if (network.chain_id, address_bytes) in STAKING_ADDRESSES_ACCOUNTING:
        if func_sig == FUNC_SIG_CLAIM:
            return _handle_staking_tx_claim(
                data_reader,
                msg,
                address_bytes,
                maximum_fee,
                fee_items,
                network,
                bool(msg.chunkify),
            )

    # data not corresponding to staking transaction
    return None


async def _handle_staking_tx_stake(
    data_reader: BufferReader,
    msg: MsgInSignTx,
    network: EthereumNetworkInfo,
    address_bytes: bytes,
    maximum_fee: str,
    fee_items: Iterable[StrPropertyType],
) -> None:
    from .layout import require_confirm_stake

    # stake args:
    # - arg0: uint64, source (1 for Trezor)
    try:
        _ = data_reader.read_memoryview(32)  # skip arg0
        if data_reader.remaining_count() != 0:
            raise ValueError  # wrong number of arguments for stake (should be 1)
    except (ValueError, EOFError):
        raise DataError("Invalid staking transaction call")

    await require_confirm_stake(
        address_bytes,
        int.from_bytes(msg.value, "big"),
        msg.address_n,
        maximum_fee,
        fee_items,
        network,
        bool(msg.chunkify),
    )


async def _handle_staking_tx_unstake(
    data_reader: BufferReader,
    msg: MsgInSignTx,
    network: EthereumNetworkInfo,
    address_bytes: bytes,
    maximum_fee: str,
    fee_items: Iterable[StrPropertyType],
) -> None:
    from .layout import require_confirm_unstake

    # unstake args:
    # - arg0: uint256, value
    # - arg1: uint16, isAllowedInterchange (bool)
    # - arg2: uint64, source (1 for Trezor)
    try:
        value = int.from_bytes(data_reader.read_memoryview(32), "big")  # parse arg0
        _ = data_reader.read_memoryview(32)  # skip arg1
        _ = data_reader.read_memoryview(32)  # skip arg2
        if data_reader.remaining_count() != 0:
            raise ValueError  # wrong number of arguments for unstake (should be 3)
        if int.from_bytes(msg.value, "big") != 0:
            raise ValueError  # unstake is non-payable
    except (ValueError, EOFError):
        raise DataError("Invalid staking transaction call")

    await require_confirm_unstake(
        address_bytes,
        value,
        msg.address_n,
        maximum_fee,
        fee_items,
        network,
        bool(msg.chunkify),
    )


async def _handle_staking_tx_claim(
    data_reader: BufferReader,
    msg: MsgInSignTx,
    staking_addr: bytes,
    maximum_fee: str,
    fee_items: Iterable[StrPropertyType],
    network: EthereumNetworkInfo,
    chunkify: bool,
) -> None:
    from .layout import require_confirm_claim

    # claim has no args and is non-payable
    if data_reader.remaining_count() != 0 or int.from_bytes(msg.value, "big") != 0:
        raise DataError("Invalid staking transaction call")

    await require_confirm_claim(
        staking_addr, msg.address_n, maximum_fee, fee_items, network, chunkify
    )
