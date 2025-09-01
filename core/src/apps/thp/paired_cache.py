from micropython import const

from trezor.messages import ThpPairedCache, ThpPairedCacheEntry

_ENABLE_EXPERIMENTAL = const(False)


def load() -> list[ThpPairedCacheEntry]:
    """Load THP paired entries from flash."""
    from storage.device import get_thp_paired_cache
    from trezor.protobuf import decode

    if (blob := get_thp_paired_cache()) is None:
        return []  # an empty cache

    cache = decode(blob, ThpPairedCache, _ENABLE_EXPERIMENTAL)
    return cache.entries


def store(entries: list[ThpPairedCacheEntry], _bonds: set[bytes] | None = None) -> None:
    """Store THP paired entries to flash."""
    from storage.device import set_thp_paired_cache
    from trezor.protobuf import dump_message_buffer

    if _bonds is None:
        from trezorble import get_bonds

        _bonds = set(get_bonds())

    # Remove entries with unbonded MAC addresses
    entries = [e for e in entries if e.mac_addr in _bonds]

    cache = ThpPairedCache(entries=entries)
    set_thp_paired_cache(dump_message_buffer(cache))
