from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import (
        MoneroAccountPublicAddress,
        MoneroTransactionDestinationEntry,
    )


def encode_addr(
    version, spend_pub: bytes, view_pub: bytes, payment_id: bytes | None = None
) -> str:
    """
    Builds Monero address from public keys
    """
    from trezor.crypto import monero as tcry

    buf = spend_pub + view_pub
    if payment_id:
        buf += bytes(payment_id)
    return tcry.xmr_base58_addr_encode_check(ord(version), bytes(buf))


def classify_subaddresses(
    tx_dests: list[MoneroTransactionDestinationEntry],
    change_addr: MoneroAccountPublicAddress,
) -> tuple[int, int, MoneroAccountPublicAddress | None]:
    """
    Classify destination subaddresses
    """
    num_stdaddresses = 0
    num_subaddresses = 0
    single_dest_subaddress: MoneroAccountPublicAddress | None = None
    addr_set = set()
    for tx in tx_dests:
        addr = tx.addr  # local_cache_attribute
        if change_addr and addr_eq(change_addr, addr):
            continue
        # addr_to_hash
        # Creates hashable address representation
        addr_hashed = bytes(addr.spend_public_key + addr.view_public_key)
        if addr_hashed in addr_set:
            continue
        addr_set.add(addr_hashed)
        if tx.is_subaddress:
            num_subaddresses += 1
            single_dest_subaddress = addr
        else:
            num_stdaddresses += 1
    return num_stdaddresses, num_subaddresses, single_dest_subaddress


def addr_eq(a: MoneroAccountPublicAddress, b: MoneroAccountPublicAddress) -> bool:
    return (
        a.spend_public_key == b.spend_public_key
        and a.view_public_key == b.view_public_key
    )


def get_change_addr_idx(
    outputs: list[MoneroTransactionDestinationEntry],
    change_dts: MoneroTransactionDestinationEntry | None,
) -> int | None:
    """
    Returns ID of the change output from the change_dts and outputs
    """
    if change_dts is None:
        return None

    change_idx = None
    for idx, dst in enumerate(outputs):
        if (
            change_dts.amount
            and change_dts.amount == dst.amount
            and addr_eq(change_dts.addr, dst.addr)
        ):
            change_idx = idx
    return change_idx
