#!/usr/bin/env python3
"""Generate (or check) the cross-implementation WARD trie conformance fixture.

    core/tools/ward_trie_fixture.py            # rewrite the fixture
    core/tools/ward_trie_fixture.py --check    # fail if the committed fixture is stale

The fixture is a deterministic sequence of trie operations with the canonical root after
each one. Any implementation -- the firmware, `@trezor/ward`, a future batch path, a second
device -- can replay it and compare roots without reimplementing the generator, which is the
only way a fourth party joins this subsystem without a fresh canonicalisation disagreement.
Three of the three trie bugs found so far were exactly that.

The roots are produced by the naive rebuilder in `core/tests/ward_trie_model.py` (the spec
transcribed into code) and cross-checked here against the firmware's incremental deriver, so
a fixture that disagrees with either is never written.

NOT WIRED INTO CI. Nothing runs this automatically yet; `core/tests/test_apps.ward
.canonicity.py` is the automated guard on the firmware side. Run --check by hand, or wire it
up once a second implementation actually consumes the fixture.
"""

from __future__ import annotations

import hashlib
import json
import sys
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
FIXTURE = ROOT / "common" / "tests" / "fixtures" / "ward" / "trie_canonicity.json"


def _install_trezor_stubs() -> None:
    """Let the firmware and model modules import unchanged under CPython."""

    class _Sha:
        def __init__(self, data: bytes = b"") -> None:
            self.m = hashlib.sha256(data)

        def update(self, data: bytes) -> "_Sha":
            self.m.update(data)
            return self

        def digest(self) -> bytes:
            return self.m.digest()

    trezor = types.ModuleType("trezor")
    crypto = types.ModuleType("trezor.crypto")
    hl = types.ModuleType("trezor.crypto.hashlib")
    hl.sha256 = _Sha
    wire = types.ModuleType("trezor.wire")

    class DataError(Exception):
        pass

    wire.DataError = DataError
    micropython = types.ModuleType("micropython")
    micropython.const = lambda x: x

    sys.modules.update(
        {
            "trezor": trezor,
            "trezor.crypto": crypto,
            "trezor.crypto.hashlib": hl,
            "trezor.wire": wire,
            "micropython": micropython,
        }
    )
    crypto.hashlib = hl
    trezor.crypto = crypto
    trezor.wire = wire


_install_trezor_stubs()
sys.path.insert(0, str(ROOT / "core" / "src"))
sys.path.insert(0, str(ROOT / "core" / "tests"))

from ward_trie_model import CanonicalTrie  # noqa: E402

from apps.ward.attest import EMPTY_ROOT  # noqa: E402
from apps.ward.leaf import ENC_PLAINTEXT, commit_of  # noqa: E402
from apps.ward.trie import compute_new_root  # noqa: E402

KT = "address"


def part(body: bytes):
    return (ENC_PLAINTEXT, b"", b"", body)


def leaf(body: bytes):
    return (KT, None, part(body))


def commit(body: bytes) -> bytes:
    return commit_of(KT, None, part(body))


# --- key geometries -----------------------------------------------------------------
#
# These are the substance of the fixture. Op count is nearly irrelevant next to geometry:
# a sweep of 2880 operations over random keys was measured never to reach a split_bit above
# 8 or a skiplen above 2, and skiplen is the quantity that goes stale on re-parenting and
# caused every known bug. Real entry_keys ARE random (they are HMAC outputs), so the
# deep-prefix sets are not realistic inputs -- they are the only way to exercise the
# arithmetic that random keys leave untested.


def keys_random(n: int) -> list[bytes]:
    return [hashlib.sha256(bytes([i])).digest() for i in range(n)]


def keys_shared_prefix(n: int) -> list[bytes]:
    p = bytes([0xAB]) * 20
    return [p + hashlib.sha256(bytes([i])).digest()[:12] for i in range(n)]


def keys_ladder(n: int) -> list[bytes]:
    out = []
    for i in range(n):
        b = bytearray(32)
        for j in range(i):
            b[j // 8] |= 1 << (7 - (j % 8))
        out.append(bytes(b))
    return out


GEOMETRIES = {
    "random": keys_random,
    "shared_prefix": keys_shared_prefix,
    "ladder": keys_ladder,
}

# A fixed script rather than a PRNG: a fixture has to be readable and diffable, and an
# implementer debugging a mismatch needs to see which operation failed, not reproduce a
# random stream. Ends by draining to empty and writing again, which is the only way the
# last-leaf delete and the empty-tree-is-writable case get covered at all.
SCRIPT = (
    # Fill up first, so the deletes that follow happen in a tree deep enough to have BRANCH
    # siblings. An earlier version deleted early, while only three or four keys were live,
    # and every delete in the random and shared-prefix geometries hit a leaf sibling -- so an
    # implementer replaying those two would never have exercised the case that broke.
    ("insert", 0, "a0"),
    ("insert", 5, "a5"),
    ("insert", 2, "a2"),
    ("insert", 7, "a7"),
    ("insert", 1, "a1"),
    ("insert", 3, "a3"),
    ("insert", 6, "a6"),
    ("insert", 4, "a4"),
    ("update", 5, "b5"),
    ("delete", 2, None),
    ("update", 0, "c0"),
    ("delete", 6, None),
    ("insert", 2, "a2_again"),
    ("delete", 7, None),
    # ...then drain to empty, which is the only way the last-leaf delete is covered, and
    # write once more, which is the only way "an emptied tree is still writable" is.
    ("delete", 0, None),
    ("delete", 1, None),
    ("delete", 2, None),
    ("delete", 3, None),
    ("delete", 4, None),
    ("delete", 5, None),
    ("insert", 2, "after_empty"),
)


def build(keys: list[bytes]) -> list[dict]:
    """Replay SCRIPT, deriving and rebuilding in lockstep. Returns the recorded steps."""
    model = CanonicalTrie()
    root = None
    live: dict[bytes, bytes] = {}
    steps = []

    for op, idx, tag in SCRIPT:
        key = keys[idx]
        body = tag.encode() if tag is not None else b""
        record = {"op": op, "key_index": idx}

        if op == "insert":
            assert key not in live, "script inserts a live key"
            proof, wkey, wcommit = model.nonmembership_witness(key)
            root = compute_new_root(
                key,
                None,
                leaf(body),
                proof,
                root,
                witness_entry_key=wkey,
                witness_commit=wcommit,
            )
            live[key] = body
            model.set(key, commit(body))
            record["value"] = tag
            record["witness_key_index"] = None if wkey is None else keys.index(wkey)

        elif op == "update":
            assert key in live, "script updates a missing key"
            proof = model.membership_proof(key)
            root = compute_new_root(key, leaf(live[key]), leaf(body), proof, root)
            live[key] = body
            model.set(key, commit(body))
            record["value"] = tag

        else:
            assert key in live, "script deletes a missing key"
            proof = model.membership_proof(key)
            sib = model.sibling_witness(key)
            kwargs = {}
            if sib is None:
                record["sibling"] = "none"
            elif sib[0] == "branch":
                kwargs["sibling_node"] = (sib[1], sib[2], sib[3])
                record["sibling"] = "branch"
            else:
                kwargs["sibling_leaf"] = (sib[1], sib[2])
                record["sibling"] = "leaf"
            root = compute_new_root(key, leaf(live[key]), None, proof, root, **kwargs)
            model.remove(key)
            del live[key]

        # The fixture is only written when the deriver and the rebuilder agree. A fixture
        # generated from one of them alone would enshrine whichever was wrong.
        assert root == model.root(), "deriver and rebuilder disagree at %r" % (record,)
        record["root"] = root.hex()
        steps.append(record)

    return steps


def generate() -> dict:
    return {
        "_comment": (
            "WARD trie canonicity conformance vectors. Replay `steps` in order against your "
            "own implementation and compare `root` after each one. See "
            "docs/core/misc/ward-trie.md for the hashing and structure rules, and "
            "core/tools/ward_trie_fixture.py to regenerate."
        ),
        "key_type": KT,
        "empty_root": EMPTY_ROOT.hex(),
        "leaf_encoding": {
            "note": (
                "Each value below is the body of a PLAINTEXT content part; the identity "
                "part is empty. commit = sha256(0x02 || len8(key_type) || key_type || "
                "len32(id_part) || id_part || len32(val_part) || val_part), where a part is "
                "encoding(1B) || len8(nonce) || nonce || len8(tag) || tag || len32(body) || "
                "body. Values are ASCII so an implementer can encode them directly."
            ),
            "encoding_plaintext": ENC_PLAINTEXT,
        },
        "geometries": {
            name: {
                "keys": [k.hex() for k in make(8)],
                "steps": build(make(8)),
            }
            for name, make in GEOMETRIES.items()
        },
    }


def _check_coverage(data: dict) -> None:
    """Refuse to write a fixture that does not reach the shapes that have actually broken.

    A conformance fixture that silently covers only the easy cases is worse than none: it
    reads as agreement. Every known trie bug involved a re-parented BRANCH sibling or the
    empty tree, so both must appear.
    """
    kinds = {}
    for name, g in data["geometries"].items():
        seen = set()
        for step in g["steps"]:
            if step["op"] == "delete":
                seen.add(step["sibling"])
        kinds[name] = seen
        for required in ("leaf", "branch", "none"):
            if required not in seen:
                raise SystemExit(
                    "fixture geometry %r never exercises a %r sibling delete: %s"
                    % (name, required, sorted(seen))
                )
    return kinds


def main() -> int:
    data = generate()
    kinds = _check_coverage(data)
    text = json.dumps(data, indent=2) + "\n"

    if "--check" in sys.argv:
        if not FIXTURE.exists():
            print("MISSING: %s" % FIXTURE)
            return 1
        if FIXTURE.read_text() != text:
            print("STALE: %s does not match what the generator produces" % FIXTURE)
            return 1
        print("up to date: %s" % FIXTURE)
        return 0

    FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE.write_text(text)
    total = sum(len(g["steps"]) for g in data["geometries"].values())
    print(
        "wrote %s (%d geometries, %d steps)" % (FIXTURE, len(data["geometries"]), total)
    )
    for name in sorted(kinds):
        print(
            "  %-14s sibling kinds covered: %s" % (name, ", ".join(sorted(kinds[name])))
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
