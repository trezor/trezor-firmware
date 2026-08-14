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
    """Keys agreeing on their first 160 bits, so branches sit deep and skiplens are large."""
    p = bytes([0xAB]) * 20
    return [p + sha256(bytes([i])).digest()[:12] for i in range(n)]


def _keys_ladder(n):
    """Key i is i leading 1-bits then zeros: every level is a compressed run.

    This is the geometry that maximises branch-sibling deletes -- the D1 case -- because
    almost every leaf's sibling is the subtree holding all the deeper keys.
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
    device is never a rebuilder. Hence a differential test rather than an assertion.

    All three trie bugs in this subsystem's history are this class of bug.

    GEOMETRY MATTERS MORE THAN OP COUNT, which is not obvious and was measured rather than
    guessed. An earlier sweep of 2880 operations over random keys never reached a split_bit
    above 8 or a skiplen above 2, with 86% of proof elements at skiplen 0 -- and skiplen is
    precisely the quantity that goes stale on re-parenting and caused every one of the bugs.
    So the four key sets below are the substance of this test, and it FAILS if the sweep
    stops reaching the hard shapes rather than merely reporting that it did not.
    """

    TRIALS = 6
    STEPS = 20
    KEYS = 16

    def _run_geometry(self, keys, seed):
        """Drive one randomised op sequence, asserting canonicity after every step.

        Returns per-class op counts and the largest skiplen seen, for the coverage floors.
        """
        counts = {
            "insert": 0,
            "update": 0,
            "delete_leaf_sibling": 0,
            "delete_branch_sibling": 0,
            "delete_last": 0,
        }
        max_skiplen = 0
        rng = _Rng(seed)

        model = CanonicalTrie()
        root = None  # the device: None means "has never written"
        live = {}

        for step in range(self.STEPS):
            key = keys[rng.below(len(keys))]
            proof = model.membership_proof(key) if key in live else None
            if proof:
                for elem in proof:
                    sk = int.from_bytes(elem[2:4], "big")
                    if sk > max_skiplen:
                        max_skiplen = sk

            if key in live and rng.below(100) < 45:
                # DELETE -- the sibling witness is whichever form actually applies
                sib = model.sibling_witness(key)
                kwargs = {}
                if sib is None:
                    counts["delete_last"] += 1
                elif sib[0] == "branch":
                    kwargs["sibling_node"] = (sib[1], sib[2], sib[3])
                    counts["delete_branch_sibling"] += 1
                else:
                    kwargs["sibling_leaf"] = (sib[1], sib[2])
                    counts["delete_leaf_sibling"] += 1
                root = compute_new_root(
                    key, _leaf(live[key]), None, proof, root, **kwargs
                )
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
                sk = int.from_bytes(elem[2:4], "big")
                if sk > max_skiplen:
                    max_skiplen = sk
            sib = model.sibling_witness(key)
            kwargs = {}
            if sib is None:
                counts["delete_last"] += 1
            elif sib[0] == "branch":
                kwargs["sibling_node"] = (sib[1], sib[2], sib[3])
                counts["delete_branch_sibling"] += 1
            else:
                kwargs["sibling_leaf"] = (sib[1], sib[2])
                counts["delete_leaf_sibling"] += 1
            root = compute_new_root(key, _leaf(live[key]), None, proof, root, **kwargs)
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

        return counts, max_skiplen

    def test_derived_root_matches_a_rebuild_and_reaches_the_hard_shapes(self):
        """Every op in every geometry lands on the canonical root -- and the sweep is
        required to have reached the shapes that have actually broken.

        Both halves are one test on purpose. Split apart, the coverage half either reruns the
        whole sweep or depends on test ordering to see its results, and a coverage floor that
        can be skipped is not a floor.

        Reporting the counts would not be enough either. A change to key generation or to the
        op mix can quietly reduce this to inserting random keys into shallow trees, which
        passes and reads like coverage. So each class must stay non-zero, and skiplen must
        stay large somewhere -- that last one is why `shared_prefix` and `ladder` exist at
        all, since random keys never got it past 2.
        """
        totals = {}
        max_skiplen = 0
        for name, make in GEOMETRIES:
            keys = make(self.KEYS)
            for trial in range(self.TRIALS):
                counts, sk = self._run_geometry(keys, seed=0x5EED + trial)
                for k, v in counts.items():
                    totals[k] = totals.get(k, 0) + v
                if sk > max_skiplen:
                    max_skiplen = sk

        for name in (
            "insert",
            "update",
            "delete_leaf_sibling",
            "delete_branch_sibling",
            "delete_last",
        ):
            self.assertTrue(totals.get(name, 0) > 0, "no coverage of: " + name)
        self.assertTrue(
            max_skiplen >= 32,
            "deep-skiplen shapes were not reached (max=%d)" % max_skiplen,
        )

    def test_a_delete_must_identify_its_sibling(self):
        """The omission that D1 closed, restated against a rebuilt tree.

        Withholding both witness forms is refused. Set up so the sibling really is a BRANCH:
        against a leaf sibling the old code was right by accident, and this would prove
        nothing.
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

        target = None
        for i, k in enumerate(keys):
            sib = model.sibling_witness(k)
            if sib is not None and sib[0] == "branch":
                target = (i, k, sib)
                break
        self.assertTrue(target is not None)
        i, k, sib = target
        proof = model.membership_proof(k)

        with self.assertRaises(DataError):
            compute_new_root(k, _leaf(bytes([i])), None, proof, root)
        with self.assertRaises(DataError):
            compute_new_root(
                k,
                _leaf(bytes([i])),
                None,
                proof,
                root,
                sibling_node=(sib[1], sib[2], sib[3]),
                sibling_leaf=(k, _commit(bytes([i]))),
            )

        # the honest form lands on the canonical root
        got = compute_new_root(
            k,
            _leaf(bytes([i])),
            None,
            proof,
            root,
            sibling_node=(sib[1], sib[2], sib[3]),
        )
        model.remove(k)
        self.assertEqual(got, model.root())

    def test_the_model_agrees_with_the_firmware_on_an_empty_tree(self):
        """Both sides must spell "empty" the same way, or D2 reopens on one of them."""
        self.assertEqual(CanonicalTrie().root(), EMPTY_ROOT)
        self.assertEqual(EMPTY_ROOT, sha256(b"\x03").digest())


if __name__ == "__main__":
    unittest.main()
