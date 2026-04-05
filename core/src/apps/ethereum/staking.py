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


FUNC_SIG_STAKE = unhexlify("3a29dbae")
FUNC_SIG_UNSTAKE = unhexlify("76ec871c")
FUNC_SIG_CLAIM = unhexlify("33986ffa")

# addresses for pool (stake/unstake) and accounting (claim) operations
ADDRESSES_POOL = (
    unhexlify("AFA848357154a6a624686b348303EF9a13F63264"),  # Hoodi testnet
    unhexlify("D523794C879D9eC028960a231F866758e405bE34"),  # mainnet
)
ADDRESSES_ACCOUNTING = (
    unhexlify("624087DD1904ab122A32878Ce9e933C7071F53B9"),  # Hoodi testnet
    unhexlify("7a7f0b3c23C23a31cFcb0c44709be70d4D545c6e"),  # mainnet
)


def get_approver(
    msg: MsgInSignTx,
    network: EthereumNetworkInfo,
    address_bytes: bytes,
    maximum_fee: str,
    fee_items: Iterable[StrPropertyType],
) -> tuple[ConfirmDataFn, Coroutine[Any, Any, None]] | None:
    """
    Returns a awaitable confirmation for ETH staking approval.

    `None` is returned for non-staking related transactions.
    """

    from .clear_signing import SC_FUNC_SIG_BYTES
    from .helpers import get_progress_indicator

    # local_cache_attribute
    data_length = msg.data_length

    if data_length > len(msg.data_initial_chunk):
        return None

    data_reader = BufferReader(msg.data_initial_chunk)
    if data_reader.remaining_count() < SC_FUNC_SIG_BYTES:
        return None

    func_sig = data_reader.read_memoryview(SC_FUNC_SIG_BYTES)
    if address_bytes in ADDRESSES_POOL:
        if func_sig == FUNC_SIG_STAKE:
            return get_progress_indicator(data_length), _handle_staking_tx_stake(
                data_reader, msg, network, address_bytes, maximum_fee, fee_items
            )
        if func_sig == FUNC_SIG_UNSTAKE:
            return get_progress_indicator(data_length), _handle_staking_tx_unstake(
                data_reader, msg, network, address_bytes, maximum_fee, fee_items
            )

    if address_bytes in ADDRESSES_ACCOUNTING:
        if func_sig == FUNC_SIG_CLAIM:
            return get_progress_indicator(data_length), _handle_staking_tx_claim(
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

    # claim has no args
    if data_reader.remaining_count() != 0:
        raise DataError("Invalid staking transaction call")

    await require_confirm_claim(
        staking_addr, msg.address_n, maximum_fee, fee_items, network, chunkify
    )
