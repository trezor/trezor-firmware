# flake8: noqa: F403,F405
from common import *  # isort:skip

from trezor.crypto.hashlib import sha256
from trezor.wire import DataError

from apps.ward import attest as A
from apps.ward import transition as TR
from apps.ward import round as ROUND
from apps.ward import leaf as L
from apps.ward import offline_store as OS
from apps.ward.attest import EMPTY_ROOT
from apps.ward.keys import _scope, entry_key
from apps.ward.leaf import (
    EMPTY,
    is_delete,
    leaf_hash,
    leaf_hash_of,
    open_content,
    open_identity,
    pack_content,
    pack_identity,
    seal_content,
    seal_identity,
    unpack_content,
    unpack_identity,
    value_digest,
)
from apps.ward.root import root_for_write
from apps.ward.trie import (
    addr_bit,
    compute_new_root,
    internal_hash,
    reconstruct,
    validate_proof_shape,
    verify_membership,
    verify_nonmembership,
)


def verify_wm_sig(ward_id, fc, fr, tc, tr, sig, tag=TR.TAG_WM_HEAD, session_nonce=b""):
    """What the WM checks, against the session nonce it holds -- the WM's side, so it lives
    here."""
    from trezor.crypto.curve import ed25519

    if len(sig) != 64:
        return False
    try:
        return ed25519.verify(
            ward_id, sig, TR.transition_preimage(tag, ward_id, fc, fr, tc, tr) + session_nonce
        )
    except Exception:
        return False


def verify_head_init_sig(ward_id, counter, root, sig):
    """What the WM checks before adopting a wallet it has never seen."""
    return verify_wm_sig(ward_id, counter, root, counter, root, sig, TR.TAG_WM_INIT)


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

        # entry_key(K_path, app_id="bitcoin", identifier=b"alice", device_id=7)
        ENTRY_KEY = bytes.fromhex(
            "5100f145ed3ad92afd590ddcce41a54f35acd588231d63b5531aae8680e30220"
        )
        self.assertEqual(entry_key(k_path, "bitcoin", b"alice", 7), ENTRY_KEY)
        self.assertEqual(
            entry_key(k_path, "bitcoin", b"alice"),
            bytes.fromhex(
                "b6675b7ef8dbf0bc5e07834035afe943a8e98737b7a38653950dda19c3ffb7f0"
            ),
        )

        # The one global key set that seals the two leaf parts.
        K_IDENT = bytes.fromhex(
            "308afbfccfbadb30d40cf6bdb2aeee95f893327583bceb9c8e2ffa1533e41b32"
        )
        K_DATA = bytes.fromhex(
            "8e274334f32b92bdf59969a3be5edac66deaaf1b9c6df46b772fa526ccef78e1"
        )
        self.assertEqual(slip21_key(SEED, [b"ward", b"K_ident"]), K_IDENT)
        self.assertEqual(slip21_key(SEED, [b"ward", b"K_data"]), K_DATA)

    def test_scope_layout(self):
        """The offline store's record name (not the trie path):
        scope = app_id || 0x00 || key_type || 0x00 || device_id(1B)."""
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

    def test_nul_in_app_id_is_unambiguous(self):
        """leaf_identity length-prefixes app_id, so NUL is ordinary data in it: the re-split that
        the offline store's NUL-delimited scope must refuse cannot happen here."""
        k_path = slip21_key(SEED, [b"ward", b"K_path"])
        self.assertNotEqual(
            entry_key(k_path, "a\x00b", b"c"), entry_key(k_path, "a", b"\x00bc")
        )
        self.assertEqual(
            pack_identity(b"c", "a\x00b"), b"\x00\x03a\x00bc"
        )

    def test_identifier_may_contain_nul(self):
        """identifier is the terminal field, so NUL in it is unambiguous and allowed."""
        k_path = slip21_key(SEED, [b"ward", b"K_path"])
        a = entry_key(k_path, "app", b"\x00lead")
        b = entry_key(k_path, "app", b"lead")
        self.assertNotEqual(a, b)
        self.assertEqual(len(a), 32)

    def test_domain_separation(self):
        """Changing any leaf_identity field must change the path."""
        k_path = slip21_key(SEED, [b"ward", b"K_path"])
        base = entry_key(k_path, "app", b"id")
        self.assertNotEqual(base, entry_key(k_path, "other", b"id"))
        self.assertNotEqual(base, entry_key(k_path, "app", b"other"))
        self.assertNotEqual(base, entry_key(k_path, "app", b"id", 1))
        # and a different K_path (i.e. a different wallet/passphrase) must too
        other = slip21_key(bytes.fromhex("22" * 64), [b"ward", b"K_path"])
        self.assertNotEqual(base, entry_key(other, "app", b"id"))


class TestWardLeaf(unittest.TestCase):
    """The leaf format of docs/ward/ward_leaf_encryption.md: AES-256-GCM parts, domain-only AAD, and a
    commitment to the sealed content alone. The known answers are byte-identical to the
    service-channel branch's `test_apps.ward.security.py::test_leaf_known_answer`."""

    K_IDENT = bytes.fromhex(
        "308afbfccfbadb30d40cf6bdb2aeee95f893327583bceb9c8e2ffa1533e41b32"
    )
    K_DATA = bytes.fromhex(
        "8e274334f32b92bdf59969a3be5edac66deaaf1b9c6df46b772fa526ccef78e1"
    )
    SEALED_CONTENT = bytes.fromhex(
        "015a5a5a5a5a5a5a5a5a5a5a5aaea42289df08d668e7ebc4f7505773b1b86985acabee6c38"
        "ee32ae912cf36b441766be2b98dd"
    )
    SEALED_IDENTITY = bytes.fromhex(
        "01595959595959595959595959b1bebe6cf1fd9cb91c8a2bb1dc7e9bbeac9cc0f95e938c293c"
        "0ba8c12134"
    )

    def test_known_answer(self):
        self.assertEqual(
            seal_content(self.K_DATA, "address", 5, b"data_alice", b"Z" * 12),
            self.SEALED_CONTENT,
        )
        self.assertEqual(
            seal_identity(self.K_IDENT, b"alice", "bitcoin", 7, b"Y" * 12),
            self.SEALED_IDENTITY,
        )
        self.assertEqual(
            open_content(self.K_DATA, self.SEALED_CONTENT),
            ("address", 5, b"data_alice"),
        )
        self.assertEqual(
            open_identity(self.K_IDENT, self.SEALED_IDENTITY), (b"alice", b"bitcoin", 7)
        )
        self.assertEqual(
            value_digest(self.SEALED_CONTENT),
            sha256(b"\x03" + self.SEALED_CONTENT).digest(),
        )

    def test_pack_layouts(self):
        self.assertEqual(
            pack_content("address", 5, b"data_alice"),
            b"\x07address\x00\x00\x00\x05data_alice",
        )
        self.assertEqual(
            pack_identity(b"alice", "bitcoin", 7), b"\x07\x07bitcoinalice"
        )
        # device_id is always one byte; 0x00 is an entry shared by all devices
        self.assertEqual(pack_identity(b"a", "b"), b"\x00\x01ba")
        self.assertEqual(unpack_identity(pack_identity(b"a", "b", 9)), (b"a", b"b", 9))
        self.assertEqual(
            unpack_content(pack_content("pointer", 3, b"")), ("pointer", 3, b"")
        )

    def test_truncated_identity_is_refused(self):
        for bad in (
            b"",  # no device_id
            b"\x00",  # no app_id length
            b"\x00\x05ab",  # shorter than its app_id
        ):
            with self.assertRaises(DataError):
                unpack_identity(bad)

    def test_the_identifier_runs_to_the_end(self):
        """No length prefix and no bound: trailing bytes are the identifier's."""
        long = b"x" * 70000
        self.assertEqual(unpack_identity(pack_identity(long, "b")), (long, b"b", 0))
        self.assertEqual(unpack_identity(b"\x00\x01b"), (b"", b"b", 0))

    def test_pack_identity_rejects_oversized_fields(self):
        for args in ((b"x", "a" * 256, 0), (b"x", "a", 256)):
            with self.assertRaises(DataError):
                pack_identity(*args)

    def test_parts_are_bound_to_key_domain_and_bytes(self):
        content = seal_content(self.K_DATA, "address", 1, b"v")
        identity = seal_identity(self.K_IDENT, b"id", "bitcoin")
        self.assertEqual(open_identity(self.K_IDENT, identity), (b"id", b"bitcoin", 0))
        for opener in (
            lambda: open_content(self.K_IDENT, content),  # wrong key
            lambda: open_identity(self.K_DATA, identity),
            lambda: L.open_sealed(
                self.K_DATA, L.DOMAIN_IDENTITY, content
            ),  # wrong domain
            lambda: open_content(self.K_DATA, content[:-1] + bytes([content[-1] ^ 1])),
            lambda: open_content(self.K_DATA, content[:28]),  # short
            lambda: open_content(self.K_DATA, b"\x02" + content[1:]),  # unknown scheme
        ):
            with self.assertRaises(DataError):
                opener()

    def test_empty_value_is_not_a_delete(self):
        """b"" is a present value: its sealing is non-empty. Only EMPTY deletes."""
        sealed = seal_content(self.K_DATA, "address", 7, b"")
        self.assertEqual(len(sealed), 1 + 12 + 16 + 1 + 7 + 4)
        self.assertFalse(is_delete(sealed))
        self.assertTrue(is_delete(EMPTY))
        self.assertEqual(open_content(self.K_DATA, sealed), ("address", 7, b""))

    def test_fresh_nonce_per_write(self):
        a = seal_content(self.K_DATA, "address", 1, b"v")
        b = seal_content(self.K_DATA, "address", 1, b"v")
        self.assertNotEqual(a, b)

    def test_only_the_sealed_content_is_committed(self):
        key = bytes([7]) * 32
        self.assertEqual(
            leaf_hash(key, self.SEALED_CONTENT),
            leaf_hash_of(key, value_digest(self.SEALED_CONTENT)),
        )


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

    # The shared four-leaf vectors of `common/tests/fixtures/ward/trie.json` on the
    # service-channel branch (tools/ward_vectors.py), which `rust/trezor-ward` also folds.
    ROOT = bytes.fromhex(
        "6c2ec0a1be361cf8e8afcc1822b087bd8b9888a70821a1f62dd2546e9f382526"
    )
    MEMBER = bytes.fromhex(
        "be2974546978e3739e6d6da85c4be9f334ce32df2b9fd4b6ff1b55c0d57e9d44"
    )
    MEMBER_CONTENT = bytes.fromhex(
        "0131313131313131313131313141414141414141414141414141414141636970686572746578742d31"
    )
    MEMBER_PROOF = [
        bytes.fromhex(
            "0184355da313cb77a710c6f53429e8573c59c1394260e80fcabc7019b5fc7eda63"
        ),
        bytes.fromhex(
            "007a271d3b377de23bfd6cd7d07923eb57514b44357a92535609890f60109785a6"
        ),
    ]
    ABSENT = bytes.fromhex(
        "ffa63583dfa6706b87d284b86b0d693a161e4840aad2c5cf6b5d27c3b9621f7d"
    )
    WITNESS = bytes.fromhex(
        "d9ef8196557c9da69806fb5d777f4e5ad6d5c18593039e0ff62f9fdf003b0198"
    )
    WITNESS_COMMIT = bytes.fromhex(
        "e655f0c657f295b8b6cc120741675218f512aee8bd7e2e868cea2de3387215a4"
    )
    PROOF = [
        bytes.fromhex(
            "04a7757969f25dee0994042284b80c92ae39d8045607a483b71c51155f3b104d6b"
        ),
        bytes.fromhex(
            "010761c463fa1be75daeb38784a70aebdc51defee3ff879f83d42611b0b007a43b"
        ),
        bytes.fromhex(
            "007a271d3b377de23bfd6cd7d07923eb57514b44357a92535609890f60109785a6"
        ),
    ]
    # A one-leaf tree for the sealed-content checks: its root is the leaf itself.
    SOLO_KEY = bytes([0x5A]) * 32
    SOLO_CONTENT = b"\x01" + bytes(28) + b"ciphertext"

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
        """The sealed content, the proof and the root, byte-for-byte across implementations."""
        self.assertEqual(len(self.MEMBER_PROOF[0]), 33)
        self.assertTrue(
            verify_membership(
                self.MEMBER, self.MEMBER_CONTENT, self.MEMBER_PROOF, self.ROOT
            )
        )
        root = leaf_hash(self.SOLO_KEY, self.SOLO_CONTENT)
        self.assertTrue(verify_membership(self.SOLO_KEY, self.SOLO_CONTENT, [], root))

    def test_frozen_nonmembership_proof(self):
        """Absence is proved by the leaf that occupies the absent key's path."""
        self.assertTrue(
            verify_nonmembership(
                self.ABSENT, self.WITNESS, self.WITNESS_COMMIT, self.PROOF, self.ROOT
            )
        )

    def test_membership_against_a_wrong_root_fails(self):
        self.assertFalse(
            verify_membership(self.SOLO_KEY, self.SOLO_CONTENT, [], bytes(32))
        )

    def test_membership_of_a_mutated_leaf_fails(self):
        """Any edit to the sealed content changes the commitment, hence the leaf and root;
        so does moving it to another path."""
        root = leaf_hash(self.SOLO_KEY, self.SOLO_CONTENT)
        self.assertFalse(
            verify_membership(self.SOLO_KEY, self.SOLO_CONTENT + b"x", [], root)
        )
        self.assertFalse(
            verify_membership(bytes([0x5B]) * 32, self.SOLO_CONTENT, [], root)
        )

    def test_witness_equal_to_target_proves_nothing(self):
        """Otherwise a membership proof would double as a proof of absence."""
        self.assertFalse(
            verify_nonmembership(
                self.WITNESS, self.WITNESS, self.WITNESS_COMMIT, self.PROOF, self.ROOT
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
        shifted_key = self.WITNESS + self.WITNESS_COMMIT[:1]
        shifted_commit = self.WITNESS_COMMIT[1:]
        self.assertTrue(shifted_key != self.WITNESS)
        self.assertEqual(
            shifted_key + shifted_commit, self.WITNESS + self.WITNESS_COMMIT
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
                self.WITNESS, shifted_key, shifted_commit, self.PROOF, self.ROOT
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
                TR.transition_preimage(TR.TAG_COMMIT, bad, 1, ok, 2, ok)
            with self.assertRaises(DataError):
                TR.transition_preimage(TR.TAG_COMMIT, ok, 1, bad, 2, ok)
            with self.assertRaises(DataError):
                A.attestation_preimage(bytes(32), bytes(32), 0, ok, 1, bad, 0)

        # and a shifted (from_mac, to_counter, to_mac) can no longer reproduce a genuine
        # authorisation, which it could byte-for-byte before
        wid, fm, tm = bytes(range(32)), bytes([7]) * 32, bytes([9]) * 32
        genuine = TR.transition_preimage(TR.TAG_COMMIT, wid, 2, fm, 3, tm)
        with self.assertRaises(DataError):
            TR.transition_preimage(
                TR.TAG_COMMIT,
                wid,
                2,
                fm + (3).to_bytes(4, "big")[:1],
                int.from_bytes((3).to_bytes(4, "big")[1:] + tm[:1], "big"),
                tm[1:],
            )
        self.assertEqual(len(genuine), 1 + len(TR.TAG_COMMIT) + 32 + 4 + 32 + 4 + 32)

    def test_relabelled_split_bit_is_rejected(self):
        """THE malleability attack, and the reason split_bit is inside the node hash.

        The sibling hash is untouched and the chain would still fold to the same value
        under the old format, where the bit index was unauthenticated metadata. A host
        that could relabel hops could manufacture a witness relationship and prove a
        PRESENT key absent.
        """
        # the leaf-most step branches on bit 4; relabel it 5, still a well-shaped path
        relabelled = [bytes([5]) + self.PROOF[0][1:]] + self.PROOF[1:]
        try:
            self.assertFalse(
                verify_nonmembership(
                    self.ABSENT, self.WITNESS, self.WITNESS_COMMIT, relabelled, self.ROOT
                )
            )
        except DataError:
            pass  # rejected by the shape check before any hashing -- also correct

    def test_proof_shape_is_enforced(self):
        """A proof must describe a real root-to-leaf path before anything is hashed."""
        good = self.PROOF[0]
        for bad in (good[:32], good + b"\x00"):  # wrong element length either way
            with self.assertRaises(DataError):
                validate_proof_shape([bad])

        # Split bits must strictly increase from the root DOWN, and a proof is ordered
        # leaf-to-root -- so a well-formed one has them DECREASING in list order. Getting
        # that backwards writes a test that asserts nothing, which is what happened here
        # while the skiplen arithmetic was doing the rejecting instead.
        with self.assertRaises(DataError):
            validate_proof_shape([bytes([2]) + good[1:], bytes([5]) + good[1:]])

        # ...and the same two, the right way round, are accepted
        self.assertEqual(
            len(
                validate_proof_shape(
                    [bytes([5]) + good[1:], bytes([2]) + good[1:]]
                )
            ),
            2,
        )

    def test_proof_length_is_bounded_by_the_key_space(self):
        """No cap is needed: split_bit is one byte and strictly increases, so a valid proof
        cannot exceed 256 elements however many the host sends."""
        full = [bytes([b]) + bytes(32) for b in range(255, -1, -1)]
        self.assertEqual(len(validate_proof_shape(full)), 256)
        with self.assertRaises(DataError):
            validate_proof_shape(full + [bytes([0]) + bytes(32)])


class TestWardComputeNewRoot(unittest.TestCase):
    """The device deriving the root that replaces the current one.

    Every case here is checked against the root a canonical REBUILD would produce, which
    is the property that matters: a device whose root drifts from the canonical one still
    verifies its own proofs happily, and only diverges when some other party rebuilds the
    tree -- at which point the whole entry set is unreachable. A test that merely asserted
    "some root came back" would not have caught either bug below.
    """

    def _key(self, bits):
        """A 32-byte path beginning with `bits`, padded with zeros."""
        out = bytearray(32)
        for i, b in enumerate(bits):
            if b:
                out[i // 8] |= 1 << (7 - (i % 8))
        return bytes(out)

    def _leaf(self, tag):
        """A sealed_content-shaped leaf; never opened, so only distinctness matters."""
        return b"\x01" + bytes(28) + tag

    def _commit(self, tag):
        return value_digest(self._leaf(tag))

    def _lh(self, key, tag):
        return leaf_hash_of(key, self._commit(tag))

    @staticmethod
    def _elem(split_bit, sibling):
        return bytes([split_bit]) + sibling

    def test_first_insert_needs_an_empty_device(self):
        """With no proof and no witness the device's own record is the only authority."""
        k = self._key([0])
        self.assertEqual(
            compute_new_root(k, None, self._leaf(b"a"), [], EMPTY_ROOT),
            self._lh(k, b"a"),
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

    def test_reconstruct_refuses_wrong_width_operands(self):
        """Checked in the fold itself, so no future caller can forget. A short key used to
        be an untyped IndexError out of `addr_bit`; a long one routed by its first 32 bytes."""
        lc = self._lh(self._key([1]), b"c")
        proof = [self._elem(0, lc)]
        for key in (bytes(31), bytes(33)):
            with self.assertRaises(DataError):
                reconstruct(bytes(32), proof, key)
        for start in (bytes(31), bytes(33)):
            with self.assertRaises(DataError):
                reconstruct(start, proof, bytes(32))

    def test_insert_refuses_a_wrong_width_witness(self):
        """A DataError, not an IndexError: the read path that would have caught it first is
        skipped on a fresh device and an emptied tree, so insert checks for itself."""
        a, b, c = self._key([0, 1]), self._key([0]), self._key([1])
        root = internal_hash(0, self._lh(b, b"b"), self._lh(c, b"c"))
        proof = [self._elem(0, self._lh(c, b"c"))]
        for w_key, w_commit in (
            (b[:31], self._commit(b"b")),
            (b + b"\x00", self._commit(b"b")),
            (b, self._commit(b"b")[:31]),
        ):
            with self.assertRaises(DataError):
                compute_new_root(
                    a,
                    None,
                    self._leaf(b"a"),
                    proof,
                    root,
                    witness_entry_key=w_key,
                    witness_commit=w_commit,
                )

    def test_insert_witness_must_prove_absence_against_the_device_root(self):
        """Each failed claim raises, through the same check the read path uses."""
        a, b, c = self._key([0, 1]), self._key([0]), self._key([1])
        lb, lc = self._lh(b, b"b"), self._lh(c, b"c")
        root = internal_hash(0, lb, lc)
        good = [self._elem(0, lc)]

        def insert(proof, stored_root, w_key=b, w_commit=None):
            return compute_new_root(
                a,
                None,
                self._leaf(b"a"),
                proof,
                stored_root,
                witness_entry_key=w_key,
                witness_commit=w_commit or self._commit(b"b"),
            )

        # the honest call succeeds, so each refusal below is about the one thing changed
        insert(good, root)
        for bad in (
            lambda: insert(good, bytes(32)),  # not the device's root
            lambda: insert(good, None),  # unsettled root: refused before anything else
            lambda: insert(good, root, w_key=a, w_commit=self._commit(b"a")),  # itself
            lambda: insert(good, root, w_key=c, w_commit=self._commit(b"c")),  # off-path
            lambda: insert(good, root, w_commit=self._commit(b"x")),  # wrong commit
        ):
            with self.assertRaises(DataError):
                bad()
        # and a non-empty tree never accepts a witness-less insert, proof or not
        with self.assertRaises(DataError):
            compute_new_root(a, None, self._leaf(b"a"), good, root)

    def test_an_unsettled_root_is_refused_not_read_as_empty(self):
        """None is "cannot verify", and `root_for_write` refuses it before the trie is reached.

        Read as empty -- as it once was -- None authorised a witness-less first insert, so a
        device without a trusted root would let the host replace the tree.
        Every operation refuses it, including the one that would have succeeded.
        """
        k, b = self._key([0]), self._key([1])
        lk, lb = self._lh(k, b"k"), self._lh(b, b"b")
        proof = [self._elem(0, lb)]
        for call in (
            lambda: compute_new_root(k, None, self._leaf(b"k"), [], None),
            lambda: compute_new_root(
                k,
                None,
                self._leaf(b"k"),
                proof,
                None,
                witness_entry_key=b,
                witness_commit=self._commit(b"b"),
            ),
            lambda: compute_new_root(k, self._leaf(b"k"), None, proof, None),
            lambda: compute_new_root(
                k, self._leaf(b"k"), self._leaf(b"k2"), proof, None
            ),
        ):
            with self.assertRaises(DataError):
                call()
        # the same first insert succeeds against the EMPTY_ROOT an adoption stores
        self.assertEqual(
            compute_new_root(k, None, self._leaf(b"k"), [], EMPTY_ROOT), lk
        )

    def test_root_for_write_never_reads_none_as_empty(self):
        """Not even at counter 0: that is this device's floor, and a second device of a wallet
        with history starts there too. A writer is online, so it holds a real root."""
        with self.assertRaises(DataError):
            root_for_write(None)
        r = bytes(range(32))
        self.assertEqual(root_for_write(r), r)
        self.assertEqual(root_for_write(EMPTY_ROOT), EMPTY_ROOT)


class TestWardAttestation(unittest.TestCase):
    """The WM's freshness signature over (counter, root).

    IT SIGNS THE ROOT ITSELF. There used to be a keyed indirection -- `root_mac` under K_mac --
    which bounded the WM to REPLAYING a pair this wallet genuinely reached. It is gone, so a
    malicious WM can now name a root the wallet never held, and nothing in this class refuses
    that: `TestWardCas` does, by folding an `auth_commit` the WM cannot mint.

    What these tests still pin is the nonce binding, the signer, and the line between the live
    and archived verification paths -- which is the whole of what an attestation is now for.
    """

    # The well-known debug WM seed. Its public key is compiled into attest.py.
    WM_SEED = b"AUTHDB QM DEBUG KEY SEED v1 ...."
    WARD_ID = bytes(range(32))
    NONCE = bytes(range(32, 64))
    ROOT = bytes([7]) * 32
    # The head this step advanced FROM. The attestation names a transition, so every preimage
    # below has two ends; this is the one that is not under test.
    PREV = bytes([6]) * 32
    # A wall-clock second that is not a round number and not zero: a layout bug that
    # dropped the field or wrote it at the wrong width would still pass against 0.
    TIME = 0x0102030405060708

    def _sign(self, message, seed=None):
        from trezor.crypto.curve import ed25519

        return ed25519.sign(seed or self.WM_SEED, message)

    # THERE IS ONE VERIFICATION PATH NOW. `verify_archived_attestation` took the nonce as DATA
    # and answered "was this EVER a head", for a chain walk anchored on an archive and for
    # `rollback` proving its target was once authoritative. Both are gone, so the tests that
    # pinned the line between the two questions have nothing left to separate -- what remains is
    # that a signature bound to one round's nonce does not verify against another's, which
    # `test_every_signed_field_is_bound` already covers.

    def test_an_archived_attestation_cannot_be_re_dated(self):
        """WHY THE COUNTER SITS BESIDE THE ROOT, stated as the attack it prevents.

        Roots are content-addressed and REPEAT whenever content repeats -- change a label and
        change it back and the root returns. If a signature committed only to the root, a host
        holding an old attestation could present it for today's identical shape and the device
        would take a year-old tree as current: a silent rollback that reads as forward progress.

        Both are in the one signed preimage, so an archived attestation names one MOMENT rather
        than one shape.
        """
        at_41 = A.attestation_preimage(self.WARD_ID, self.NONCE, 40, self.PREV, 41, self.ROOT, self.TIME)
        at_99 = A.attestation_preimage(self.WARD_ID, self.NONCE, 98, self.PREV, 99, self.ROOT, self.TIME)
        self.assertNotEqual(at_41, at_99)

    def test_debug_key_matches_its_seed(self):
        """The compiled debug pubkey really is this seed's, or every test below is vacuous."""
        from trezor.crypto.curve import ed25519

        self.assertEqual(ed25519.publickey(self.WM_SEED), A._WM_PUBKEY_DEBUG)

    def test_production_key_is_unprovisioned(self):
        """Shipping with a placeholder is correct: a device that accepted a WM key from
        whoever offered one would be checking freshness against an adversary's clock."""
        self.assertEqual(A._WM_PUBKEY, bytes(32))

    def test_the_empty_tree_is_attestable_too(self):
        """An absent root encodes as EMPTY_ROOT rather than being skipped, so "empty" is still
        a state the WM can attest at a given counter -- otherwise it could not name one at all,
        and a wallet with nothing in it could never be synced."""
        empty5 = A.attestation_preimage(self.WARD_ID, self.NONCE, 4, self.PREV, 5, None, self.TIME)
        self.assertEqual(
            empty5,
            A.attestation_preimage(
                self.WARD_ID,
                self.NONCE,
                4,
                self.PREV,
                5,
                A.EMPTY_ROOT,
                self.TIME,
            ),
        )
        self.assertNotEqual(
            empty5,
            A.attestation_preimage(
                self.WARD_ID,
                self.NONCE,
                5,
                self.PREV,
                6,
                None,
                self.TIME,
            ),
        )
        self.assertNotEqual(
            empty5,
            A.attestation_preimage(
                self.WARD_ID,
                self.NONCE,
                4,
                self.PREV,
                5,
                self.ROOT,
                self.TIME,
            ),
        )

    def test_attestation_preimage_layout(self):
        """Both ends, in order, at fixed width -- and the version byte that says so."""
        mac = self.ROOT
        self.assertEqual(
            A.attestation_preimage(
                self.WARD_ID, self.NONCE, 4, self.PREV, 5, mac, self.TIME
            ),
            b"WARD ATTEST v1"
            + bytes([7])
            + self.NONCE
            + self.WARD_ID
            + (4).to_bytes(4, "big")
            + self.PREV
            + (5).to_bytes(4, "big")
            + mac
            + self.TIME.to_bytes(8, "big"),
        )

    def test_the_predecessor_is_bound_too(self):
        """The whole point of naming a step rather than a head: an attestation for the same
        destination but a different origin is a different statement, so a host cannot pair one
        with a link that merely ends in the right place."""
        self.assertNotEqual(
            A.attestation_preimage(
                self.WARD_ID, self.NONCE, 4, self.PREV, 5, self.ROOT, self.TIME
            ),
            A.attestation_preimage(
                self.WARD_ID, self.NONCE, 4, bytes([9]) * 32, 5, self.ROOT, self.TIME
            ),
        )

    def test_genesis_attests_itself(self):
        """Counter 0 has no predecessor, so the step is `(0, empty) -> (0, empty)`. It cannot be
        confused with a real transition: every one of those advances the counter by exactly one,
        so no genuine step has from == to."""
        self.assertEqual(
            A.attestation_preimage(
                self.WARD_ID,
                self.NONCE,
                0,
                None,
                0,
                None,
                self.TIME,
            ),
            A.attestation_preimage(
                self.WARD_ID,
                self.NONCE,
                0,
                A.EMPTY_ROOT,
                0,
                A.EMPTY_ROOT,
                self.TIME,
            ),
        )

    def test_a_genuine_attestation_verifies(self):
        mac = self.ROOT  # the attested 32 bytes ARE the root now
        sig = self._sign(
            A.attestation_preimage(self.WARD_ID, self.NONCE, 4, self.PREV, 5, mac, self.TIME)
        )
        self.assertTrue(
            A.verify_attestation(self.WARD_ID, self.NONCE, 4, self.PREV, 5, mac, self.TIME, sig)
        )

    def test_every_signed_field_is_bound(self):
        """Changing anything the signature covers must break it -- notably the nonce, which
        is what stops a host stockpiling anchors and replaying one later."""
        mac = self.ROOT  # the attested 32 bytes ARE the root now
        sig = self._sign(
            A.attestation_preimage(self.WARD_ID, self.NONCE, 4, self.PREV, 5, mac, self.TIME)
        )

        self.assertFalse(
            A.verify_attestation(self.WARD_ID, bytes(32), 4, self.PREV, 5, mac, self.TIME, sig)
        )
        self.assertFalse(
            A.verify_attestation(self.WARD_ID, self.NONCE, 5, self.PREV, 6, mac, self.TIME, sig)
        )
        self.assertFalse(
            A.verify_attestation(self.WARD_ID, self.NONCE, 4, self.PREV, 5, bytes(32), self.TIME, sig)
        )
        self.assertFalse(
            A.verify_attestation(bytes(32), self.NONCE, 4, self.PREV, 5, mac, self.TIME, sig)
        )
        self.assertFalse(
            A.verify_attestation(self.WARD_ID, self.NONCE, 4, self.PREV, 5, mac, self.TIME + 1, sig)
        )

    def test_another_signer_is_refused(self):
        mac = self.ROOT  # the attested 32 bytes ARE the root now
        pre = A.attestation_preimage(self.WARD_ID, self.NONCE, 4, self.PREV, 5, mac, self.TIME)
        sig = self._sign(pre, seed=b"NOT THE WARD MANAGER DEBUG KEY!!")
        self.assertFalse(
            A.verify_attestation(self.WARD_ID, self.NONCE, 4, self.PREV, 5, mac, self.TIME, sig)
        )

    def test_a_zero_signature_never_verifies(self):
        """Not paranoia. Against the all-zero placeholder key an all-zero signature is a
        DEGENERATE acceptance -- R=0, S=0 satisfies [S]B = R + [k]A when A is the identity
        -- so an unprovisioned device would accept an attestation carrying no signature at
        all. Both halves are refused: the zero signature, and verifying against the
        placeholder key.
        """
        mac = self.ROOT  # the attested 32 bytes ARE the root now
        self.assertFalse(
            A.verify_attestation(self.WARD_ID, self.NONCE, 4, self.PREV, 5, mac, self.TIME, bytes(64))
        )

    def test_a_malformed_signature_is_refused(self):
        mac = self.ROOT  # the attested 32 bytes ARE the root now
        sig = self._sign(
            A.attestation_preimage(
                self.WARD_ID,
                self.NONCE,
                4,
                self.PREV,
                5,
                mac,
                self.TIME,
            )
        )
        self.assertFalse(
            A.verify_attestation(
                self.WARD_ID,
                self.NONCE,
                4,
                self.PREV,
                5,
                mac,
                self.TIME,
                sig[:63],
            )
        )
        self.assertFalse(
            A.verify_attestation(
                self.WARD_ID,
                self.NONCE,
                4,
                self.PREV,
                5,
                mac,
                self.TIME,
                sig + b"\x00",
            )
        )


class TestWardCas(unittest.TestCase):
    """Authorising a transition from one root to the next.

    A MAC rather than a signature: K_auth is seed-derived, so exactly the parties that
    need to verify a transition -- the other devices of this wallet -- can, and nobody
    else. See transition.py for when that would need to become a signature.
    """

    K_AUTH = bytes(range(32))
    WARD_ID = bytes(range(32, 64))
    R1 = bytes([1]) * 32
    R2 = bytes([2]) * 32

    def _link(self, f, fr, t, tr):
        return (f, fr, t, tr, TR.auth_commit(self.K_AUTH, self.WARD_ID, f, fr, t, tr))

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
        mine = TR.auth_commit(self.K_AUTH, self.WARD_ID, 41, self.R1, 42, self.R2)
        theirs_root = bytes([3]) * 32

        # the winner's head at the same counter does not reproduce my authorisation
        self.assertFalse(
            TR.verify_auth_commit(
                self.K_AUTH, self.WARD_ID, 41, self.R1, 42, theirs_root, mine
            )
        )
        # ...and my own head does
        self.assertTrue(
            TR.verify_auth_commit(
                self.K_AUTH, self.WARD_ID, 41, self.R1, 42, self.R2, mine
            )
        )
        # the from-state is bound too, so a claim filed from a different head cannot be
        # re-read as one filed from this one
        self.assertFalse(
            TR.verify_auth_commit(
                self.K_AUTH, self.WARD_ID, 41, theirs_root, 42, self.R2, mine
            )
        )

    def test_empty_root_sentinel(self):
        """A root inside a preimage is fixed-width, so the empty tree needs an encoding no
        real root can take. sha256(0x02), domain-separated from the leaf (0x00), internal (0x01)
        and value (0x03) tags -- spelled as a literal, so this asserts it really is that hash."""
        from trezor.crypto.hashlib import sha256

        self.assertEqual(A.EMPTY_ROOT, sha256(b"\x02").digest())

    def test_preimage_names_both_endpoints(self):
        """Binding only the destination would let a link be lifted out of its place in the
        history and replayed after a different predecessor -- which is what a chain exists
        to prevent."""
        m0, m1 = bytes([7]) * 32, bytes([9]) * 32
        pre = TR.transition_preimage(TR.TAG_COMMIT, self.WARD_ID, 4, m0, 5, m1)
        self.assertEqual(
            pre,
            bytes([len(TR.TAG_COMMIT)])
            + TR.TAG_COMMIT
            + self.WARD_ID
            + (4).to_bytes(4, "big")
            + m0
            + (5).to_bytes(4, "big")
            + m1,
        )
        # The endpoints are ROOTS again, so the empty tree is encoded HERE -- an absent root
        # becomes the EMPTY_ROOT stand-in rather than being skipped, which is what keeps the
        # preimage fixed-width when the tree is empty at either end. That normalisation used to
        # live one layer down, in `root_mac`.
        self.assertEqual(
            TR.transition_preimage(TR.TAG_COMMIT, self.WARD_ID, 0, None, 1, m1),
            TR.transition_preimage(
                TR.TAG_COMMIT, self.WARD_ID, 0, A.EMPTY_ROOT, 1, m1
            ),
        )

    def test_every_field_is_bound(self):
        mac = TR.auth_commit(self.K_AUTH, self.WARD_ID, 4, self.R1, 5, self.R2)
        self.assertTrue(
            TR.verify_auth_commit(
                self.K_AUTH, self.WARD_ID, 4, self.R1, 5, self.R2, mac
            )
        )
        for args in (
            (self.K_AUTH, self.WARD_ID, 3, self.R1, 5, self.R2),
            (self.K_AUTH, self.WARD_ID, 4, self.R2, 5, self.R2),
            (self.K_AUTH, self.WARD_ID, 4, self.R1, 6, self.R2),
            (self.K_AUTH, self.WARD_ID, 4, self.R1, 5, self.R1),
            (self.K_AUTH, bytes(32), 4, self.R1, 5, self.R2),
            (bytes(32), self.WARD_ID, 4, self.R1, 5, self.R2),
        ):
            self.assertFalse(TR.verify_auth_commit(*args, mac))

    def test_a_revert_is_not_a_commit(self):
        """Same endpoints, different meaning. Sharing a tag would let a rollback be
        replayed as an ordinary write, or the reverse."""
        commit = TR.auth_commit(self.K_AUTH, self.WARD_ID, 4, self.R1, 5, self.R2)
        revert = TR.auth_commit(
            self.K_AUTH, self.WARD_ID, 4, self.R1, 5, self.R2, TR.TAG_REVERT
        )
        self.assertNotEqual(commit, revert)
        self.assertFalse(
            TR.verify_auth_commit(
                self.K_AUTH, self.WARD_ID, 4, self.R1, 5, self.R2, revert
            )
        )

    def test_a_genuine_chain_folds_to_its_head(self):
        counter, root = 0, None
        for link in (
            self._link(0, None, 1, self.R1),
            self._link(1, self.R1, 2, self.R2),
        ):
            counter, root, _reverted = TR.verify_chain_step(
                self.K_AUTH, self.WARD_ID, counter, root, link
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
            counter, root, _reverted = TR.verify_chain_step_back(
                self.K_AUTH, self.WARD_ID, counter, root, link
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
            TR.verify_chain_step(
                self.K_AUTH, self.WARD_ID, 0, None, candidate
            )

        # backward, anchored at (1, R1), only the real one is admissible
        counter, root, _r = TR.verify_chain_step_back(
            self.K_AUTH, self.WARD_ID, 1, self.R1, real
        )
        self.assertEqual((counter, root), (0, None))
        with self.assertRaises(DataError):
            TR.verify_chain_step_back(
                self.K_AUTH, self.WARD_ID, 1, self.R1, orphan
            )

    def test_a_batch_link_folds_in_both_directions(self):
        """One transition carrying MAX_BATCH changes is a single genuine step, either way."""
        n = TR.MAX_BATCH
        link = self._link(0, None, n, self.R2)
        self.assertEqual(
            TR.verify_chain_step(self.K_AUTH, self.WARD_ID, 0, None, link)[:2], (n, self.R2)
        )
        self.assertEqual(
            TR.verify_chain_step_back(self.K_AUTH, self.WARD_ID, n, self.R2, link)[:2],
            (0, None),
        )

    def test_the_backward_chain_refuses_every_way_of_lying_with_real_links(self):
        """The mirror of the forward case: authentic links, wrong placement."""
        # a jump longer than any batch may carry
        far = TR.MAX_BATCH + 1
        with self.assertRaises(DataError):
            TR.verify_chain_step_back(
                self.K_AUTH,
                self.WARD_ID,
                far,
                self.R2,
                self._link(0, None, far, self.R2),
            )
        # a link ending at another branch's root at the right counter
        with self.assertRaises(DataError):
            TR.verify_chain_step_back(
                self.K_AUTH,
                self.WARD_ID,
                2,
                self.R1,
                self._link(1, self.R1, 2, self.R2),
            )
        # a link ending at a counter the walk is not at
        with self.assertRaises(DataError):
            TR.verify_chain_step_back(
                self.K_AUTH,
                self.WARD_ID,
                5,
                self.R2,
                self._link(1, self.R1, 2, self.R2),
            )
        # and one that was never authorised at all
        with self.assertRaises(DataError):
            TR.verify_chain_step_back(
                self.K_AUTH,
                self.WARD_ID,
                1,
                self.R1,
                (0, None, 1, self.R1, bytes(32)),
            )

    def test_the_chain_refuses_every_way_of_lying_with_real_links(self):
        """Each link here is individually authentic; only its placement is wrong. That is
        the interesting case -- forged links are the easy half."""
        # a jump longer than any batch may carry
        with self.assertRaises(DataError):
            TR.verify_chain_step(
                self.K_AUTH,
                self.WARD_ID,
                0,
                None,
                self._link(0, None, TR.MAX_BATCH + 1, self.R2),
            )
        # a link from another branch
        with self.assertRaises(DataError):
            TR.verify_chain_step(
                self.K_AUTH,
                self.WARD_ID,
                1,
                self.R1,
                self._link(1, self.R2, 2, self.R2),
            )
        # a link that starts somewhere the running head is not
        with self.assertRaises(DataError):
            TR.verify_chain_step(
                self.K_AUTH,
                self.WARD_ID,
                5,
                self.R1,
                self._link(1, self.R1, 2, self.R2),
            )
        # and one that was never authorised at all
        with self.assertRaises(DataError):
            TR.verify_chain_step(
                self.K_AUTH,
                self.WARD_ID,
                0,
                None,
                (0, None, 1, self.R1, bytes(32)),
            )


class TestWardWmAuthorisation(unittest.TestCase):
    """The authorisation a WM checks: over ROOTS, the identical bytes `auth_commit` MACs.

    A WM stores `(counter, root)` and checks the predecessor against the `from` end, so signing the
    root transition means every operand it acts on is inside what it verifies. There used to be a
    mac layer between the two -- `root_mac` under K_mac, which these operands were -- and its
    removal is why the tags below are at v2.
    """

    _K_SIG = b"\x11" * 32
    _ROOT_A = b"\x55" * 32
    _ROOT_B = b"\x66" * 32
    # the round nonce of the device's latest sync, which the WM holds as the session nonce
    _SESSION = b"\x9c" * 32

    def _ward_id(self):
        from trezor.crypto.curve import ed25519

        return ed25519.publickey(self._K_SIG)

    def test_a_signature_verifies_against_ward_id_alone(self):
        """`ward_id` IS the verifying key, so a WM needs nothing but the identifier it keys by."""
        wid = self._ward_id()
        sig = TR.wm_sig(
            self._K_SIG, wid, 41, self._ROOT_A, 42, self._ROOT_B
        )
        self.assertTrue(
            verify_wm_sig(wid, 41, self._ROOT_A, 42, self._ROOT_B, sig)
        )

    def test_it_binds_both_endpoints(self):
        """Binding only the destination would let an authorisation be lifted out of its place and
        replayed after a different predecessor -- exactly what a predecessor check must prevent."""
        wid = self._ward_id()
        sig = TR.wm_sig(
            self._K_SIG, wid, 41, self._ROOT_A, 42, self._ROOT_B
        )

        # a different predecessor
        self.assertFalse(
            verify_wm_sig(wid, 40, self._ROOT_A, 42, self._ROOT_B, sig)
        )
        self.assertFalse(
            verify_wm_sig(wid, 41, self._ROOT_B, 42, self._ROOT_B, sig)
        )
        # a different destination
        self.assertFalse(
            verify_wm_sig(wid, 41, self._ROOT_A, 43, self._ROOT_B, sig)
        )
        self.assertFalse(
            verify_wm_sig(wid, 41, self._ROOT_A, 42, self._ROOT_A, sig)
        )

    def test_another_wallet_cannot_use_it(self):
        wid = self._ward_id()
        from trezor.crypto.curve import ed25519

        sig = TR.wm_sig(
            self._K_SIG, wid, 41, self._ROOT_A, 42, self._ROOT_B
        )
        other = ed25519.publickey(b"\x22" * 32)
        self.assertFalse(
            verify_wm_sig(other, 41, self._ROOT_A, 42, self._ROOT_B, sig)
        )

    def test_it_is_bound_to_the_session_nonce(self):
        """An authorisation is good only for the sync it was minted in: the WM checks it against the
        nonce of the wallet's latest sync, and a new sync ends the session."""
        wid = self._ward_id()
        sig = TR.wm_sig(
            self._K_SIG, wid, 41, self._ROOT_A, 42, self._ROOT_B, TR.TAG_WM_HEAD, self._SESSION
        )
        self.assertTrue(
            verify_wm_sig(wid, 41, self._ROOT_A, 42, self._ROOT_B, sig, session_nonce=self._SESSION)
        )
        self.assertFalse(
            verify_wm_sig(
                wid, 41, self._ROOT_A, 42, self._ROOT_B, sig, session_nonce=b"\x9d" * 32
            )
        )
        self.assertFalse(verify_wm_sig(wid, 41, self._ROOT_A, 42, self._ROOT_B, sig))

    def test_head_init_cannot_be_replayed_as_an_advance(self):
        """Its own tag, so the authorisation that opens a wallet's history cannot be re-presented
        as a step within it."""
        wid = self._ward_id()
        init = TR.head_init_sig(self._K_SIG, wid, 0, self._ROOT_A)
        self.assertTrue(verify_head_init_sig(wid, 0, self._ROOT_A, init))
        # the same bytes, offered as a 0 -> 0 advance
        self.assertFalse(
            verify_wm_sig(wid, 0, self._ROOT_A, 0, self._ROOT_A, init)
        )

        advance = TR.wm_sig(self._K_SIG, wid, 0, self._ROOT_A, 0, self._ROOT_A)
        self.assertFalse(verify_head_init_sig(wid, 0, self._ROOT_A, advance))

    def test_the_tag_is_the_only_thing_separating_the_two_authenticators(self):
        """WHAT CHANGED, AND WHY THIS TEST STILL MATTERS.

        The device and the WM authenticators used to cover different operands -- roots and mac
        heads -- and this test asserted they could not be confused because of that. They now share
        a builder, deliberately: the same statement made to two verifiers holding different
        secrets, differing in one appended field only the WM can supply. So the operand difference
        is all but gone and the TAG is the whole of the separation at THIS layer, which makes
        pinning it more important than it was, not less.

        Domain separation still holds where it has to: every tag in the family produces a
        different preimage, and the length prefix means no tag can be re-split into another
        however the lengths move.
        """
        wid = self._ward_id()
        commit = TR.transition_preimage(
            TR.TAG_COMMIT, wid, 41, self._ROOT_A, 42, self._ROOT_B
        )
        for other in (TR.TAG_REVERT, TR.TAG_WM_HEAD, TR.TAG_WM_INIT):
            self.assertNotEqual(
                commit,
                TR.transition_preimage(other, wid, 41, self._ROOT_A, 42, self._ROOT_B),
            )

        # ...and the operands really are identical now, which is the point of the change: an
        # auth_commit and a wm_sig over the same transition cover the same bytes.
        self.assertEqual(
            TR.transition_preimage(
                TR.TAG_WM_HEAD, wid, 41, self._ROOT_A, 42, self._ROOT_B
            )[1 + len(TR.TAG_WM_HEAD) :],
            commit[1 + len(TR.TAG_COMMIT) :],
        )

    def test_operands_must_be_fixed_width(self):
        """Same reason as everywhere else in WARD: a short operand lets the preimage be re-split."""
        wid = self._ward_id()
        with self.assertRaises(DataError):
            TR.transition_preimage(TR.TAG_WM_HEAD, wid[:31], 0, self._ROOT_A, 1, self._ROOT_B)
        with self.assertRaises(DataError):
            TR.transition_preimage(TR.TAG_WM_HEAD, wid, 0, self._ROOT_A[:31], 1, self._ROOT_B)
        with self.assertRaises(DataError):
            TR.transition_preimage(TR.TAG_WM_HEAD, wid, 0, self._ROOT_A, 1, self._ROOT_B + b"\x00")

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
            TR.transition_preimage(TR.TAG_WM_HEAD, wid, 41, self._ROOT_A, 42, self._ROOT_B),
            bytes.fromhex(
                "115741524420574d20434f4d4d4954207635"
                "d04ab232742bb4ab3a1368bd4615e4e6d0224ab71a016baf8520a332c9778737"
                "00000029" + "55" * 32 + "0000002a" + "66" * 32
            ),
        )
        self.assertEqual(
            TR.wm_sig(
                self._K_SIG,
                wid,
                41,
                self._ROOT_A,
                42,
                self._ROOT_B,
                TR.TAG_WM_HEAD,
                self._SESSION,
            ),
            bytes.fromhex(
                "1827761a1f642c18073b7c49944411a50ea358bfff71131d93ab9bde12a0084d"
                "9c2fceb4fbcab1457072538f8d7df2ae7fae44f62505cec3515a350be6d71e09"
            ),
        )
        # The INIT preimage is pinned as well as its signature, so a change to the tag fails
        # with a readable diff rather than an opaque 64-byte mismatch. `0f` is len("WARD WM
        # INIT v4"); both endpoints are (0, root), there being no predecessor to name.
        self.assertEqual(
            TR.transition_preimage(TR.TAG_WM_INIT, wid, 0, self._ROOT_A, 0, self._ROOT_A),
            bytes.fromhex(
                "0f5741524420574d20494e4954207634"
                "d04ab232742bb4ab3a1368bd4615e4e6d0224ab71a016baf8520a332c9778737"
                "00000000" + "55" * 32 + "00000000" + "55" * 32
            ),
        )
        self.assertEqual(
            TR.head_init_sig(self._K_SIG, wid, 0, self._ROOT_A),
            bytes.fromhex(
                "d7702a698f249607637b93a8b3dd83707eb7b5e7291e86be1caad9e55ee0efee"
                "d385da6aea7c7d6c700b1ded7720196801ad021c8460bef9043e9041dd67f008"
            ),
        )

    def test_a_malformed_signature_is_refused_not_raised(self):
        wid = self._ward_id()
        self.assertFalse(
            verify_wm_sig(wid, 0, self._ROOT_A, 1, self._ROOT_B, b"")
        )
        self.assertFalse(
            verify_wm_sig(
                wid, 0, self._ROOT_A, 1, self._ROOT_B, b"\x00" * 63
            )
        )
        self.assertFalse(
            verify_wm_sig(
                wid, 0, self._ROOT_A, 1, self._ROOT_B, b"\x00" * 64
            )
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


class TestWardSealedPartIsStrict(unittest.TestCase):
    """`leaf.check_sealed`: a part that is not a well-formed sealing is refused before it is
    hashed or opened, so every implementation commits to the same bytes."""

    def test_short_or_unknown_scheme_is_refused(self):
        good = b"\x01" + bytes(28)
        L.check_sealed(good)
        for bad in (good[:-1], b"\x02" + good[1:], b"\x00" + good[1:]):
            with self.assertRaises(DataError):
                L.check_sealed(bad)

    def test_an_empty_part_is_a_delete(self):
        self.assertTrue(is_delete(EMPTY))
        self.assertTrue(is_delete(None))
        self.assertFalse(is_delete(b"\x01" + bytes(28)))


class TestWardDemotionConsent(TestCaseWithContext):
    """`round`: how long the user's approval of a descent stays good for.

    THE RECORD IS THE CONSENT, so what it contains is what the consent means. It holds the exact
    transition the user approved AND the head they approved it from, because the screen they held
    to confirm counts the discarded changes from that head: "currently at #N, restoring at #M,
    discarding K changes". Approving it answers a question about K.

    Left alive while the device moved on to #N+j, the same endpoints would mean discarding K+j
    changes -- and the exemption exists precisely to waive the anti-rollback floor, so it would
    waive a floor that had risen since. Nobody was asked about that.
    """

    _FROM = bytes([0x11]) * 32
    _TO = bytes([0x22]) * 32

    def setUp(self):
        # A LIVE SESSION, because the authorisation lives in the session cache -- which is the
        # point of it: a demotion not completed in this session must be confirmed again rather
        # than inherited. `TestCaseWithContext` installs a context but opens no session, and the
        # cache raises without one.
        if utils.USE_THP:
            from storage import cache_thp

            cache_thp.clear_trezor_cache()
        else:
            from storage import cache_codec

            cache_codec.start_session()

    def test_it_matches_only_the_transition_that_was_approved(self):
        ROUND.authorise_demotion(57, 40, self._FROM, 41, self._TO)
        self.assertTrue(ROUND.demotion_matches(57, 40, self._FROM, 41, self._TO))

        # a different destination root at the approved counter is a DIFFERENT state
        self.assertFalse(
            ROUND.demotion_matches(57, 40, self._FROM, 41, bytes([0x33]) * 32)
        )
        # ...and so is a different predecessor
        self.assertFalse(
            ROUND.demotion_matches(57, 40, bytes([0x33]) * 32, 41, self._TO)
        )
        self.assertFalse(ROUND.demotion_matches(57, 39, self._FROM, 41, self._TO))
        self.assertFalse(ROUND.demotion_matches(57, 40, self._FROM, 42, self._TO))

    def test_it_stops_matching_once_the_device_has_moved(self):
        """THE BUG THIS CLOSES, stated as the sequence that reaches it.

        The host declines to publish the approved demotion, carries the device forward with
        ordinary writes -- entirely unprivileged -- and offers the approved transition later. The
        endpoints still match. The situation does not.
        """
        ROUND.authorise_demotion(57, 40, self._FROM, 41, self._TO)
        self.assertTrue(ROUND.demotion_matches(57, 40, self._FROM, 41, self._TO))

        for moved_to in (58, 80, 100):
            self.assertFalse(
                ROUND.demotion_matches(moved_to, 40, self._FROM, 41, self._TO)
            )

    def test_one_hold_buys_one_descent(self):
        ROUND.authorise_demotion(57, 40, self._FROM, 41, self._TO)
        ROUND.clear_demotion()
        self.assertFalse(ROUND.demotion_matches(57, 40, self._FROM, 41, self._TO))

    def test_an_absent_authorisation_matches_nothing(self):
        """Absent is the safe answer, and it is what an unset cache slot reads back as."""
        self.assertFalse(ROUND.demotion_matches(57, 40, self._FROM, 41, self._TO))
        self.assertFalse(ROUND.demotion_matches(0, 0, bytes(32), 0, bytes(32)))


if __name__ == "__main__":
    unittest.main()
