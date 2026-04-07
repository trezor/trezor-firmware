from micropython import const
from typing import TYPE_CHECKING

from trezor.messages import ThpPairedCache, ThpPairedCacheEntry

if __debug__:
    from trezor import log, utils

if TYPE_CHECKING:
    from buffer_types import AnyBytes

_ENABLE_EXPERIMENTAL = const(False)


def load() -> list[ThpPairedCacheEntry]:
    """Load THP paired entries from flash."""
    from storage.device import get_thp_paired_names
    from trezor.protobuf import decode

    if (blob := get_thp_paired_names()) is None:
        return []  # an empty cache

    cache = decode(blob, ThpPairedCache, _ENABLE_EXPERIMENTAL)
    if __debug__:
        log.debug(__name__, "loaded THP cache:\n%s", utils.dump_protobuf(cache))

    return cache.entries


def store(entries: list[ThpPairedCacheEntry], _bonds: set[bytes] | None = None) -> None:
    """Store THP paired entries to flash."""
    from storage.device import set_thp_paired_names
    from trezor.protobuf import dump_message_buffer

    if _bonds is None:
        from trezorble import get_bonds

        _bonds = set(get_bonds())

    # Remove entries with unbonded MAC addresses
    entries = [e for e in entries if e.mac_addr in _bonds]

    cache = ThpPairedCache(entries=entries)
    if __debug__:
        log.debug(__name__, "storing THP cache:\n%s", utils.dump_protobuf(cache))

    set_thp_paired_names(dump_message_buffer(cache))


def cache_host_info(mac_addr: AnyBytes | None, host_name: str, app_name: str) -> None:
    if mac_addr is None:
        if __debug__:
            log.debug(__name__, "no MAC address: host=%s app=%s", host_name, app_name)
        return

    from trezor.messages import ThpPairedCacheEntry
    from trezor.strings import trim_str

    entries = load()
    for e in entries:
        if mac_addr == e.mac_addr:
            if __debug__:
                log.debug(
                    __name__,
                    "found cached MAC %s:\n%s",
                    mac_addr,
                    utils.dump_protobuf(e),
                )
            # skip writing to flash if this MAC address is already cached
            return

    host_name = trim_str(host_name, max_bytes=32)
    app_name = trim_str(app_name, max_bytes=32)
    entries.append(
        ThpPairedCacheEntry(mac_addr=mac_addr, host_name=host_name, app_name=app_name)
    )
    store(entries)
