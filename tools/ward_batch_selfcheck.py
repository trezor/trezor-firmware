#!/usr/bin/env python3
"""WARD batch-update CPython self-check.

Runs the firmware batch-update crypto/storage on CPython (stubbing the micropython
surface) and cross-checks it against the trezorlib WARD trie oracle. This is the
runnable proof for the parts that would otherwise only be exercised on the emulator:

  1. keys / preimages   head_mac, AuthCommit, AuthRevert layout + domain separation
  2. batch fold         compute_batch_root vs an independent trezorlib WARDTree
  3. batch storage      the _BATCH envelope round-trip (kind = commit / revert)
  4. rollback crypto    forward-AuthCommit proves predecessor; forward-increment; F1

Usage:  python3 tools/ward_batch_selfcheck.py     (exit 0 = all passed)

Emulator-gated flows NOT covered here (run on the unix emulator):
  - end-to-end WARDPerformBatch / WARDConfirmBatchByWM and rollback rounds
  - core micropython unit tests: make -C core test TESTOPTS=test_apps.authdb.py
"""
import hashlib
import hmac as _hmac
import importlib.util
import os
import sys
import types

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE_SRC = os.path.join(REPO, "core", "src")
PY_SRC = os.path.join(REPO, "python", "src")


def _install_stubs():
    """Stub the micropython / trezor.crypto surface the firmware modules import."""
    mp = types.ModuleType("micropython")
    mp.const = lambda x: x
    sys.modules["micropython"] = mp

    ub = types.ModuleType("ubinascii")
    ub.unhexlify = lambda s: bytes.fromhex(s.decode() if isinstance(s, (bytes, bytearray)) else s)
    sys.modules["ubinascii"] = ub

    trezor = types.ModuleType("trezor")
    trezor.__path__ = []
    sys.modules["trezor"] = trezor
    utils = types.ModuleType("trezor.utils")
    utils.consteq = lambda a, b: a == b
    trezor.utils = utils
    sys.modules["trezor.utils"] = utils
    log = types.ModuleType("trezor.log")
    log.debug = lambda *a, **k: None
    trezor.log = log
    sys.modules["trezor.log"] = log

    crypto = types.ModuleType("trezor.crypto")
    crypto.__path__ = []

    class _HMAC:
        SHA256 = "sha256"

        def __init__(self, alg, key, msg=b""):
            self._h = _hmac.new(key, msg, hashlib.sha256)

        def update(self, d):
            self._h.update(d)

        def digest(self):
            return self._h.digest()

    hf = lambda alg, key, msg=b"": _HMAC(alg, key, msg)  # noqa: E731
    hf.SHA256 = "sha256"
    crypto.hmac = hf
    trezor.crypto = crypto
    sys.modules["trezor.crypto"] = crypto

    hl = types.ModuleType("trezor.crypto.hashlib")

    class _Sha256:
        def __init__(self, d=b""):
            self._h = hashlib.sha256(d)

        def update(self, d):
            self._h.update(d)

        def digest(self):
            return self._h.digest()

    hl.sha256 = _Sha256
    sys.modules["trezor.crypto.hashlib"] = hl

    curve = types.ModuleType("trezor.crypto.curve")
    ed = types.ModuleType("trezor.crypto.curve.ed25519")
    # Deterministic stand-in — only exercises the SigCommit plumbing, not real Ed25519.
    ed.sign = lambda sk, m: hashlib.sha512(sk + m).digest()[:64]
    ed.publickey = lambda sk: hashlib.sha256(sk).digest()
    ed.verify = lambda pk, sig, msg: True
    curve.ed25519 = ed
    sys.modules["trezor.crypto.curve"] = curve
    sys.modules["trezor.crypto.curve.ed25519"] = ed

    # storage.common in-memory kv for ward_store
    storage_pkg = types.ModuleType("storage")
    storage_pkg.__path__ = []
    common = types.ModuleType("storage.common")
    kv = {}
    common.APP_AUTHDB = 0
    common.get = lambda ns, k, public=False: kv.get((ns, k))
    common.set = lambda ns, k, v, public=False: kv.__setitem__((ns, k), v)
    common.delete = lambda ns, k, public=False: kv.pop((ns, k), None)
    sys.modules["storage"] = storage_pkg
    sys.modules["storage.common"] = common


def _load(name, relpath):
    spec = importlib.util.spec_from_file_location(name, os.path.join(CORE_SRC, relpath))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    _install_stubs()
    sys.path.insert(0, PY_SRC)
    svc = _load("wardsvc", "apps/ward/service.py")
    ws = _load("wardstore", "storage/ward_store.py")
    from trezorlib.authdb_tree import WARDTree

    WID = bytes(range(32))
    KA, KH = b"A" * 32, b"H" * 32

    # --- 1. keys / preimages ------------------------------------------------
    assert svc.EMPTY_ROOT_HASH == hashlib.sha256(b"\x03").digest()
    R0, R1 = bytes([1]) * 32, bytes([2]) * 32
    assert svc.head_mac(KH, WID, 5, R0) == _hmac.new(
        KH, svc._TAG_HEAD + WID + (5).to_bytes(4, "big") + R0, hashlib.sha256
    ).digest()
    ac = svc.auth_commit(KA, WID, 4, R0, 7, R1)
    assert svc.verify_auth_commit(KA, WID, 4, R0, 7, R1, ac)
    assert not svc.verify_auth_commit(KA, WID, 4, R0, 8, R1, ac)  # wrong to_counter
    assert svc.auth_commit(KA, WID, 4, R0, 7, R1) != svc.auth_revert(KA, WID, 4, R0, 7, R1)
    assert len({svc._TAG_HEAD, svc._TAG_COMMIT, svc._TAG_REVERT}) == 3
    print("1 keys/preimages: layout + domain separation + verify ...... OK")

    # --- 2. batch fold vs trezorlib oracle ----------------------------------
    def ek(i):
        return hashlib.sha256(b"ek%d" % i).digest()

    def blob(t):
        return (bytes([t]) * 12, bytes([t]) * 16, b"ct-%d" % t + b"x" * 8)

    def base():
        t = WARDTree()
        for i, tg in [(1, 0x11), (2, 0x22), (3, 0x33)]:
            n, tag, ct = blob(tg)
            t.set_leaf(ek(i), n, tag, ct)
        return t

    # n=1 keeps full generality (INSERT/UPDATE/DELETE), delegating to compute_new_root.
    def apply1(t, op, exp_mutate):
        rf = t.get_root_hash()
        got = svc.compute_batch_root(None if not t._leaves else rf, [op])
        exp_mutate(t)
        want = None if not t._leaves else t.get_root_hash()
        assert got == want, "n=1 op root mismatch"

    t = base()
    # update leaf 1
    A2 = blob(0xAA)
    apply1(
        t,
        (ek(1), blob(0x11), A2, t.get_proof_by_key(ek(1)), None, None),
        lambda tr: tr.set_leaf(ek(1), *A2),
    )
    # delete leaf 2
    apply1(
        t,
        (ek(2), blob(0x22), None, t.get_proof_by_key(ek(2)), None, None),
        lambda tr: tr.del_leaf(ek(2)),
    )
    # insert leaf 4 (non-membership witness)
    pr, w, wc = t.get_nonmembership_proof_by_key(ek(4))
    D = blob(0xDD)
    apply1(t, (ek(4), None, D, pr, w, wc), lambda tr: tr.set_leaf(ek(4), *D))
    # duplicate entry_key in one batch is rejected
    dup_op = (ek(1), blob(0xAA), blob(0xAB), t.get_proof_by_key(ek(1)), None, None)
    try:
        svc.compute_batch_root(t.get_root_hash(), [dup_op, dup_op])
        raise AssertionError("expected duplicate-entry_key rejection")
    except ValueError:
        pass
    print("2 n=1 INSERT/UPDATE/DELETE vs oracle + dup-entry_key reject ......... OK")

    # --- 3. batch storage envelope (kind commit / revert) -------------------
    wid20 = WID[:20]
    z = b"\x00" * 32
    rf, tr = hashlib.sha256(b"from").digest(), hashlib.sha256(b"to").digest()
    ac = svc.auth_commit(KA, WID, 4, rf, 5, tr)
    ws.batch_put(wid20, 4, 5, rf, tr, z, KH, ac, b"", [10, 20])
    e = ws.batch_get(wid20)
    assert e["kind"] == ws.BATCH_COMMIT and e["pending_ids"] == [10, 20]
    assert e["from_root"] == rf and e["to_root"] == tr
    rev = svc.auth_revert(KA, WID, 5, tr, 6, rf)
    ws.batch_put(wid20, 5, 6, tr, rf, z, KH, rev, b"", [], ws.BATCH_REVERT)
    e = ws.batch_get(wid20)
    assert e["kind"] == ws.BATCH_REVERT and e["pending_ids"] == []
    assert ws.batch_clear(wid20) and ws.batch_get(wid20) is None
    print("3 batch storage: envelope round-trip + kind commit/revert + clear   OK")

    # --- 4. rollback crypto (F1 / F6 / root resurrection) -------------------
    C, Rprev, Rstuck = 5, b"\x11" * 32, b"\x22" * 32
    fwd = svc.auth_commit(KA, WID, C - 1, Rprev, C, Rstuck)  # created the stuck head
    assert svc.verify_auth_commit(KA, WID, C - 1, Rprev, C, Rstuck, fwd)
    assert not svc.verify_auth_commit(KA, WID, C - 1, b"\x99" * 32, C, Rstuck, fwd)  # wrong prev
    old = svc.auth_commit(KA, WID, 1, Rprev, 2, Rstuck)  # same roots, old counters
    assert not svc.verify_auth_commit(KA, WID, C - 1, Rprev, C, Rstuck, old)  # counter-bound
    rv = svc.auth_revert(KA, WID, C, Rstuck, C + 1, Rprev)  # forward-increment
    assert svc.verify_auth_revert(KA, WID, C, Rstuck, C + 1, Rprev, rv) and (C + 1) > C
    print("4 rollback: predecessor proof, counter-bound, forward-increment .... OK")

    # --- 5. multi-leaf UPDATE multiproof vs the trezorlib oracle ------------
    import random

    def bl(x):
        return (bytes([x & 0xFF]) * 12, bytes([(x >> 8) & 0xFF]) * 16, b"ct%d" % x)

    rnd = random.Random(20260805)
    cases = 0
    for n_entries in (2, 3, 8, 32, 128):
        for n_update in range(2, min(n_entries, 8) + 1):
            base = WARDTree()
            keys = [hashlib.sha256(b"k%d" % i).digest() for i in range(n_entries)]
            blobs = {k: bl(1000 + i) for i, k in enumerate(keys)}
            for k, b in blobs.items():
                base.set_leaf(k, *b)
            R0 = base.get_root_hash()
            expect = WARDTree()
            for k, b in blobs.items():
                expect.set_leaf(k, *b)
            ops = []
            for k in rnd.sample(keys, n_update):
                new = bl(9000 + rnd.randint(0, 10 ** 6))
                ops.append((k, blobs[k][:3], new[:3], base.get_proof_by_key(k), None, None))
                expect.set_leaf(k, *new)
            assert svc.compute_batch_root(R0, ops) == expect.get_root_hash()
            cases += 1
    # verification gate: a wrong pre-state root is rejected
    try:
        svc.compute_batch_root(hashlib.sha256(b"wrong").digest(), ops)
        raise AssertionError("multiproof accepted a wrong stored_root")
    except ValueError:
        pass
    # multi-leaf insert/delete is rejected (updates-only until the general multiproof)
    try:
        svc.compute_batch_root(
            R0, ops[:1] + [(hashlib.sha256(b"new").digest(), None, bl(1)[:3], [], None, None)]
        )
        raise AssertionError("multiproof accepted an insert in a multi-leaf batch")
    except ValueError:
        pass
    print(f"5 multi-leaf UPDATE multiproof == oracle ({cases} batches) + gates .. OK")

    # --- 6. another-Trezor AuthCommit CHAIN verify (Phase 4a) ---------------
    KA2 = b"K" * 32
    EH = svc.EMPTY_ROOT_HASH

    def cr(i):
        return bytes([i]) * 32

    def link(fc, fr, tc, tr):
        return (fc, fr, tc, tr, svc.auth_commit(KA2, WID, fc, fr, tc, tr))

    def fold(links, base=(0, EH)):
        rc, rr = base
        for lk in links:
            rc, rr = svc.verify_chain_step(KA2, WID, rc, rr, lk)
        return rc, rr

    good = [link(0, EH, 1, cr(1)), link(1, cr(1), 2, cr(2)), link(2, cr(2), 3, cr(3))]
    assert fold(good) == (3, cr(3))
    rejects = {
        "tampered auth_commit": good[:1]
        + [(1, cr(1), 2, cr(2), bytes([good[1][4][0] ^ 1]) + good[1][4][1:])],
        "off-path (authorized, wrong from)": good[:1] + [link(1, cr(9), 2, cr(2))],
        "counter gap": [link(0, EH, 1, cr(1)), link(1, cr(1), 3, cr(3))],
        "stale/root-resurrection": [link(0, EH, 1, cr(1)), link(5, cr(1), 6, cr(2))],
    }
    for name, bad in rejects.items():
        try:
            fold(bad)
            raise AssertionError("chain verify accepted: " + name)
        except ValueError:
            pass
    print("6 chain verify: authorized chain folds; tampered/off-path/gap/stale reject  OK")

    # --- 7. plaintext leaf mode: 0x04 domain, codec + oracle parity ---------
    import trezorlib.ward_crypto as wc

    # A fixed UPDATE batch, folded once per mode. The (entry_key, blob) set is identical;
    # only the leaf mode (hence the commit domain tag) changes, so the two roots MUST
    # differ (domain separation) while each still matches its own oracle (codec parity).
    pkeys = [hashlib.sha256(b"pk%d" % i).digest() for i in range(6)]

    def build(pt: bool):
        svc.WARD_PLAINTEXT_LEAVES = pt
        wc.WARD_PLAINTEXT_LEAVES = pt
        # plaintext leaves carry empty nonce/tag with the packed content in the ct slot;
        # encrypted leaves carry a real AEAD triple.
        def blob(i, v):
            if pt:
                return (b"", b"", wc.pack_leaf(1000 + i, b"id%d" % i, b"val%d" % v))
            return (bytes([i & 0xFF]) * 12, bytes([i & 0xFF]) * 16, b"ct%d.%d" % (i, v))

        base = WARDTree()
        blobs = {k: blob(i, 0) for i, k in enumerate(pkeys)}
        for k, b in blobs.items():
            base.set_leaf(k, *b)
        R0 = base.get_root_hash()
        expect = WARDTree()
        for k, b in blobs.items():
            expect.set_leaf(k, *b)
        ops = []
        for i, k in enumerate(pkeys[:3]):
            new = blob(i, 9)
            ops.append((k, blobs[k][:3], new[:3], base.get_proof_by_key(k), None, None))
            expect.set_leaf(k, *new)
        got = svc.compute_batch_root(R0, ops)
        assert got == expect.get_root_hash(), "batch fold != oracle in %s mode" % (
            "plaintext" if pt else "encrypted"
        )
        return got

    enc_root = build(False)
    pt_root = build(True)  # leaves consts flipped to plaintext for the checks below

    # commit domain tag: plaintext = sha256(0x04 || len32(content) || content); the codec
    # (pack/unpack) mirrors host<->firmware and round-trips.
    content = wc.pack_leaf(7, b"addr", b"value")
    assert svc.commit_of(b"", b"", content) == hashlib.sha256(
        b"\x04" + len(content).to_bytes(4, "big") + content
    ).digest()
    assert svc.commit_of(b"", b"", content) == wc.commit_of(b"", b"", content)
    assert wc.unpack_leaf(content) == (7, b"addr", b"value")
    assert svc.unpack_leaf(content) == (7, b"addr", b"value")
    assert enc_root != pt_root, "encrypted and plaintext roots must differ (0x02 vs 0x04)"

    # restore the production default so a later import sees encrypted mode.
    svc.WARD_PLAINTEXT_LEAVES = False
    wc.WARD_PLAINTEXT_LEAVES = False
    print("7 plaintext mode: 0x04 commit + pack/unpack parity + oracle fold ... OK")

    print("\nALL WARD BATCH-UPDATE SELF-CHECKS PASSED")


if __name__ == "__main__":
    main()
