# flake8: noqa: F403,F405
from common import *  # isort:skip

from trezor.wire import DataError

from apps.ward import attest as A
from apps.ward import cas as CAS
from apps.ward import leaf as L
from apps.ward import offline_store as OS
from apps.ward.attest import EMPTY_ROOT
from apps.ward.keys import _scope, entry_key
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
from apps.ward.trie import (
    addr_bit,
    compute_new_root,
    internal_hash,
    validate_proof_shape,
    verify_membership,
    verify_nonmembership,
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
        self.assertEqual(
            entry_key(k_path, "bitcoin", b"alice", "address", 7), ENTRY_KEY
        )

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
        self.assertEqual(
            _scope(b"bitcoin", "address", 0), _scope("bitcoin", "address", 0)
        )

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
        self.assertEqual(
            unpack_identity(pack_identity(b"alice", "bitcoin", 7)),
            (b"alice", b"bitcoin", 7),
        )
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
        self.assertEqual(
            unpack_content(pack_content(5, b"data_alice")), (5, b"data_alice")
        )
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
        self.assertEqual(
            decode_content(self.K_DATA, self.EK, self.KT, empty_value), (0, b"")
        )
        self.assertIsNone(decode_content(self.K_DATA, self.EK, self.KT, deleted))

    def test_content_round_trip(self):
        part = encode_content(self.K_DATA, self.EK, self.KT, b"hello", c_leaf=9)
        self.assertEqual(
            decode_content(self.K_DATA, self.EK, self.KT, part), (9, b"hello")
        )

    def test_identity_round_trip(self):
        part = encode_identity(self.K_IDENT, self.EK, self.KT, b"alice", "bitcoin", 7)
        self.assertEqual(
            decode_identity(self.K_IDENT, self.EK, self.KT, part),
            (b"alice", b"bitcoin", 7),
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
        from trezor.messages import WardLeafContent, WardPlaintextLeaf

        wire = WardLeafContent(
            encoding=ENC_PLAINTEXT, plaintext=WardPlaintextLeaf(content=b"")
        )
        self.assertTrue(is_delete(L.read_leaf_content(wire)))

        # a NON-empty plaintext part, by contrast, must be refused
        wire = WardLeafContent(
            encoding=ENC_PLAINTEXT, plaintext=WardPlaintextLeaf(content=b"x")
        )
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
        "2b4e46b341ecf5ebbb506bb6878e1523dff181e103ede3c683c955d34302fa1e"
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
            "0000e96a5c3627be9ad15ae404da1ac72b42f1a602039dbc46fa22eb52e6071949d3"
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
        self.assertEqual(
            commit_of("address", self.ID_PART, self.VAL_PART), self.WITNESS_COMMIT
        )
        self.assertEqual(len(self.PROOF[0]), 34)
        self.assertTrue(
            verify_membership(
                self.MEMBER,
                "address",
                self.ID_PART,
                self.VAL_PART,
                self.PROOF,
                self.ROOT,
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
                self.MEMBER,
                "address",
                self.ID_PART,
                self.VAL_PART,
                self.PROOF,
                bytes(32),
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
                verify_membership(
                    self.MEMBER, "address", idp, valp, self.PROOF, self.ROOT
                )
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

    def test_false_absence_by_boundary_shift_is_rejected(self):
        """A PRESENT key proved absent, using its own membership proof. Length checks stop it.

        The leaf preimage concatenates entry_key and commit with nothing marking the
        boundary, so (K, C) and (K || C[0], C[1:]) hash identically -- no attack on SHA-256
        involved. A non-membership witness is host-supplied, and the other two checks do not
        help: the shifted key DIFFERS from the target, and routing reads bits 0..255, i.e.
        the first 32 bytes, so it agrees at every branch bit.

        The consequence was a soundness break, not an inconvenience: a host could hide any
        present entry on every read, and a delete of it would report the idempotent success
        reserved for a proved absence.
        """
        shifted_key = self.MEMBER + self.WITNESS_COMMIT[:1]
        shifted_commit = self.WITNESS_COMMIT[1:]
        self.assertTrue(shifted_key != self.MEMBER)
        self.assertEqual(
            shifted_key + shifted_commit, self.MEMBER + self.WITNESS_COMMIT
        )

        # the primitive refuses to hash operands of the wrong width at all
        with self.assertRaises(DataError):
            leaf_hash_of(shifted_key, shifted_commit)

        # ...and the witness is refused before the comparisons that would have passed.
        # A malformed operand RAISES rather than reading as a failed claim: returning
        # False here surfaced as "absence does not match the trusted root", which blames
        # the host's tree for what is a malformed message.
        with self.assertRaises(DataError):
            verify_nonmembership(
                self.MEMBER, shifted_key, shifted_commit, self.PROOF, self.ROOT
            )

    def test_preimage_operands_are_fixed_width(self):
        """The same ambiguity, in every other preimage that concatenates opaque bytes.

        Only the leaf one was exploitable -- the others are reachable but blocked by range
        checks further on, or by a signature the host cannot forge. Pinning the widths at the
        primitive means none of them depends on that accident holding.
        """
        short, long = bytes(31), bytes(33)
        ok = bytes(32)
        for bad in (short, long):
            with self.assertRaises(DataError):
                CAS.transition_preimage(CAS.TAG_COMMIT, bad, 1, ok, 2, ok)
            with self.assertRaises(DataError):
                CAS.transition_preimage(CAS.TAG_COMMIT, ok, 1, bad, 2, ok)
            with self.assertRaises(DataError):
                A.root_mac(bytes(32), bad, 1, None)
            with self.assertRaises(DataError):
                A.attestation_preimage(bytes(32), bytes(32), 1, bad, 0)

        # and a shifted (from_mac, to_counter, to_mac) can no longer reproduce a genuine
        # authorisation, which it could byte-for-byte before
        wid, fm, tm = bytes(range(32)), bytes([7]) * 32, bytes([9]) * 32
        genuine = CAS.transition_preimage(CAS.TAG_COMMIT, wid, 2, fm, 3, tm)
        with self.assertRaises(DataError):
            CAS.transition_preimage(
                CAS.TAG_COMMIT,
                wid,
                2,
                fm + (3).to_bytes(4, "big")[:1],
                int.from_bytes((3).to_bytes(4, "big")[1:] + tm[:1], "big"),
                tm[1:],
            )
        self.assertEqual(len(genuine), 1 + len(CAS.TAG_COMMIT) + 32 + 4 + 32 + 4 + 32)

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
            good[:33],  # wrong element length
            bytes([1, 0]) + good[2:],  # split_bit >= 256
        ):
            with self.assertRaises(DataError):
                validate_proof_shape([bad])

        # Split bits must strictly increase from the root DOWN, and a proof is ordered
        # leaf-to-root -- so a well-formed one has them DECREASING in list order. Getting
        # that backwards writes a test that asserts nothing, which is what happened here
        # while the skiplen arithmetic was doing the rejecting instead.
        with self.assertRaises(DataError):
            validate_proof_shape([bytes([0, 2]) + good[2:], bytes([0, 5]) + good[2:]])

        # ...and the same two, the right way round, are accepted
        self.assertEqual(
            len(
                validate_proof_shape(
                    [bytes([0, 5]) + good[2:], bytes([0, 2]) + good[2:]]
                )
            ),
            2,
        )

    def test_proof_length_is_bounded_by_the_key_space(self):
        """No cap is needed: split_bit strictly increases and stays under 256, so a valid
        proof cannot exceed 256 elements however many the host sends."""
        full = [bytes([0, b]) + bytes(32) for b in range(255, -1, -1)]
        self.assertEqual(len(validate_proof_shape(full)), 256)
        with self.assertRaises(DataError):
            validate_proof_shape(full + [bytes([1, 0]) + bytes(32)])


class TestWardComputeNewRoot(unittest.TestCase):
    """The device deriving the root that replaces the current one.

    Every case here is checked against the root a canonical REBUILD would produce, which
    is the property that matters: a device whose root drifts from the canonical one still
    verifies its own proofs happily, and only diverges when some other party rebuilds the
    tree -- at which point the whole entry set is unreachable. A test that merely asserted
    "some root came back" would not have caught either bug below.
    """

    KT = "address"
    EMPTY = (1, b"", b"", b"")

    def _key(self, bits):
        """A 32-byte path beginning with `bits`, padded with zeros."""
        out = bytearray(32)
        for i, b in enumerate(bits):
            if b:
                out[i // 8] |= 1 << (7 - (i % 8))
        return bytes(out)

    def _leaf(self, tag):
        return (self.KT, self.EMPTY, (1, b"", b"", tag))

    def _commit(self, tag):
        return commit_of(self.KT, self.EMPTY, (1, b"", b"", tag))

    def _lh(self, key, tag):
        return leaf_hash_of(key, self._commit(tag))

    @staticmethod
    def _elem(split_bit, sibling):
        return split_bit.to_bytes(2, "big") + sibling

    def test_first_insert_needs_an_empty_device(self):
        """With no proof and no witness the device's own record is the only authority."""
        k = self._key([0])
        self.assertEqual(
            compute_new_root(k, None, self._leaf(b"a"), [], None), self._lh(k, b"a")
        )
        # ...and the same call is refused once the device holds a root
        with self.assertRaises(DataError):
            compute_new_root(k, None, self._leaf(b"a"), [], bytes(32))

    def test_update_must_prove_the_current_leaf(self):
        """A host cannot swap a value without first proving what is there now."""
        a, b = self._key([0]), self._key([1])
        la, lb = self._lh(a, b"a"), self._lh(b, b"b")
        root = internal_hash(0, la, lb)
        proof = [self._elem(0, lb)]

        self.assertEqual(
            compute_new_root(a, self._leaf(b"a"), self._leaf(b"a2"), proof, root),
            internal_hash(0, self._lh(a, b"a2"), lb),
        )
        with self.assertRaises(DataError):
            compute_new_root(a, self._leaf(b"WRONG"), self._leaf(b"a2"), proof, root)

    def test_delete_promotes_the_sibling_unchanged(self):
        """The collapsing sibling takes the branch's place with its hash untouched.

        This needed a witness for the sibling's KIND until a node's hash stopped committing
        to its depth: a branch's hash went stale the instant it moved, a leaf's did not, and
        the device could not tell them apart from the proof alone. Now neither moves.
        """
        a, b = self._key([0]), self._key([1])
        la, lb = self._lh(a, b"a"), self._lh(b, b"b")
        root = internal_hash(0, la, lb)
        proof = [self._elem(0, lb)]
        # one leaf left, and a single-leaf tree's root IS that leaf hash
        self.assertEqual(compute_new_root(a, self._leaf(b"a"), None, proof, root), lb)

    def test_emptying_the_tree_yields_a_root_that_says_so(self):
        """Deleting the last entry gives EMPTY_ROOT, never None.

        "The tree is empty" and "this device has no root and therefore checks nothing" used
        to be the same value, so deleting a one-entry wallet's only entry silently turned
        verification off -- reachable by ordinary use, from a state the user has every
        reason to believe is protected.
        """
        a = self._key([0])
        root = self._lh(a, b"a")
        got = compute_new_root(a, self._leaf(b"a"), None, [], root)
        self.assertEqual(got, EMPTY_ROOT)
        self.assertTrue(got is not None)

    def test_an_emptied_tree_accepts_a_first_insert_again(self):
        """...and EMPTY_ROOT still counts as empty where that matters.

        Otherwise the fix above would trade a security hole for a dead wallet: there is no
        leaf to witness, so an insert here has to take the no-proof path exactly as it does
        on a device that has never written.
        """
        k = self._key([0, 1])
        self.assertEqual(
            compute_new_root(k, None, self._leaf(b"fresh"), [], EMPTY_ROOT),
            self._lh(k, b"fresh"),
        )

    def test_an_empty_tree_holds_nothing_to_replace(self):
        """An update or a delete against an empty tree is refused, not silently derived."""
        k = self._key([0])
        with self.assertRaises(DataError):
            compute_new_root(k, self._leaf(b"a"), self._leaf(b"b"), [], EMPTY_ROOT)
        with self.assertRaises(DataError):
            compute_new_root(k, self._leaf(b"a"), None, [], EMPTY_ROOT)

    def test_delete_promotes_a_branch_sibling_unchanged(self):
        """THE case this module used to get wrong, twice.

        Deleting `a` collapses the root branch, so the b/c branch moves up a level. Its hash
        used to commit to a depth measured from its old parent, so promoting it unchanged
        -- the obvious way to write this -- produced a root no rebuild agreed with, and the
        fix was to have it arrive decomposed so the device could re-derive it. With depth out
        of the preimage the obvious way is the correct one.
        """
        a = self._key([0])
        b = self._key([1, 0, 0, 0, 0, 0])
        c = self._key([1, 0, 0, 0, 0, 1])
        la, lb, lc = self._lh(a, b"a"), self._lh(b, b"b"), self._lh(c, b"c")

        bc = internal_hash(5, lb, lc)  # b and c first differ at bit 5
        root = internal_hash(0, la, bc)
        proof = [self._elem(0, bc)]

        # afterwards b/c IS the root, with the same hash it had one level down
        got = compute_new_root(a, self._leaf(b"a"), None, proof, root)
        self.assertEqual(got, bc)

    def test_insert_above_an_existing_branch(self):
        """The second bug: the new key parts from its witness inside a COMPRESSED run.

        Path compression only compares the bits the tree branches on, so two keys can
        agree at every one of them and still diverge above an existing branch -- the
        ordinary case for a random key, not a corner one. The new node is spliced in
        there and the branch below is re-parented, which the device can fix itself since
        that node is on the path it is folding.
        """
        b = self._key([0, 0, 0, 0, 0, 0])
        c = self._key([0, 0, 0, 0, 0, 1])
        a = self._key([0, 0, 1])  # agrees with b at bit 0, parts at bit 2
        lb, lc, la = self._lh(b, b"b"), self._lh(c, b"c"), self._lh(a, b"a")

        root = internal_hash(5, lb, lc)  # two leaves: the b/c branch is the root
        proof = [self._elem(5, lc)]  # witness is b

        got = compute_new_root(
            a,
            None,
            self._leaf(b"a"),
            proof,
            root,
            witness_entry_key=b,
            witness_commit=self._commit(b"b"),
        )
        # canonical: root branches at bit 2, and the b/c branch hangs below UNCHANGED --
        # it used to need its skiplen restated for the depth it had just moved to
        self.assertEqual(got, internal_hash(2, internal_hash(5, lb, lc), la))

    def test_insert_below_the_witness_path(self):
        """The simpler case: the keys part deeper than every existing branch."""
        b = self._key([0])
        c = self._key([1])
        a = self._key([0, 1])  # agrees with b at bit 0, parts at bit 1
        lb, lc, la = self._lh(b, b"b"), self._lh(c, b"c"), self._lh(a, b"a")

        root = internal_hash(0, lb, lc)
        proof = [self._elem(0, lc)]
        got = compute_new_root(
            a,
            None,
            self._leaf(b"a"),
            proof,
            root,
            witness_entry_key=b,
            witness_commit=self._commit(b"b"),
        )
        self.assertEqual(got, internal_hash(0, internal_hash(1, lb, la), lc))


class TestWardAttestation(unittest.TestCase):
    """The WM's freshness signature and the root MAC it signs.

    The WM cannot compute a mac -- K_mac never leaves the device -- so it can only ever
    REPLAY a (counter, mac) pair this wallet genuinely reached. That, plus a counter
    floor, is the entire freshness guarantee; the tests below pin both halves.
    """

    # The well-known debug WM seed. Its public key is compiled into attest.py.
    WM_SEED = b"AUTHDB QM DEBUG KEY SEED v1 ...."
    WARD_ID = bytes(range(32))
    NONCE = bytes(range(32, 64))
    K_MAC = bytes(range(64, 96))
    ROOT = bytes([7]) * 32
    # A wall-clock second that is not a round number and not zero: a layout bug that
    # dropped the field or wrote it at the wrong width would still pass against 0.
    TIME = 0x0102030405060708

    def _sign(self, message, seed=None):
        from trezor.crypto.curve import ed25519

        return ed25519.sign(seed or self.WM_SEED, message)

    # --- the two verification paths, and the line between them ---------------------

    def test_an_archived_attestation_cannot_answer_the_live_question(self):
        """THE PROPERTY THAT REPLACES THE NONCE'S ANTI-STOCKPILING GUARANTEE.

        The nonce exists so a host cannot keep "a drawer of previously-signed anchors and serve
        whichever suits it" -- the device mints it before the host reaches the WM, so the WM must
        sign a value nobody could know in advance. An archive of attestations IS that drawer, and
        it is admitted only because it answers a different question: not "is this the head now"
        but "was this ever a head".

        This pins the line. A tuple signed under one round's nonce must NOT verify against
        another round's -- which is what keeps the archive out of every path that decides
        currency, without those paths needing to know the archive exists.
        """
        archived_nonce = bytes([0xA1]) * 32
        live_nonce = self.NONCE
        self.assertNotEqual(archived_nonce, live_nonce)

        mac = A.root_mac(self.K_MAC, self.WARD_ID, 41, self.ROOT)
        sig = self._sign(
            A.attestation_preimage(self.WARD_ID, archived_nonce, 41, mac, self.TIME)
        )

        # it verifies as HISTORY, under the nonce it was minted for...
        self.assertTrue(
            A.verify_archived_attestation(
                self.WARD_ID, archived_nonce, 41, mac, self.TIME, sig
            )
        )
        # ...and is refused as CURRENCY by the round-bound path, which only ever offers the
        # nonce of the round actually open. This is the whole separation, in one assertion.
        self.assertFalse(
            A.verify_attestation(self.WARD_ID, live_nonce, 41, mac, self.TIME, sig)
        )

    def test_the_archived_path_is_not_a_weaker_check(self):
        """It refuses forgeries exactly as the live path does -- the difference is the QUESTION,
        not the rigour. A tuple the WM never signed is refused whichever door it arrives at."""
        mac = A.root_mac(self.K_MAC, self.WARD_ID, 41, self.ROOT)
        genuine = self._sign(
            A.attestation_preimage(self.WARD_ID, self.NONCE, 41, mac, self.TIME)
        )

        # wrong signer
        forged = self._sign(
            A.attestation_preimage(self.WARD_ID, self.NONCE, 41, mac, self.TIME),
            seed=b"NOT THE WARD MANAGER DEBUG KEY!!",
        )
        self.assertFalse(
            A.verify_archived_attestation(
                self.WARD_ID, self.NONCE, 41, mac, self.TIME, forged
            )
        )
        # every operand is bound: a different counter or mac does not verify
        self.assertFalse(
            A.verify_archived_attestation(
                self.WARD_ID, self.NONCE, 42, mac, self.TIME, genuine
            )
        )
        self.assertFalse(
            A.verify_archived_attestation(
                self.WARD_ID, self.NONCE, 41, bytes(32), self.TIME, genuine
            )
        )

    def test_an_archived_mac_cannot_be_re_dated(self):
        """WHY THE COUNTER LIVES INSIDE root_mac, stated as the attack it prevents.

        If a mac committed only to the root, a host holding an old attestation could pair it
        with any counter: the WM's signature covers the counter, but nothing would tie that
        counter to the root supplied at adoption. The device would take a year-old tree as
        today's state -- a silent rollback that reads as forward progress.

        Because the counter IS inside the mac, an archived (counter, mac) is satisfiable by
        exactly one root at exactly one moment.
        """
        mac_at_41 = A.root_mac(self.K_MAC, self.WARD_ID, 41, self.ROOT)
        mac_at_99 = A.root_mac(self.K_MAC, self.WARD_ID, 99, self.ROOT)
        self.assertNotEqual(mac_at_41, mac_at_99)

    def test_debug_key_matches_its_seed(self):
        """The compiled debug pubkey really is this seed's, or every test below is vacuous."""
        from trezor.crypto.curve import ed25519

        self.assertEqual(ed25519.publickey(self.WM_SEED), A._WM_PUBKEY_DEBUG)

    def test_production_key_is_unprovisioned(self):
        """Shipping with a placeholder is correct: a device that accepted a WM key from
        whoever offered one would be checking freshness against an adversary's clock."""
        self.assertEqual(A._WM_PUBKEY, bytes(32))

    def test_root_mac_binds_everything_it_names(self):
        mac = A.root_mac(self.K_MAC, self.WARD_ID, 5, self.ROOT)
        self.assertEqual(len(mac), 32)
        # the counter, which is the point: roots repeat whenever contents repeat, so a mac
        # over the root alone would name a shape rather than a moment
        self.assertNotEqual(mac, A.root_mac(self.K_MAC, self.WARD_ID, 6, self.ROOT))
        self.assertNotEqual(
            mac, A.root_mac(self.K_MAC, self.WARD_ID, 5, bytes([8]) * 32)
        )
        self.assertNotEqual(mac, A.root_mac(self.K_MAC, bytes(32), 5, self.ROOT))
        self.assertNotEqual(mac, A.root_mac(bytes(32), self.WARD_ID, 5, self.ROOT))

    def test_the_empty_tree_is_attestable_too(self):
        """An absent root macs the all-zero root rather than being skipped, so "empty" is
        still bound to a counter -- otherwise a WM could attest empty at any counter."""
        empty5 = A.root_mac(self.K_MAC, self.WARD_ID, 5, None)
        self.assertNotEqual(empty5, A.root_mac(self.K_MAC, self.WARD_ID, 6, None))
        self.assertNotEqual(empty5, A.root_mac(self.K_MAC, self.WARD_ID, 5, self.ROOT))

    def test_attestation_preimage_layout(self):
        mac = A.root_mac(self.K_MAC, self.WARD_ID, 5, self.ROOT)
        self.assertEqual(
            A.attestation_preimage(self.WARD_ID, self.NONCE, 5, mac, self.TIME),
            b"WARD ATTEST v1"
            + bytes([2])
            + self.NONCE
            + self.WARD_ID
            + (5).to_bytes(4, "big")
            + mac
            + self.TIME.to_bytes(8, "big"),
        )

    def test_a_genuine_attestation_verifies(self):
        mac = A.root_mac(self.K_MAC, self.WARD_ID, 5, self.ROOT)
        sig = self._sign(
            A.attestation_preimage(self.WARD_ID, self.NONCE, 5, mac, self.TIME)
        )
        self.assertTrue(
            A.verify_attestation(self.WARD_ID, self.NONCE, 5, mac, self.TIME, sig)
        )

    def test_every_signed_field_is_bound(self):
        """Changing anything the signature covers must break it -- notably the nonce, which
        is what stops a host stockpiling anchors and replaying one later."""
        mac = A.root_mac(self.K_MAC, self.WARD_ID, 5, self.ROOT)
        sig = self._sign(
            A.attestation_preimage(self.WARD_ID, self.NONCE, 5, mac, self.TIME)
        )

        self.assertFalse(
            A.verify_attestation(self.WARD_ID, bytes(32), 5, mac, self.TIME, sig)
        )
        self.assertFalse(
            A.verify_attestation(self.WARD_ID, self.NONCE, 6, mac, self.TIME, sig)
        )
        self.assertFalse(
            A.verify_attestation(self.WARD_ID, self.NONCE, 5, bytes(32), self.TIME, sig)
        )
        self.assertFalse(
            A.verify_attestation(bytes(32), self.NONCE, 5, mac, self.TIME, sig)
        )
        self.assertFalse(
            A.verify_attestation(self.WARD_ID, self.NONCE, 5, mac, self.TIME + 1, sig)
        )

    def test_another_signer_is_refused(self):
        mac = A.root_mac(self.K_MAC, self.WARD_ID, 5, self.ROOT)
        pre = A.attestation_preimage(self.WARD_ID, self.NONCE, 5, mac, self.TIME)
        sig = self._sign(pre, seed=b"NOT THE WARD MANAGER DEBUG KEY!!")
        self.assertFalse(
            A.verify_attestation(self.WARD_ID, self.NONCE, 5, mac, self.TIME, sig)
        )

    def test_a_zero_signature_never_verifies(self):
        """Not paranoia. Against the all-zero placeholder key an all-zero signature is a
        DEGENERATE acceptance -- R=0, S=0 satisfies [S]B = R + [k]A when A is the identity
        -- so an unprovisioned device would accept an attestation carrying no signature at
        all. Both halves are refused: the zero signature, and verifying against the
        placeholder key.
        """
        mac = A.root_mac(self.K_MAC, self.WARD_ID, 5, self.ROOT)
        self.assertFalse(
            A.verify_attestation(self.WARD_ID, self.NONCE, 5, mac, self.TIME, bytes(64))
        )

    def test_a_malformed_signature_is_refused(self):
        mac = A.root_mac(self.K_MAC, self.WARD_ID, 5, self.ROOT)
        sig = self._sign(
            A.attestation_preimage(self.WARD_ID, self.NONCE, 5, mac, self.TIME)
        )
        self.assertFalse(
            A.verify_attestation(self.WARD_ID, self.NONCE, 5, mac, self.TIME, sig[:63])
        )
        self.assertFalse(
            A.verify_attestation(
                self.WARD_ID, self.NONCE, 5, mac, self.TIME, sig + b"\x00"
            )
        )


class TestWardCas(unittest.TestCase):
    """Authorising a transition from one root to the next.

    A MAC rather than a signature: K_auth is seed-derived, so exactly the parties that
    need to verify a transition -- the other devices of this wallet -- can, and nobody
    else. See cas.py for when that would need to become a signature.
    """

    K_AUTH = bytes(range(32))
    K_MAC = bytes(range(64, 96))
    WARD_ID = bytes(range(32, 64))
    R1 = bytes([1]) * 32
    R2 = bytes([2]) * 32

    def _link(self, f, fr, t, tr):
        return (f, fr, t, tr, CAS.auth_commit(self.K_AUTH, self.K_MAC, self.WARD_ID, f, fr, t, tr))

    def test_a_claim_distinguishes_two_candidates_at_one_counter(self):
        """What the counter-path settlement in `offline_store.reconcile_pending` now rests on.

        Two devices of one wallet both sitting at 41 each build a candidate 42. Settling on
        `claimed <= adopted` cannot tell them apart, so the loser cleared its own queued change as
        landed when it reconciled to the winner's head -- silent loss of a change the user
        approved, from ordinary concurrent use.

        The claim already carries the `auth_commit` of the transition it was filed for, and that
        names a TO-ROOT. So the question "did MY change produce this head" is answerable without a
        chain: re-derive the authorisation over (41, our root) -> (42, adopted root) and see
        whether it reproduces. This pins that it discriminates -- same counters, same from-root,
        different to-root must not verify -- because if it did not, the new check would be the old
        one wearing a hash.
        """
        mine = CAS.auth_commit(self.K_AUTH, self.K_MAC, self.WARD_ID, 41, self.R1, 42, self.R2)
        theirs_root = bytes([3]) * 32

        # the winner's head at the same counter does not reproduce my authorisation
        self.assertFalse(
            CAS.verify_auth_commit(
                self.K_AUTH, self.K_MAC, self.WARD_ID, 41, self.R1, 42, theirs_root, mine
            )
        )
        # ...and my own head does
        self.assertTrue(
            CAS.verify_auth_commit(
                self.K_AUTH, self.K_MAC, self.WARD_ID, 41, self.R1, 42, self.R2, mine
            )
        )
        # the from-state is bound too, so a claim filed from a different head cannot be
        # re-read as one filed from this one
        self.assertFalse(
            CAS.verify_auth_commit(
                self.K_AUTH, self.K_MAC, self.WARD_ID, 41, theirs_root, 42, self.R2, mine
            )
        )

    def test_empty_root_sentinel(self):
        """A root inside a preimage is fixed-width, so the empty tree needs an encoding no
        real root can take. sha256(0x03), domain-separated from the leaf/internal/commit
        tags -- and spelled as a literal, so this asserts it really is that hash."""
        from trezor.crypto.hashlib import sha256

        self.assertEqual(A.EMPTY_ROOT, sha256(b"\x03").digest())

    def test_preimage_names_both_endpoints(self):
        """Binding only the destination would let a link be lifted out of its place in the
        history and replayed after a different predecessor -- which is what a chain exists
        to prevent."""
        m0, m1 = bytes([7]) * 32, bytes([9]) * 32
        pre = CAS.transition_preimage(CAS.TAG_COMMIT, self.WARD_ID, 4, m0, 5, m1)
        self.assertEqual(
            pre,
            bytes([len(CAS.TAG_COMMIT)])
            + CAS.TAG_COMMIT
            + self.WARD_ID
            + (4).to_bytes(4, "big")
            + m0
            + (5).to_bytes(4, "big")
            + m1,
        )
        # The endpoints are MAC HEADS now, so the empty tree is encoded one layer down -- in
        # `root_mac`, which macs the EMPTY_ROOT stand-in rather than skipping an absent root.
        self.assertEqual(
            A.root_mac(self.K_MAC, self.WARD_ID, 0, None),
            A.root_mac(self.K_MAC, self.WARD_ID, 0, A.EMPTY_ROOT),
        )

    def test_every_field_is_bound(self):
        mac = CAS.auth_commit(self.K_AUTH, self.K_MAC, self.WARD_ID, 4, self.R1, 5, self.R2)
        self.assertTrue(
            CAS.verify_auth_commit(
                self.K_AUTH, self.K_MAC, self.WARD_ID, 4, self.R1, 5, self.R2, mac
            )
        )
        for args in (
            (self.K_AUTH, self.K_MAC, self.WARD_ID, 3, self.R1, 5, self.R2),
            (self.K_AUTH, self.K_MAC, self.WARD_ID, 4, self.R2, 5, self.R2),
            (self.K_AUTH, self.K_MAC, self.WARD_ID, 4, self.R1, 6, self.R2),
            (self.K_AUTH, self.K_MAC, self.WARD_ID, 4, self.R1, 5, self.R1),
            (self.K_AUTH, self.K_MAC, bytes(32), 4, self.R1, 5, self.R2),
            (bytes(32), self.K_MAC, self.WARD_ID, 4, self.R1, 5, self.R2),
        ):
            self.assertFalse(CAS.verify_auth_commit(*args, mac))

    def test_a_revert_is_not_a_commit(self):
        """Same endpoints, different meaning. Sharing a tag would let a rollback be
        replayed as an ordinary write, or the reverse."""
        commit = CAS.auth_commit(self.K_AUTH, self.K_MAC, self.WARD_ID, 4, self.R1, 5, self.R2)
        revert = CAS.auth_commit(
            self.K_AUTH, self.K_MAC, self.WARD_ID, 4, self.R1, 5, self.R2, CAS.TAG_REVERT
        )
        self.assertNotEqual(commit, revert)
        self.assertFalse(
            CAS.verify_auth_commit(
                self.K_AUTH, self.K_MAC, self.WARD_ID, 4, self.R1, 5, self.R2, revert
            )
        )

    def test_a_genuine_chain_folds_to_its_head(self):
        counter, root = 0, None
        for link in (
            self._link(0, None, 1, self.R1),
            self._link(1, self.R1, 2, self.R2),
        ):
            counter, root, _reverted = CAS.verify_chain_step(
                self.K_AUTH, self.K_MAC, self.WARD_ID, counter, root, link
            )
        self.assertEqual((counter, root), (2, self.R2))

    def test_a_genuine_chain_folds_BACKWARDS_to_its_tail(self):
        """The direction `verify_chain` actually walks.

        Anchored at the head and stepping back, each link's `to` end is pinned by a state already
        established -- ultimately by the WM's attestation of the anchor -- rather than its `from`
        end being pinned and its `to` end left to the host.
        """
        counter, root = 2, self.R2
        for link in (
            self._link(1, self.R1, 2, self.R2),
            self._link(0, None, 1, self.R1),
        ):
            counter, root, _reverted = CAS.verify_chain_step_back(
                self.K_AUTH, self.K_MAC, self.WARD_ID, counter, root, link
            )
        self.assertEqual((counter, root), (0, None))

    def test_the_backward_chain_refuses_an_ORPHANED_candidate(self):
        """THE PROPERTY THE BACKWARD WALK EXISTS FOR, and the forward fold does not have.

        A device hands out an `auth_commit` on WardLeafAck before it knows whether the write
        landed, so a host holds genuine links for transitions the WM never accepted. R1 and R2
        here are two such candidates for counter 1: both authorised, only one of them history.

        Folding FORWARD from (0, None) either is accepted, because the `to` end is the host's to
        choose. Walking BACK from the head the WM attested, the orphan is refused on the root
        check before its MAC is ever computed -- not by a rule that has to be remembered, but
        because the walk asked for the link ending somewhere else.
        """
        orphan = self._link(0, None, 1, self.R2)  # authorised, and never the head
        real = self._link(0, None, 1, self.R1)  # the branch the WM took

        # forward, the orphan is indistinguishable: both fold cleanly off (0, None)
        for candidate in (orphan, real):
            CAS.verify_chain_step(
                self.K_AUTH, self.K_MAC, self.WARD_ID, 0, None, candidate
            )

        # backward, anchored at (1, R1), only the real one is admissible
        counter, root, _r = CAS.verify_chain_step_back(
            self.K_AUTH, self.K_MAC, self.WARD_ID, 1, self.R1, real
        )
        self.assertEqual((counter, root), (0, None))
        with self.assertRaises(DataError):
            CAS.verify_chain_step_back(
                self.K_AUTH, self.K_MAC, self.WARD_ID, 1, self.R1, orphan
            )

    def test_the_backward_chain_refuses_every_way_of_lying_with_real_links(self):
        """The mirror of the forward case: authentic links, wrong placement."""
        # a gap
        with self.assertRaises(DataError):
            CAS.verify_chain_step_back(
                self.K_AUTH,
                self.K_MAC,
                self.WARD_ID,
                2,
                self.R2,
                self._link(0, None, 2, self.R2),
            )
        # a link ending at another branch's root at the right counter
        with self.assertRaises(DataError):
            CAS.verify_chain_step_back(
                self.K_AUTH,
                self.K_MAC,
                self.WARD_ID,
                2,
                self.R1,
                self._link(1, self.R1, 2, self.R2),
            )
        # a link ending at a counter the walk is not at
        with self.assertRaises(DataError):
            CAS.verify_chain_step_back(
                self.K_AUTH,
                self.K_MAC,
                self.WARD_ID,
                5,
                self.R2,
                self._link(1, self.R1, 2, self.R2),
            )
        # and one that was never authorised at all
        with self.assertRaises(DataError):
            CAS.verify_chain_step_back(
                self.K_AUTH,
                self.K_MAC,
                self.WARD_ID,
                1,
                self.R1,
                (0, None, 1, self.R1, bytes(32)),
            )

    def test_the_chain_refuses_every_way_of_lying_with_real_links(self):
        """Each link here is individually authentic; only its placement is wrong. That is
        the interesting case -- forged links are the easy half."""
        # a gap, which is how a fork stays invisible
        with self.assertRaises(DataError):
            CAS.verify_chain_step(
                self.K_AUTH,
                self.K_MAC,
                self.WARD_ID,
                0,
                None,
                self._link(0, None, 2, self.R2),
            )
        # a link from another branch
        with self.assertRaises(DataError):
            CAS.verify_chain_step(
                self.K_AUTH,
                self.K_MAC,
                self.WARD_ID,
                1,
                self.R1,
                self._link(1, self.R2, 2, self.R2),
            )
        # a link that starts somewhere the running head is not
        with self.assertRaises(DataError):
            CAS.verify_chain_step(
                self.K_AUTH,
                self.K_MAC,
                self.WARD_ID,
                5,
                self.R1,
                self._link(1, self.R1, 2, self.R2),
            )
        # and one that was never authorised at all
        with self.assertRaises(DataError):
            CAS.verify_chain_step(
                self.K_AUTH,
                self.K_MAC,
                self.WARD_ID,
                0,
                None,
                (0, None, 1, self.R1, bytes(32)),
            )


class TestWardWmAuthorisation(unittest.TestCase):
    """The authorisation a WM checks: over MAC HEADS, never roots.

    A WM stores `(counter, mac)` and nothing else, so signing what it stores means it never has to
    be sent a root to verify an advance. That is the whole reason this is not `sig_commit`, which
    covers the same bytes as `auth_commit` and therefore names roots.
    """

    _K_SIG = b"\x11" * 32
    _K_MAC = b"\x33" * 32
    # The signing path takes ROOTS -- `transition_macs` is the one place a counter meets a root,
    # so a test that handed `wm_sig` macs directly would be exercising a path no caller has.
    _ROOT_A = b"\x55" * 32
    _ROOT_B = b"\x66" * 32
    _MAC_A = b"\xaa" * 32
    _MAC_B = b"\xbb" * 32

    def _mac(self, counter, root):
        """What the WM would hold for this (counter, root) -- the verifier's vantage point."""
        return A.root_mac(self._K_MAC, self._ward_id(), counter, root)

    def _ward_id(self):
        from trezor.crypto.curve import ed25519

        return ed25519.publickey(self._K_SIG)

    def test_a_signature_verifies_against_ward_id_alone(self):
        """`ward_id` IS the verifying key, so a WM needs nothing but the identifier it keys by."""
        wid = self._ward_id()
        sig = CAS.wm_sig(
            self._K_SIG, self._K_MAC, wid, 41, self._ROOT_A, 42, self._ROOT_B
        )
        self.assertTrue(
            CAS.verify_wm_sig(wid, 41, self._mac(41, self._ROOT_A), 42, self._mac(42, self._ROOT_B), sig)
        )

    def test_it_binds_both_endpoints(self):
        """Binding only the destination would let an authorisation be lifted out of its place and
        replayed after a different predecessor -- exactly what a compare-and-swap must prevent."""
        wid = self._ward_id()
        sig = CAS.wm_sig(
            self._K_SIG, self._K_MAC, wid, 41, self._ROOT_A, 42, self._ROOT_B
        )

        # a different predecessor
        self.assertFalse(
            CAS.verify_wm_sig(wid, 40, self._MAC_A, 42, self._MAC_B, sig)
        )
        self.assertFalse(
            CAS.verify_wm_sig(wid, 41, self._MAC_B, 42, self._MAC_B, sig)
        )
        # a different destination
        self.assertFalse(
            CAS.verify_wm_sig(wid, 41, self._MAC_A, 43, self._MAC_B, sig)
        )
        self.assertFalse(
            CAS.verify_wm_sig(wid, 41, self._MAC_A, 42, self._MAC_A, sig)
        )

    def test_another_wallet_cannot_use_it(self):
        wid = self._ward_id()
        from trezor.crypto.curve import ed25519

        sig = CAS.wm_sig(
            self._K_SIG, self._K_MAC, wid, 41, self._ROOT_A, 42, self._ROOT_B
        )
        other = ed25519.publickey(b"\x22" * 32)
        self.assertFalse(
            CAS.verify_wm_sig(other, 41, self._MAC_A, 42, self._MAC_B, sig)
        )

    def test_head_init_cannot_be_replayed_as_an_advance(self):
        """Its own tag, so the authorisation that opens a wallet's history cannot be re-presented
        as a step within it."""
        wid = self._ward_id()
        init = CAS.head_init_sig(self._K_SIG, wid, self._MAC_A)
        self.assertTrue(CAS.verify_head_init_sig(wid, self._MAC_A, init))
        # the same bytes, offered as a 0 -> 0 advance
        self.assertFalse(
            CAS.verify_wm_sig(wid, 0, self._MAC_A, 0, self._MAC_A, init)
        )

        advance = CAS.wm_sig(self._K_SIG, self._K_MAC, wid, 0, self._ROOT_A, 0, self._ROOT_A)
        self.assertFalse(CAS.verify_head_init_sig(wid, self._MAC_A, advance))

    def test_the_tag_is_the_only_thing_separating_the_two_authenticators(self):
        """WHAT CHANGED, AND WHY THIS TEST STILL MATTERS.

        The device and the WM authenticators used to cover different operands -- roots and mac
        heads -- and this test asserted they could not be confused because of that. They now cover
        IDENTICAL bytes, deliberately: the same statement made to two verifiers holding different
        secrets. So the operand difference is gone and the TAG is the whole of the separation,
        which makes pinning it more important than it was, not less.

        Domain separation still holds where it has to: every tag in the family produces a
        different preimage, and the length prefix means no tag can be re-split into another
        however the lengths move.
        """
        wid = self._ward_id()
        commit = CAS.transition_preimage(
            CAS.TAG_COMMIT, wid, 41, self._MAC_A, 42, self._MAC_B
        )
        for other in (CAS.TAG_REVERT, CAS.TAG_WM_HEAD, CAS.TAG_WM_INIT):
            self.assertNotEqual(
                commit,
                CAS.transition_preimage(other, wid, 41, self._MAC_A, 42, self._MAC_B),
            )

        # ...and the operands really are identical now, which is the point of the change: an
        # auth_commit and a wm_sig over the same transition cover the same bytes.
        self.assertEqual(
            CAS.transition_preimage(
                CAS.TAG_WM_HEAD, wid, 41, self._MAC_A, 42, self._MAC_B
            )[1 + len(CAS.TAG_WM_HEAD) :],
            commit[1 + len(CAS.TAG_COMMIT) :],
        )

    def test_operands_must_be_fixed_width(self):
        """Same reason as everywhere else in WARD: a short operand lets the preimage be re-split."""
        wid = self._ward_id()
        with self.assertRaises(DataError):
            CAS.transition_preimage(CAS.TAG_WM_HEAD, wid[:31], 0, self._MAC_A, 1, self._MAC_B)
        with self.assertRaises(DataError):
            CAS.transition_preimage(CAS.TAG_WM_HEAD, wid, 0, self._MAC_A[:31], 1, self._MAC_B)
        with self.assertRaises(DataError):
            CAS.transition_preimage(CAS.TAG_WM_HEAD, wid, 0, self._MAC_A, 1, self._MAC_B + b"\x00")

    def test_known_answer(self):
        """Fixed vectors, so this agrees with `tests/ward_keys.py` -- which implements the same
        two preimages independently, over `trezorlib._ed25519` rather than the crypto module. A
        host that computes these differently would be caught here rather than at the WM, and the
        oracle deliberately shares no code with this side: agreement by construction proves
        nothing."""
        wid = self._ward_id()
        self.assertEqual(
            wid,
            bytes.fromhex(
                "d04ab232742bb4ab3a1368bd4615e4e6d0224ab71a016baf8520a332c9778737"
            ),
        )
        self.assertEqual(
            CAS.transition_preimage(CAS.TAG_WM_HEAD, wid, 41, self._MAC_A, 42, self._MAC_B),
            bytes.fromhex(
                "115741524420574d20434f4d4d4954207631"
                "d04ab232742bb4ab3a1368bd4615e4e6d0224ab71a016baf8520a332c9778737"
                "00000029" + "aa" * 32 + "0000002a" + "bb" * 32
            ),
        )
        self.assertEqual(
            CAS.wm_sig(
            self._K_SIG, self._K_MAC, wid, 41, self._ROOT_A, 42, self._ROOT_B
        ),
            bytes.fromhex(
                "ec1bf2e467728ac99a5f380895121e58d176ef5a93cf6ae5266875571d71610e"
                "07e00ffe1ad4fdb3adcf4d7366234232645d41a40be168c797bfa02e17206309"
            ),
        )
        # The INIT preimage is pinned as well as its signature, so a change to the tag fails
        # with a readable diff rather than an opaque 64-byte mismatch. `0f` is len("WARD WM
        # INIT v1"); both endpoints are (0, current_mac), there being no predecessor to name.
        self.assertEqual(
            CAS.transition_preimage(CAS.TAG_WM_INIT, wid, 0, self._MAC_A, 0, self._MAC_A),
            bytes.fromhex(
                "0f5741524420574d20494e4954207631"
                "d04ab232742bb4ab3a1368bd4615e4e6d0224ab71a016baf8520a332c9778737"
                "00000000" + "aa" * 32 + "00000000" + "aa" * 32
            ),
        )
        self.assertEqual(
            CAS.head_init_sig(self._K_SIG, wid, self._MAC_A),
            bytes.fromhex(
                "abf7c0028b8d9a9dd8d3b21bab5f5fd2c163e8b280f5ec395dbc1674c1f3d8e4"
                "dfc5bb3dbeeb516483862dc184e17241722b79eafd56045fc9d2c4d80af27506"
            ),
        )

    def test_a_malformed_signature_is_refused_not_raised(self):
        wid = self._ward_id()
        self.assertFalse(CAS.verify_wm_sig(wid, 0, self._MAC_A, 1, self._MAC_B, b""))
        self.assertFalse(
            CAS.verify_wm_sig(wid, 0, self._MAC_A, 1, self._MAC_B, b"\x00" * 63)
        )
        self.assertFalse(
            CAS.verify_wm_sig(wid, 0, self._MAC_A, 1, self._MAC_B, b"\x00" * 64)
        )


class TestWardRecordCommit(unittest.TestCase):
    """`offline_store.record_commit`: what an offer claim names a queued record by."""

    _WALLET = b"\xa0" * 16

    def _rec(self, identifier=b"addr1", value=b"one", pending=False, offered=False):
        return OS.encode_record(
            self._WALLET, "address", "btc", identifier, value, pending, offered
        )

    def test_the_flags_are_normalised_out(self):
        """A record is marked OFFERED after its claim is filed and loses PENDING when the claim
        settles, so a commitment covering the flags would stop matching the record it was filed
        for -- and the claim would silently decline to settle anything."""
        base = self._rec()
        for pending, offered in ((True, False), (False, True), (True, True)):
            self.assertEqual(
                OS.record_commit(base),
                OS.record_commit(self._rec(pending=pending, offered=offered)),
            )

    def test_the_value_and_the_identity_are_covered(self):
        """The point of the commitment. Slots are reused and a queued value can be replaced in
        place, so a claim that matched a different generation would settle a change that never
        landed -- clearing a record the user still expects to be published."""
        base = OS.record_commit(self._rec())
        self.assertNotEqual(base, OS.record_commit(self._rec(value=b"two")))
        self.assertNotEqual(base, OS.record_commit(self._rec(value=b"")))
        self.assertNotEqual(base, OS.record_commit(self._rec(identifier=b"addr2")))

    def test_a_change_of_form_is_a_different_record(self):
        """Compact and full records name the same entry differently, and a claim filed against
        one must not settle the other: the form is part of what was offered."""
        full = OS.encode_record(
            self._WALLET, "address", "btc", b"addr1", b"one", True, False
        )
        compact = OS.encode_record(
            self._WALLET, "address", "btc", b"addr1", b"one", True, False, compact=True
        )
        self.assertNotEqual(OS.record_commit(full), OS.record_commit(compact))

    def test_it_is_stable(self):
        """Re-encoding the same record must produce the same commitment, or a claim would never
        match the record it was filed for."""
        self.assertEqual(OS.record_commit(self._rec()), OS.record_commit(self._rec()))
        self.assertEqual(len(OS.record_commit(self._rec())), 32)


class TestWardLeafOneofIsStrict(unittest.TestCase):
    """`leaf.read_leaf_*`: the manual oneof is read canonically, or refused.

    The codegen has no `oneof`, so `encoding` is a plain field. Two implementations could
    therefore disagree about which arm a message is -- and the disagreement lands on the commit
    preimage, which is what the trie hashes, so it is a different leaf and a different root.
    Not a forgery: the device computes its own commit and trusts only its own root. It is
    divergence, and divergence here is a proof the device cannot reproduce.
    """

    class _Sealed:
        def __init__(self, nonce=None, tag=None, ct=b"x"):
            self.nonce = b"\x00" * 12 if nonce is None else nonce
            self.tag = b"\x00" * 16 if tag is None else tag
            self.ct = ct

    class _Clear:
        def __init__(self, content=b"v"):
            self.content = content

    class _Content:
        def __init__(self, encoding=None, encrypted=None, plaintext=None):
            self.encoding = encoding
            self.encrypted = encrypted
            self.plaintext = plaintext

    def test_an_unknown_encoding_is_refused_rather_than_normalised(self):
        """It used to read as "not plaintext" and therefore as sealed. A later build that gives
        encoding 2 a meaning would frame those bytes differently and commit to a different leaf
        for a message this build had already accepted."""
        msg = self._Content(encoding=2, encrypted=self._Sealed())
        with self.assertRaises(DataError):
            L.read_leaf_content(msg)

    def test_setting_both_arms_is_refused(self):
        """Firmware dispatched on the discriminator, the host twins on field presence, so this
        framed one way on the device and the other way on the host."""
        msg = self._Content(encoding=0, encrypted=self._Sealed(), plaintext=self._Clear())
        with self.assertRaises(DataError):
            L.read_leaf_content(msg)

    def test_a_sealed_part_must_carry_a_real_nonce_and_tag(self):
        """Both are fixed by the AEAD. A short one reached the cipher before."""
        for bad in (self._Sealed(nonce=b"\x00" * 11), self._Sealed(tag=b"\x00" * 15)):
            with self.assertRaises(DataError):
                L.read_leaf_content(self._Content(encoding=0, encrypted=bad))

    def test_the_canonical_forms_still_read(self):
        """The strictness must not cost the two shapes that actually travel: a sealed part, and
        the empty content that is how a delete is represented."""
        part = L.read_leaf_content(self._Content(encoding=0, encrypted=self._Sealed()))
        self.assertEqual(part[0], L.ENC_ENCRYPTED)
        self.assertEqual(part[3], b"x")

        empty = L.read_leaf_content(self._Content(encoding=1, plaintext=self._Clear(b"")))
        self.assertTrue(L.is_delete(empty))

        self.assertEqual(L.read_leaf_content(None), None)


if __name__ == "__main__":
    unittest.main()
