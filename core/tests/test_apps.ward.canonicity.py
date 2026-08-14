# flake8: noqa: F403,F405
from common import *  # isort:skip

from trezor.crypto.hashlib import sha256
from trezor.wire import DataError
from ward_trie_model import CanonicalTrie

from apps.ward.attest import EMPTY_ROOT
from apps.ward.leaf import ENC_PLAINTEXT, commit_of
from apps.ward.trie import compute_new_root

_KT = "address"


def _part(body):
    """A firmware Part: (encoding, nonce, tag, body). Plaintext, so no nonce or tag."""
    return (ENC_PLAINTEXT, b"", b"", body)


def _leaf(body):
    """(key_type, id_part, val_part), the shape compute_new_root takes."""
    return (_KT, None, _part(body))


def _commit(body):
    return commit_of(_KT, None, _part(body))


class _Rng:
    """A deterministic LCG.

    Not for randomness -- for REPRODUCIBILITY. A failure has to be replayable from the seed
    alone, and MicroPython has no seeded PRNG that is guaranteed stable across versions.
    """

    def __init__(self, seed: int) -> None:
        self.s = seed & 0x7FFFFFFF

    def below(self, n: int) -> int:
        self.s = (self.s * 1103515245 + 12345) & 0x7FFFFFFF
        return self.s % n


def _keys_random(n):
    """Independent keys. This is what real entry_keys are -- they are HMAC outputs."""
    return [sha256(bytes([i])).digest() for i in range(n)]


def _keys_shared_prefix(n):
    """Keys agreeing on their first 160 bits, so branches sit deep in the key."""
    p = bytes([0xAB]) * 20
    return [p + sha256(bytes([i])).digest()[:12] for i in range(n)]


def _keys_ladder(n):
    """Key i is i leading 1-bits then zeros: every level is a compressed run.

    This is the geometry where almost every leaf's sibling is a BRANCH -- the subtree holding
    all the deeper keys -- which used to be the hard case for delete and is now the ordinary
    one.
    """
    out = []
    for i in range(n):
        b = bytearray(32)
        for j in range(i):
            b[j // 8] |= 1 << (7 - (j % 8))
        out.append(bytes(b))
    return out


def _keys_mixed(n):
    half = n // 2
    p = bytes([0xAB]) * 20
    return _keys_random(half) + [
        p + sha256(bytes([i])).digest()[:12] for i in range(n - half)
    ]


GEOMETRIES = (
    ("random", _keys_random),
    ("shared_prefix", _keys_shared_prefix),
    ("ladder", _keys_ladder),
    ("mixed", _keys_mixed),
)


class TestWardTrieCanonicity(unittest.TestCase):
    """The derived root must equal the root a rebuild produces, for every reachable shape.

    THE PROPERTY THIS TESTS, AND WHY NOTHING ELSE CAN. The device derives each root from the
    previous one plus a proof (`compute_new_root`) and verifies by reconstructing a single
    path. It never rebuilds the tree, so it cannot notice that its root is not the canonical
    root of its own key set: reconstruction along one path stays self-consistent inside a
    locally-wrong tree. That is exactly how the sibling-kind bug survived -- the device
    verified its own proofs happily against a root no rebuilder agreed with, and the wallet
    would only have wedged when a host recomputed. Only a rebuilder can see it, and the
    device is never a rebuilder. Hence a differential test rather than an assertion. All
    three of those bugs are gone now, having been artifacts of committing to a node's depth,
    but the test that would have caught them is worth more than the bugs were.

    All three trie bugs in this subsystem's history are this class of bug.

    GEOMETRY MATTERS MORE THAN OP COUNT, which is not obvious and was measured rather than
    guessed. An earlier sweep of 2880 operations over random keys never reached a split_bit
    above 8 -- and depth is what every one of the bugs turned on, since they were all about a
    node moving between levels.
    So the four key sets below are the substance of this test, and it FAILS if the sweep
    stops reaching the hard shapes rather than merely reporting that it did not.
    """

    TRIALS = 6
    STEPS = 20
    KEYS = 16

    def _run_geometry(self, keys, seed):
        """Drive one randomised op sequence, asserting canonicity after every step.

        Returns per-class op counts and the deepest split_bit seen, for the coverage floors.
        """
        counts = {
            "insert": 0,
            "update": 0,
            "delete": 0,
            "delete_last": 0,
        }
        max_split_bit = 0
        rng = _Rng(seed)

        model = CanonicalTrie()
        root = None  # the device: None means "has never written"
        live = {}

        for step in range(self.STEPS):
            key = keys[rng.below(len(keys))]
            proof = model.membership_proof(key) if key in live else None
            if proof:
                for elem in proof:
                    sb = int.from_bytes(elem[0:2], "big")
                    if sb > max_split_bit:
                        max_split_bit = sb

            if key in live and rng.below(100) < 45:
                # DELETE -- the proof is all of it; the sibling promotes unchanged
                counts["delete_last" if not proof else "delete"] += 1
                root = compute_new_root(key, _leaf(live[key]), None, proof, root)
                model.remove(key)
                del live[key]

            elif key in live:
                # UPDATE
                body = bytes([rng.below(256)]) * (1 + rng.below(5))
                root = compute_new_root(key, _leaf(live[key]), _leaf(body), proof, root)
                live[key] = body
                model.set(key, _commit(body))
                counts["update"] += 1

            else:
                # INSERT -- with a non-membership witness unless the tree is empty
                body = bytes([rng.below(256)]) * (1 + rng.below(5))
                p, wkey, wcommit = model.nonmembership_witness(key)
                root = compute_new_root(
                    key,
                    None,
                    _leaf(body),
                    p,
                    root,
                    witness_entry_key=wkey,
                    witness_commit=wcommit,
                )
                live[key] = body
                model.set(key, _commit(body))
                counts["insert"] += 1

            self.assertEqual(root, model.root())
            self.assertTrue(root is not None)

        # DRAIN. Delete everything that is left, one at a time, until the tree is empty.
        #
        # Not decoration: the coverage floor below caught that a 16-key tree essentially
        # never drains to its last leaf by chance, so `delete_last` had zero coverage. The
        # fix is to reach the shape deliberately rather than to raise the op count and hope.
        # Draining also walks the entire collapse sequence -- every depth, both sibling
        # kinds, ending at the empty tree -- which random deletion samples only thinly.
        while live:
            key = sorted(live)[rng.below(len(live))]
            proof = model.membership_proof(key)
            for elem in proof:
                sb = int.from_bytes(elem[0:2], "big")
                if sb > max_split_bit:
                    max_split_bit = sb
            counts["delete_last" if not proof else "delete"] += 1
            root = compute_new_root(key, _leaf(live[key]), None, proof, root)
            model.remove(key)
            del live[key]
            self.assertEqual(root, model.root())

        # ...and an emptied tree says so, rather than reverting to "no root" (D2)
        self.assertEqual(root, EMPTY_ROOT)

        # it must also still be writable, or the D2 fix would be a denial of service: there
        # is no leaf left to witness, so this takes the first-insert path again
        first = keys[0]
        root = compute_new_root(first, None, _leaf(b"again"), [], root)
        model.set(first, _commit(b"again"))
        self.assertEqual(root, model.root())

        return counts, max_split_bit

    def test_derived_root_matches_a_rebuild_and_reaches_the_hard_shapes(self):
        """Every op in every geometry lands on the canonical root -- and the sweep is
        required to have reached the shapes that have actually broken.

        Both halves are one test on purpose. Split apart, the coverage half either reruns the
        whole sweep or depends on test ordering to see its results, and a coverage floor that
        can be skipped is not a floor.

        Reporting the counts would not be enough either. A change to key generation or to the
        op mix can quietly reduce this to inserting random keys into shallow trees, which
        passes and reads like coverage. So each class must stay non-zero, and the split_bit
        must reach deep somewhere -- that last one is why `shared_prefix` and `ladder` exist
        at all, since random keys never get past single digits.
        """
        totals = {}
        max_split_bit = 0
        for name, make in GEOMETRIES:
            keys = make(self.KEYS)
            for trial in range(self.TRIALS):
                counts, sk = self._run_geometry(keys, seed=0x5EED + trial)
                for k, v in counts.items():
                    totals[k] = totals.get(k, 0) + v
                if sk > max_split_bit:
                    max_split_bit = sk

        for name in (
            "insert",
            "update",
            "delete",
            "delete_last",
        ):
            self.assertTrue(totals.get(name, 0) > 0, "no coverage of: " + name)
        self.assertTrue(
            max_split_bit >= 32,
            "deep shapes were not reached (max split_bit=%d)" % max_split_bit,
        )

    def test_a_delete_needs_nothing_but_its_proof(self):
        """What the sibling-kind witness used to be needed for, and no longer is.

        Set up with the shape that was hardest: the collapsing sibling is a BRANCH, which
        used to have to arrive decomposed so the device could re-derive it at its new depth.
        A node's hash no longer commits to depth, so it promotes unchanged -- and this
        asserts the result is still the canonical one, which is the only thing that mattered.
        """
        keys = _keys_ladder(6)
        model = CanonicalTrie()
        root = None
        for i, k in enumerate(keys):
            p, wkey, wcommit = model.nonmembership_witness(k)
            root = compute_new_root(
                k,
                None,
                _leaf(bytes([i])),
                p,
                root,
                witness_entry_key=wkey,
                witness_commit=wcommit,
            )
            model.set(k, _commit(bytes([i])))

        # a ladder puts a branch under almost every leaf, so this is the branch-sibling case
        target, body = keys[0], bytes([0])
        proof = model.membership_proof(target)
        self.assertTrue(len(proof) > 0)
        got = compute_new_root(target, _leaf(body), None, proof, root)
        model.remove(target)
        self.assertEqual(got, model.root())

    def test_the_model_agrees_with_the_firmware_on_an_empty_tree(self):
        """Both sides must spell "empty" the same way, or D2 reopens on one of them."""
        self.assertEqual(CanonicalTrie().root(), EMPTY_ROOT)
        self.assertEqual(EMPTY_ROOT, sha256(b"\x03").digest())


if __name__ == "__main__":
    unittest.main()
