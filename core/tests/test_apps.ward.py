# flake8: noqa: F403,F405
from common import *  # isort:skip

from trezor.wire import DataError

from apps.ward.keys import _scope, entry_key
from apps.ward import leaf as L
from apps.ward.trie import (
    addr_bit,
    validate_proof_shape,
    verify_membership,
    verify_nonmembership,
)
from apps.ward.leaf import (
    EMPTY_PART,
    ENC_ENCRYPTED,
    ENC_PLAINTEXT,
    commit_of,
    decode_content,
    decode_identity,
    encode_content,
    encode_identity,
    is_delete,
    leaf_hash_of,
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
    K_IDENT = bytes(range(32, 64))
    K_DATA = bytes(range(64, 96))

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
        empty_value = encode_content(self.K_DATA, self.EK, self.KT, b"")
        deleted = encode_content(self.K_DATA, self.EK, self.KT, None)

        self.assertFalse(is_delete(empty_value))
        self.assertTrue(is_delete(deleted))
        self.assertNotEqual(part_bytes(empty_value), part_bytes(deleted))
        self.assertEqual(deleted, EMPTY_PART)

        # ...and an empty value survives the round trip AS an empty value
        self.assertEqual(decode_content(self.K_DATA, self.EK, self.KT, empty_value), (0, b""))
        self.assertIsNone(decode_content(self.K_DATA, self.EK, self.KT, deleted))

    def test_content_round_trip(self):
        part = encode_content(self.K_DATA, self.EK, self.KT, b"hello", c_leaf=9)
        self.assertEqual(decode_content(self.K_DATA, self.EK, self.KT, part), (9, b"hello"))

    def test_identity_round_trip(self):
        part = encode_identity(self.K_IDENT, self.EK, self.KT, b"alice", "bitcoin", 7)
        self.assertEqual(
            decode_identity(self.K_IDENT, self.EK, self.KT, part), (b"alice", b"bitcoin", 7)
        )
        self.assertIsNone(decode_identity(self.K_IDENT, self.EK, self.KT, EMPTY_PART))

    def test_a_delete_empties_both_parts(self):
        """A full delete leaves no tombstone. The reference keeps the identity part
        alive, which preserves a record of which entries once existed."""
        self.assertTrue(is_delete(EMPTY_PART))
        self.assertIsNone(decode_identity(self.K_IDENT, self.EK, self.KT, EMPTY_PART))
        self.assertIsNone(decode_content(self.K_DATA, self.EK, self.KT, EMPTY_PART))


class TestWardSealedLeaf(unittest.TestCase):
    """The sealed leaf, pinned against the reference's own published vectors.

    The nonce is passed explicitly so these are known-answer tests; production leaves it
    None and a fresh one is generated per write.
    """

    NONCE = b"\x5a" * 12
    KT = "address"

    def setUp(self):
        self.k_path = slip21_key(SEED, [b"ward", b"K_path"])
        self.k_ident = slip21_key(SEED, [b"ward", b"K_ident", b"address"])
        self.k_data = slip21_key(SEED, [b"ward", b"K_data", b"address"])
        self.ek = entry_key(self.k_path, "bitcoin", b"alice", "address", 7)

    def _leaf(self):
        id_part = encode_identity(
            self.k_ident, self.ek, self.KT, b"alice", "bitcoin", 7, nonce=self.NONCE
        )
        val_part = encode_content(
            self.k_data, self.ek, self.KT, b"data_alice", c_leaf=5, nonce=self.NONCE
        )
        return id_part, val_part

    def test_frozen_commit_and_leaf_hash(self):
        """The whole sealed leaf, byte-for-byte against the reference.

        This is the strongest cross-implementation check available: it pins the SLIP-21
        labels, the scope, both plaintext layouts, the part framing, the AAD, the bucket
        padding and the commitment in a single pair of constants. If any one of them
        drifts, this fails.
        """
        id_part, val_part = self._leaf()
        commit = commit_of(self.KT, id_part, val_part)
        self.assertEqual(
            commit,
            bytes.fromhex(
                "4e2f5c55548a63a56e10eed9b00b4eaebe7b27ece484aefe319ffdd5b8c3e534"
            ),
        )
        self.assertEqual(
            leaf_hash_of(self.ek, commit),
            bytes.fromhex(
                "ff2d92fe3997f4c2201aa3060c3b2f2fa8bf7e72f463caa63489c95122c57400"
            ),
        )

    def test_seal_then_open(self):
        id_part, val_part = self._leaf()
        self.assertEqual(id_part[0], ENC_ENCRYPTED)
        self.assertEqual(val_part[0], ENC_ENCRYPTED)
        self.assertEqual(len(id_part[1]), 12)  # nonce
        self.assertEqual(len(id_part[2]), 16)  # Poly1305 tag
        self.assertEqual(
            decode_identity(self.k_ident, self.ek, self.KT, id_part),
            (b"alice", b"bitcoin", 7),
        )
        self.assertEqual(
            decode_content(self.k_data, self.ek, self.KT, val_part), (5, b"data_alice")
        )

    def test_ciphertext_hides_the_plaintext(self):
        """Neither the identifier nor the value may appear in what the host receives."""
        id_part, val_part = self._leaf()
        for part in (id_part, val_part):
            self.assertTrue(b"alice" not in part[3])
            self.assertTrue(b"data_alice" not in part[3])
            self.assertTrue(b"bitcoin" not in part[3])

    def test_padding_hides_the_length(self):
        """Ciphertext is padded to a bucket, so its length leaks only a coarse band."""
        short = encode_content(self.k_data, self.ek, self.KT, b"x", nonce=self.NONCE)
        longer = encode_content(
            self.k_data, self.ek, self.KT, b"y" * 40, nonce=self.NONCE
        )
        self.assertEqual(len(short[3]), 64)
        self.assertEqual(len(longer[3]), 64)  # same bucket => same ciphertext length
        big = encode_content(
            self.k_data, self.ek, self.KT, b"z" * 200, nonce=self.NONCE
        )
        self.assertEqual(len(big[3]), 256)

    def test_a_tampered_part_is_rejected(self):
        """Any edit to the tag or the ciphertext must fail the tag check."""
        _id_part, val_part = self._leaf()
        encoding, nonce, tag, ct = val_part

        bad_tag = (encoding, nonce, bytes([tag[0] ^ 1]) + tag[1:], ct)
        with self.assertRaises(DataError):
            decode_content(self.k_data, self.ek, self.KT, bad_tag)

        bad_ct = (encoding, nonce, tag, bytes([ct[0] ^ 1]) + ct[1:])
        with self.assertRaises(DataError):
            decode_content(self.k_data, self.ek, self.KT, bad_ct)

    def test_a_part_cannot_be_moved_to_another_path(self):
        """The AAD binds a part to its entry_key, so replaying it elsewhere fails.

        This is what stops a host from answering a request for one entry with another
        entry's leaf -- the swap that the keyed path alone would not catch.
        """
        _id_part, val_part = self._leaf()
        other_ek = entry_key(self.k_path, "bitcoin", b"bob", "address", 7)
        with self.assertRaises(DataError):
            decode_content(self.k_data, other_ek, self.KT, val_part)

    def test_a_part_cannot_be_consumed_as_the_other_part(self):
        """Distinct AAD domains stop an identity part being opened as a content part."""
        id_part, val_part = self._leaf()
        with self.assertRaises(DataError):
            decode_content(self.k_ident, self.ek, self.KT, id_part)
        with self.assertRaises(DataError):
            decode_identity(self.k_data, self.ek, self.KT, val_part)

    def test_a_part_cannot_be_opened_under_another_key_type(self):
        """key_type is in the AAD as well as selecting the key."""
        id_part, _val_part = self._leaf()
        with self.assertRaises(DataError):
            decode_identity(self.k_ident, self.ek, "label", id_part)

    def test_fresh_nonce_per_write(self):
        """Sealing the same value twice must not reuse a nonce.

        Reuse under ChaCha20-Poly1305 loses confidentiality AND tag unforgeability, and a
        rollback legitimately revisits a leaf, so the nonce must never be derived from it.
        """
        a = encode_content(self.k_data, self.ek, self.KT, b"same")
        b = encode_content(self.k_data, self.ek, self.KT, b"same")
        self.assertNotEqual(a[1], b[1])
        self.assertNotEqual(a[3], b[3])

    def test_plaintext_mode_round_trips(self):
        """The per-part dev switch works, and independently per part.

        The reference has these flags but never exercises them, so its plaintext branches
        were unreachable and untested.
        """
        try:
            L.WARD_PLAINTEXT_CONTENT = True
            part = encode_content(self.k_data, self.ek, self.KT, b"readable")
            self.assertEqual(part[0], ENC_PLAINTEXT)
            self.assertEqual(part[1], b"")  # no nonce
            self.assertTrue(b"readable" in part[3])  # host-inspectable, as intended
            self.assertEqual(
                decode_content(self.k_data, self.ek, self.KT, part), (0, b"readable")
            )
            # ...and the other part is unaffected
            id_part = encode_identity(
                self.k_ident, self.ek, self.KT, b"alice", "bitcoin", 7
            )
            self.assertEqual(id_part[0], ENC_ENCRYPTED)
        finally:
            L.WARD_PLAINTEXT_CONTENT = False

    def test_an_empty_part_survives_a_sealed_build(self):
        """A delete's empty part is plaintext-encoded by construction, so the codec must
        accept it even in a sealed build -- otherwise a build rejects its own delete."""
        from trezor.messages import LeafContent, PlaintextLeaf

        wire = LeafContent(encoding=ENC_PLAINTEXT, plaintext=PlaintextLeaf(content=b""))
        self.assertTrue(is_delete(L.read_leaf_content(wire)))

        # a NON-empty plaintext part, by contrast, must be refused
        wire = LeafContent(encoding=ENC_PLAINTEXT, plaintext=PlaintextLeaf(content=b"x"))
        with self.assertRaises(DataError):
            L.read_leaf_content(wire)


class TestWardTrie(unittest.TestCase):
    """The trie verifier, pinned against vectors that trezorlib, the firmware reference
    and @trezor/ward all agree on.

    They come from a fixed four-leaf tree; only the leaf whose path starts with bit 0 is
    alone on that side, so its membership proof is a single element. The same element is
    the absence proof for any other key starting with 0, since a lookup for one lands on
    that leaf.

    Conformance vectors carry more weight for a trie than usual: a verifier cannot detect
    a non-canonical tree from one path (see the module docstring), so agreement between
    implementations is what keeps everyone building the same shape.
    """

    ROOT = bytes.fromhex(
        "acfe9d9b2c3069070aeb21d72dd53cd7dd3245016ba461c09451d715cb2a6a2d"
    )
    MEMBER = bytes.fromhex(
        "358b7591f24d313e523c7b34b8bd513e4310e08d058aee11d679ba41958853fe"
    )
    ABSENT = bytes.fromhex(
        "5ad38304b535c2987dbd24657c1a11b884984ff600d9f389deb0d4e634fee792"
    )
    WITNESS_COMMIT = bytes.fromhex(
        "2a36629301c9f5965be929bdbb741bbf5980f3829349748045ce20130496bb54"
    )
    PROOF = [
        bytes.fromhex(
            "00000000e96a5c3627be9ad15ae404da1ac72b42f1a602039dbc46fa22eb52e6071949d3"
        )
    ]
    ID_PART = (
        0,
        bytes.fromhex("111111111111111111111111"),
        bytes.fromhex("21212121212121212121212121212121"),
        bytes.fromhex("6964656e746974792d31"),
    )
    VAL_PART = (
        0,
        bytes.fromhex("313131313131313131313131"),
        bytes.fromhex("41414141414141414141414141414141"),
        bytes.fromhex("636970686572746578742d31"),
    )

    def test_bit_order_is_msb_first(self):
        """bit 0 is the TOP bit of byte 0. Getting this backwards would still produce a
        self-consistent trie that disagrees with every other implementation."""
        key = bytes.fromhex("80" + "00" * 31)
        self.assertEqual([addr_bit(key, i) for i in range(3)], [1, 0, 0])
        key = bytes.fromhex("01" + "00" * 31)
        self.assertEqual(addr_bit(key, 7), 1)
        self.assertEqual(addr_bit(key, 0), 0)
        # bit 8 is the top bit of byte 1
        self.assertEqual(addr_bit(bytes.fromhex("00" + "80" + "00" * 30), 8), 1)

    def test_frozen_membership_proof(self):
        """The commit, the proof and the root, byte-for-byte across three impls."""
        self.assertEqual(commit_of("address", self.ID_PART, self.VAL_PART), self.WITNESS_COMMIT)
        self.assertEqual(len(self.PROOF[0]), 36)
        self.assertTrue(
            verify_membership(
                self.MEMBER, "address", self.ID_PART, self.VAL_PART, self.PROOF, self.ROOT
            )
        )

    def test_frozen_nonmembership_proof(self):
        """Absence is proved by the leaf that occupies the absent key's path."""
        self.assertTrue(
            verify_nonmembership(
                self.ABSENT, self.MEMBER, self.WITNESS_COMMIT, self.PROOF, self.ROOT
            )
        )

    def test_membership_against_a_wrong_root_fails(self):
        self.assertFalse(
            verify_membership(
                self.MEMBER, "address", self.ID_PART, self.VAL_PART, self.PROOF, bytes(32)
            )
        )

    def test_membership_of_a_mutated_leaf_fails(self):
        """Any edit to either part changes the commit, hence the leaf, hence the root."""
        for part in ("id", "val"):
            idp, valp = self.ID_PART, self.VAL_PART
            if part == "id":
                idp = (idp[0], idp[1], idp[2], idp[3] + b"x")
            else:
                valp = (valp[0], valp[1], valp[2], valp[3] + b"x")
            self.assertFalse(
                verify_membership(self.MEMBER, "address", idp, valp, self.PROOF, self.ROOT)
            )
        # ...and so does the key_type, which is why it is inside the commit
        self.assertFalse(
            verify_membership(
                self.MEMBER, "label", self.ID_PART, self.VAL_PART, self.PROOF, self.ROOT
            )
        )

    def test_witness_equal_to_target_proves_nothing(self):
        """Otherwise a membership proof would double as a proof of absence."""
        self.assertFalse(
            verify_nonmembership(
                self.MEMBER, self.MEMBER, self.WITNESS_COMMIT, self.PROOF, self.ROOT
            )
        )

    def test_relabelled_split_bit_is_rejected(self):
        """THE malleability attack, and the reason split_bit is inside the node hash.

        The sibling hash is untouched and the chain would still fold to the same value
        under the old format, where the bit index was unauthenticated metadata. A host
        that could relabel hops could manufacture a witness relationship and prove a
        PRESENT key absent.
        """
        relabelled = [bytes([0, 1]) + self.PROOF[0][2:]]
        try:
            self.assertFalse(
                verify_nonmembership(
                    self.ABSENT, self.MEMBER, self.WITNESS_COMMIT, relabelled, self.ROOT
                )
            )
        except DataError:
            pass  # rejected by the shape check before any hashing -- also correct

    def test_proof_shape_is_enforced(self):
        """A proof must describe a real root-to-leaf path before anything is hashed."""
        good = self.PROOF[0]
        for bad in (
            good[:35],  # wrong element length
            bytes([1, 0]) + bytes([0, 0]) + good[4:],  # split_bit >= 256
            bytes([0, 5]) + bytes([0, 0]) + good[4:],  # skiplen != split_bit - start_bit
        ):
            with self.assertRaises(DataError):
                validate_proof_shape([bad])

        # split bits must strictly increase from the root down
        with self.assertRaises(DataError):
            validate_proof_shape(
                [
                    bytes([0, 5]) + bytes([0, 5]) + good[4:],
                    bytes([0, 2]) + bytes([0, 2]) + good[4:],
                ]
            )

    def test_proof_length_is_bounded_by_the_key_space(self):
        """No cap is needed: split_bit strictly increases and stays under 256, so a valid
        proof cannot exceed 256 elements however many the host sends."""
        full = [bytes([0, b]) + bytes([0, 0]) + bytes(32) for b in range(255, -1, -1)]
        self.assertEqual(len(validate_proof_shape(full)), 256)
        with self.assertRaises(DataError):
            validate_proof_shape(full + [bytes([1, 0]) + bytes([0, 0]) + bytes(32)])


if __name__ == "__main__":
    unittest.main()
