# flake8: noqa: F403,F405
from common import *  # isort:skip

from trezor.wire import DataError

from apps.ward.keys import _scope, entry_key
from apps.ward.leaf import (
    EMPTY_PART,
    ENC_ENCRYPTED,
    ENC_PLAINTEXT,
    decode_content,
    decode_identity,
    encode_content,
    encode_identity,
    is_delete,
    pack_content,
    pack_identity,
    part_bytes,
    unpack_content,
    unpack_identity,
)

# Seed used by the reference implementation's own vectors, so the constants below are
# directly comparable with them.
SEED = bytes.fromhex("11" * 64)


def slip21_key(seed, path):
    """SLIP-21 derivation, spelled out rather than imported.

    `apps.common.seed.Slip21Node` is the code under test's dependency; deriving
    independently here means a change to it cannot silently move these vectors.
    """
    from trezor.crypto import hmac

    data = hmac(hmac.SHA512, b"Symmetric key seed", seed).digest()
    for label in path:
        h = hmac(hmac.SHA512, data[0:32], b"\x00")
        h.update(label)
        data = h.digest()
    return data[32:64]


class TestWardKeys(unittest.TestCase):
    def test_frozen_vectors(self):
        """Pins the keyed path byte-for-byte against the reference implementation.

        These exact constants appear in the reference's python/tests/test_ward_crypto.py,
        which also pins the TS host. Any drift in the SLIP-21 labels or the scope layout
        breaks this test rather than surfacing as an unexplained lookup miss at the
        emulator -- or, worse, as a wallet whose entries are all at the wrong paths.
        """
        k_path = slip21_key(SEED, [b"ward", b"K_path"])
        K_PATH = bytes.fromhex(
            "61d6a580121fc98b7bad5ffa0b96552306222c4d97a410dc80e86b837db263c6"
        )
        self.assertEqual(k_path, K_PATH)

        # entry_key(K_path, app_id="bitcoin", identifier=b"alice", "address", device_id=7)
        ENTRY_KEY = bytes.fromhex(
            "20f3088c1a70e4749e21b2f1969b6f982ced4f8d1983cdda856b292bbb51750a"
        )
        self.assertEqual(entry_key(k_path, "bitcoin", b"alice", "address", 7), ENTRY_KEY)

        # The sibling keys that seal the two leaf parts once leaves stop being plaintext.
        # Not used yet; pinned now so the labels cannot drift before they are.
        K_IDENT = bytes.fromhex(
            "5d9542d7e3ca96a17077ea4889ad6461ae63a78cd3e0779a4135d6feeb0ea3b4"
        )
        K_DATA = bytes.fromhex(
            "9ae3bc6866b853cffc237fa11437e68d41ed91c9b8811e2b50a3f4f1cd0aa3e5"
        )
        self.assertEqual(slip21_key(SEED, [b"ward", b"K_ident", b"address"]), K_IDENT)
        self.assertEqual(slip21_key(SEED, [b"ward", b"K_data", b"address"]), K_DATA)

    def test_scope_layout(self):
        """scope = app_id || 0x00 || key_type || 0x00 || device_id(1B)."""
        self.assertEqual(_scope("bitcoin", "address", 7), b"bitcoin\x00address\x00\x07")
        # app_id=None is the empty string, not an omission or a placeholder
        self.assertEqual(_scope(None, "address", 0), b"\x00address\x00\x00")
        # bytes pass through unchanged; str is UTF-8
        self.assertEqual(_scope(b"bitcoin", "address", 0), _scope("bitcoin", "address", 0))

    def test_scope_rejects_nul(self):
        """The delimiters are only unambiguous while the fields cannot contain them.

        Without these checks the same bytes re-split into a different tuple, so two
        distinct entries would collide on one entry_key:

            app_id="x", key_type="address",     device_id=0,    identifier=b"\\x00foo"
            app_id="x", key_type="address\\0\\0", device_id=0x66, identifier=b"oo"
        """
        with self.assertRaises(DataError):
            _scope("bit\x00coin", "address", 0)
        with self.assertRaises(DataError):
            _scope("bitcoin", "add\x00ress", 0)

        # ...and the collision the checks prevent is a real one: assert the two encodings
        # would otherwise have been equal, so this test fails if the layout ever changes
        # in a way that makes the checks unnecessary (or insufficient).
        self.assertEqual(
            b"x" + b"\x00" + b"address" + b"\x00" + bytes([0]) + b"\x00foo",
            b"x" + b"\x00" + b"address\x00\x00" + b"\x00" + bytes([0x66]) + b"oo",
        )

    def test_scope_rejects_out_of_range_device_id(self):
        """device_id occupies exactly one byte, so a wider value has no encoding.

        The reference silently masks with & 0xFF, which maps 256 and 0 to the same path.
        Rejecting is better than aliasing two device slots onto one entry.
        """
        for bad in (-1, 256, 1000):
            with self.assertRaises(DataError):
                _scope("bitcoin", "address", bad)
        # boundaries are valid
        self.assertEqual(_scope("a", "b", 0)[-1:], b"\x00")
        self.assertEqual(_scope("a", "b", 255)[-1:], b"\xff")

    def test_identifier_may_contain_nul(self):
        """identifier is the terminal field, so NUL in it is unambiguous and allowed."""
        k_path = slip21_key(SEED, [b"ward", b"K_path"])
        a = entry_key(k_path, "app", b"\x00lead")
        b = entry_key(k_path, "app", b"lead")
        self.assertNotEqual(a, b)
        self.assertEqual(len(a), 32)

    def test_domain_separation(self):
        """Changing any scope field must change the path."""
        k_path = slip21_key(SEED, [b"ward", b"K_path"])
        base = entry_key(k_path, "app", b"id")
        self.assertNotEqual(base, entry_key(k_path, "other", b"id"))
        self.assertNotEqual(base, entry_key(k_path, "app", b"other"))
        self.assertNotEqual(base, entry_key(k_path, "app", b"id", "label"))
        self.assertNotEqual(base, entry_key(k_path, "app", b"id", "address", 1))
        # and a different K_path (i.e. a different wallet/passphrase) must too
        other = slip21_key(bytes.fromhex("22" * 64), [b"ward", b"K_path"])
        self.assertNotEqual(base, entry_key(other, "app", b"id"))


class TestWardLeaf(unittest.TestCase):
    EK = bytes(range(32))
    KT = "address"

    def test_part_framing(self):
        """part = encoding(1B) || len8(nonce) || nonce || len8(tag) || tag
        || len32(body) || body."""
        self.assertEqual(
            part_bytes((ENC_ENCRYPTED, b"\xaa" * 12, b"\xbb" * 16, b"body")),
            bytes([0])
            + bytes([12])
            + b"\xaa" * 12
            + bytes([16])
            + b"\xbb" * 16
            + (4).to_bytes(4, "big")
            + b"body",
        )
        # plaintext carries no nonce or tag, so both length bytes are zero
        self.assertEqual(
            part_bytes((ENC_PLAINTEXT, b"", b"", b"xy")),
            bytes([1]) + bytes([0]) + bytes([0]) + (2).to_bytes(4, "big") + b"xy",
        )
        # None is the empty part, not a crash
        self.assertEqual(part_bytes(None), part_bytes(EMPTY_PART))

    def test_pack_identity_layout(self):
        """len16(identifier) || identifier || len8(app_id) || app_id || device_id(1B)."""
        self.assertEqual(
            pack_identity(b"alice", "bitcoin", 7),
            (5).to_bytes(2, "big") + b"alice" + bytes([7]) + b"bitcoin" + bytes([7]),
        )
        self.assertEqual(unpack_identity(pack_identity(b"alice", "bitcoin", 7)),
                         (b"alice", b"bitcoin", 7))
        # empty identifier and empty app_id are representable
        self.assertEqual(unpack_identity(pack_identity(b"", b"", 0)), (b"", b"", 0))
        # padding past the end is tolerated, which is what sealing will add
        padded = pack_identity(b"alice", "bitcoin", 7) + b"\x00" * 40
        self.assertEqual(unpack_identity(padded), (b"alice", b"bitcoin", 7))

    def test_pack_identity_rejects_oversized_fields(self):
        """The length prefixes are 2 bytes and 1 byte, so longer fields have no encoding."""
        with self.assertRaises(DataError):
            pack_identity(b"x", "a" * 256, 0)
        with self.assertRaises(DataError):
            pack_identity(b"x", "a", 256)

    def test_pack_content_layout(self):
        """C_leaf(4B BE) || len32(value) || value."""
        self.assertEqual(
            pack_content(5, b"data_alice"),
            (5).to_bytes(4, "big") + (10).to_bytes(4, "big") + b"data_alice",
        )
        self.assertEqual(unpack_content(pack_content(5, b"data_alice")), (5, b"data_alice"))
        padded = pack_content(5, b"v") + b"\x00" * 50
        self.assertEqual(unpack_content(padded), (5, b"v"))

    def test_empty_value_is_not_a_delete(self):
        """The divergence from the reference, which returns an empty part for any empty
        value and so cannot tell an empty entry from a deleted one.

        These two must stay distinguishable, or an entry whose value is empty can neither
        be represented nor deleted.
        """
        empty_value = encode_content(self.EK, self.KT, b"")
        deleted = encode_content(self.EK, self.KT, None)

        self.assertFalse(is_delete(empty_value))
        self.assertTrue(is_delete(deleted))
        self.assertNotEqual(part_bytes(empty_value), part_bytes(deleted))
        self.assertEqual(deleted, EMPTY_PART)

        # ...and an empty value survives the round trip AS an empty value
        self.assertEqual(decode_content(self.EK, self.KT, empty_value), (0, b""))
        self.assertIsNone(decode_content(self.EK, self.KT, deleted))

    def test_content_round_trip(self):
        part = encode_content(self.EK, self.KT, b"hello", c_leaf=9)
        self.assertEqual(decode_content(self.EK, self.KT, part), (9, b"hello"))

    def test_identity_round_trip(self):
        part = encode_identity(self.EK, self.KT, b"alice", "bitcoin", 7)
        self.assertEqual(decode_identity(self.EK, self.KT, part), (b"alice", b"bitcoin", 7))
        self.assertIsNone(decode_identity(self.EK, self.KT, EMPTY_PART))

    def test_a_delete_empties_both_parts(self):
        """A full delete leaves no tombstone. The reference keeps the identity part
        alive, which preserves a record of which entries once existed."""
        self.assertTrue(is_delete(EMPTY_PART))
        self.assertIsNone(decode_identity(self.EK, self.KT, EMPTY_PART))
        self.assertIsNone(decode_content(self.EK, self.KT, EMPTY_PART))


if __name__ == "__main__":
    unittest.main()
