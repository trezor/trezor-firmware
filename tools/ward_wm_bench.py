#!/usr/bin/env python3
"""WARD Manager (WM) successor-only CAS self-test + MAC-vs-Ed25519 benchmark.

Part A exercises the WM emulator's successor-only compare-and-swap register
(tests/ward_mgr_emu.py): a transition is accepted only if it extends the current
head, a stale-base submit raises WMConflict (the 409 the connect client rebases on),
and — when WARD_KSIG is on — the device's Ed25519 SigCommit is verified at ingest
(F4) and a forged one is rejected.

Part B answers the D1 benchmark question — the cost of the transition authorization
with WARD_KSIG OFF (symmetric MACs only) vs ON (MACs + one Ed25519 signature). The
key result is analytical and holds regardless of batch size: WARD_KSIG adds exactly
ONE Ed25519 sign per transition on the device and ONE verify on the WM, because the
signature covers the fixed-size (from,to) transition tuple, not each leaf.

Usage:  python3 tools/ward_wm_bench.py

CAVEAT: the CPython timings below use the pure-python trezorlib._ed25519 reference
and hashlib — they show the RELATIVE shape (Ed25519 ≫ HMAC), not device time. The
real per-commit latency must be measured on the emulator/device, where Ed25519 is
hardware/optimised. This tool bounds the *structure* of the cost, not its absolute.
"""
import hashlib
import hmac as _hmac
import os
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "python", "src"))
sys.path.insert(0, os.path.join(REPO, "tests"))

from trezorlib import _ed25519  # noqa: E402
import ward_mgr_emu as wm_emu  # noqa: E402


def _sign_commit(wm, ward_id, fc, fr, tc, tr, kind="commit"):
    """Produce a valid device SigCommit over the transition preimage (test-only: the
    device holds K_sig; here we reproduce it from the known seed)."""
    ksig = wm_emu._slip21_key(wm.seed, [b"ward", b"K_sig"])
    pk = _ed25519.publickey_unsafe(ksig)
    tag = wm_emu._TAG_REVERT if kind == "revert" else wm_emu._TAG_COMMIT
    pre = wm_emu._transition_preimage(tag, ward_id, fc, fr, tc, tr)
    return _ed25519.signature_unsafe(pre, ksig, pk)


def part_a_cas() -> None:
    print("== Part A: WM successor-only CAS ==")
    ward_id = bytes(range(32))
    wm = wm_emu.WMEmulator()
    R1, R2 = b"\x11" * 32, b"\x22" * 32

    assert wm.head(ward_id) == (0, None, None)
    sig1 = wm.submit_transition(ward_id, 0, None, 1, R1, b"m1")
    assert wm.head(ward_id) == (1, R1, b"m1") and len(sig1) == 64
    print("  accept genesis -> (1, R1) ................................ OK")

    # A stale-base resubmit (from the old head) is a 409 -> rebase.
    try:
        wm.submit_transition(ward_id, 0, None, 1, R1, b"m1")
        raise AssertionError("expected WMConflict on stale base")
    except wm_emu.WMConflict as c:
        assert (c.counter, c.root) == (1, R1)
    print("  stale-base submit -> WMConflict(head=1) .................. OK")

    wm.submit_transition(ward_id, 1, R1, 2, R2, b"m2")
    assert wm.head(ward_id) == (2, R2, b"m2") and len(wm.transitions(ward_id)) == 2
    print("  successor (1->2) advances head + records history ........ OK")

    # WARD_KSIG on: SigCommit verified at ingest (F4).
    wmk = wm_emu.WMEmulator(verify_sig_commit=True)
    good = _sign_commit(wmk, ward_id, 0, None, 1, R1)
    wmk.submit_transition(ward_id, 0, None, 1, R1, b"m1", sig_commit=good)
    print("  WARD_KSIG: valid SigCommit accepted ...................... OK")
    forged = bytearray(_sign_commit(wmk, ward_id, 1, R1, 2, R2))
    forged[0] ^= 1
    try:
        wmk.submit_transition(ward_id, 1, R1, 2, R2, b"m2", sig_commit=bytes(forged))
        raise AssertionError("expected forged SigCommit rejection")
    except ValueError:
        pass
    assert wmk.head(ward_id) == (1, R1, b"m1")  # head did NOT advance on the forged one
    print("  WARD_KSIG: forged SigCommit rejected at ingest (F4) ...... OK")


def _bench(fn, iters):
    t0 = time.perf_counter()
    for _ in range(iters):
        fn()
    return (time.perf_counter() - t0) / iters * 1e6  # microseconds/op


def part_b_bench() -> None:
    print("\n== Part B: transition-auth cost, WARD_KSIG off vs on ==")
    key = b"k" * 32
    msg = b"m" * 108  # ~ a transition preimage (tag+ward_id+2*(4+32))
    ksig = hashlib.sha256(b"seed").digest()
    pk = _ed25519.publickey_unsafe(ksig)
    sig = _ed25519.signature_unsafe(msg, ksig, pk)

    us_hmac = _bench(lambda: _hmac.new(key, msg, hashlib.sha256).digest(), 20000)
    us_sha = _bench(lambda: hashlib.sha256(msg).digest(), 40000)
    us_sign = _bench(lambda: _ed25519.signature_unsafe(msg, ksig, pk), 30)
    us_verify = _bench(lambda: _ed25519.checkvalid(sig, msg, pk), 30)

    print(f"  per-op (CPython, indicative): HMAC-SHA256={us_hmac:.2f}us  "
          f"SHA256={us_sha:.2f}us  Ed25519-sign={us_sign:.0f}us  Ed25519-verify={us_verify:.0f}us")

    print("\n  Per-transition authorization work (independent of what the batch touches):")
    print("    MACs always: head_mac + AuthCommit + root_mac = 3 x HMAC-SHA256")
    print("    WARD_KSIG delta: +1 Ed25519 sign (device) , +1 Ed25519 verify (WM)")
    depth = 20  # ~log2(1e6)
    print(f"\n  {'batch':>5} | {'MAC-only auth':>16} | {'+WARD_KSIG (device)':>20} | {'WM verify':>10}")
    print("  " + "-" * 60)
    for n in (1, 10, 50):
        # fold hashing is the batch's structural cost (not the auth delta); shown for context
        fold_us = n * depth * us_sha
        mac_auth = 3 * us_hmac
        ksig_dev = mac_auth + us_sign
        print(f"  {n:>5} | {mac_auth:>13.1f}us | {ksig_dev:>17.1f}us | {us_verify:>7.0f}us"
              f"   (fold≈{fold_us:.0f}us)")
    print("\n  => The Ed25519 overhead is O(1) per transition (one sign + one verify),")
    print("     NOT per leaf: a 1-leaf and a 50-leaf batch pay the SAME signature cost.")
    print("     Absolute device numbers require an emulator/hardware run (Ed25519 there")
    print("     is hardware-accelerated, ~1000x faster than this pure-python reference).")


if __name__ == "__main__":
    part_a_cas()
    part_b_bench()
    print("\nWARD WM CAS + BENCHMARK: OK")
