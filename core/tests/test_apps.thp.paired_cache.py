# flake8: noqa: F403,F405
from common import *  # isort: skip
from trezor import config, utils

if utils.USE_THP:
    from storage.device import get_thp_paired_cache
    from trezor.messages import ThpPairedCacheEntry

    from apps.thp import paired_cache

    ALL_ENTRIES = [
        ThpPairedCacheEntry(mac_addr=b"\x01\x02\x03\x04\x05\x06", host_name="First"),
        ThpPairedCacheEntry(mac_addr=b"\x11\x12\x13\x14\x15\x16", host_name="Second"),
        ThpPairedCacheEntry(mac_addr=b"\x21\x22\x23\x24\x25\x26", host_name="Third"),
        ThpPairedCacheEntry(mac_addr=b"\x31\x32\x33\x34\x35\x36", host_name="Fourth"),
        ThpPairedCacheEntry(mac_addr=b"\x41\x42\x43\x44\x45\x46", host_name="Fifth"),
        ThpPairedCacheEntry(mac_addr=b"\x51\x52\x53\x54\x55\x56", host_name="Sixth"),
        ThpPairedCacheEntry(mac_addr=b"\x61\x62\x63\x64\x65\x66", host_name="Seventh"),
        ThpPairedCacheEntry(mac_addr=b"\x71\x72\x73\x74\x75\x76", host_name="Eighth"),
    ]


@unittest.skipUnless(utils.USE_THP, "only needed for THP")
class TestTrezorHostProtocolPairedCache(unittest.TestCase):
    def setUp(self):
        config.init()
        config.wipe()

    def test_empty(self):
        self.assertEqual(paired_cache.load(), [])
        paired_cache.store(entries=[], _bonds=[])
        self.assertEqual(paired_cache.load(), [])

    def test_store_and_load(self):
        for i in range(len(ALL_ENTRIES)):
            entries = ALL_ENTRIES[: i + 1]
            bonds = {e.mac_addr for e in entries}
            paired_cache.store(entries=entries, _bonds=bonds)
            self.assertListEqual(paired_cache.load(), entries)

        paired_cache.store(entries=entries, _bonds=set())
        self.assertListEqual(paired_cache.load(), [])

    def test_store_no_bonds(self):
        for i in range(len(ALL_ENTRIES)):
            entries = ALL_ENTRIES[: i + 1]
            paired_cache.store(entries=entries, _bonds=[])
            self.assertListEqual(paired_cache.load(), [])

        paired_cache.store(entries=entries, _bonds=set())
        self.assertListEqual(paired_cache.load(), [])

    def test_store_less_bonds(self):
        for i in range(len(ALL_ENTRIES)):
            entries = ALL_ENTRIES[: i + 1]
            # last entry has no matching bond
            bonds = {e.mac_addr for e in entries[:-1]}
            paired_cache.store(entries=entries, _bonds=bonds)
            self.assertListEqual(paired_cache.load(), entries[:-1])

        paired_cache.store(entries=entries, _bonds=set())
        self.assertListEqual(paired_cache.load(), [])

    def test_store_more_bonds(self):
        for i in range(len(ALL_ENTRIES)):
            entries = ALL_ENTRIES[:i]
            # last bond have no matching entry
            bonds = {e.mac_addr for e in ALL_ENTRIES[: i + 1]}
            paired_cache.store(entries=entries, _bonds=bonds)
            self.assertListEqual(paired_cache.load(), entries)

        paired_cache.store(entries=entries, _bonds=set())
        self.assertListEqual(paired_cache.load(), [])

    def test_max_size(self):
        self.assertIsNone(get_thp_paired_cache())
        # serialize longest `host_name`` and maximal number of bonds
        entries = [
            ThpPairedCacheEntry(mac_addr=bytes([i] * 6), host_name=f"{i}" * 32)
            for i in range(8)
        ]
        bonds = {e.mac_addr for e in entries}
        paired_cache.store(entries=entries, _bonds=bonds)
        self.assertListEqual(paired_cache.load(), entries)

        cache_blob = get_thp_paired_cache()
        self.assertIsNotNone(cache_blob)
        # Check that serialized size is not too large:
        # 8 entries x (32 bytes [name] + 6 bytes [addr]) = 304 bytes
        assert len(cache_blob) <= 400


if __name__ == "__main__":
    unittest.main()
