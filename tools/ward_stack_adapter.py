#!/usr/bin/env python3
"""The WARD ADAPTER of `tools/ward_stack.py`: one WARD session through wardd, step by step.

    ward_stack_adapter.py --port 37744 --wardd ws://127.0.0.1:21329 --token-file F

It stands in for the WARD app. Every write goes through the device and is stored and published by
wardd (`WarddProvider.apply_result`); the device adopts the new head on the next sync. Every read
is a pull the device verifies against its root, served by wardd from its Evolu replica. Screens are
confirmed over the emulator's debuglink (wire port + 1), and what each one showed is kept, so a
read is checked on the screen it produced rather than on its acknowledgement alone.

Arc: sync -> write an entry -> read it, fresh: no warning -> point an alias at it -> read the
alias -> update the entry -> read the alias again -> queue three changes and flush them as one
batch -> delete the entry -> read the alias as "not found" -> replica and WM agree -> TAKE THE WM
DOWN -> a new session cannot sync (wm_unavailable) and reads its last head under the "Not proven
current" warning -> START A SECOND DEVICE of the same wallet, with its own wardd, whose replica
fills from the relay -> the second device CATCHES UP WITHOUT THE WM (session only, warned) -> both
devices queue different values for the same two contacts -> bring the WM back -> the first device
syncs and flushes: the relay stores it and the WM accepts it -> the second device syncs and
flushes: contact1 is resolved KEEP ORIGINAL, contact2 KEEP NEW -> both devices read the same
resolved values -> the first device progresses -> WM DOWN -> the second device catches up to it
without the WM -> serving the second device a root OLDER than it stored is refused, as a head and
as a read -> after the WM restarted, a write from the session before is refused -> an entry added
and then deleted leaves exactly the root from before the add, on the device and in both replicas
-> THE WM IS RESTORED FROM A BACKUP taken at #10 -> the first device detects it during its sync,
the user approves, the device signs the changes since again (roll-forward) and shows when the WM
accepted the last of them -> the WM is back at the head, and the next sync just reconciles.

Counters are relative to the head the session starts at, so the arc can be rerun on the same
device. The WM steps need the stack's run directory (`WARD_STACK_RUN_DIR`) and are skipped
without it.

Exits 0 when every step passed; prints one line per step either way.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import typing as t
from pathlib import Path


def _import_paths() -> None:
    root = os.environ.get("TREZOR_FIRMWARE")
    root = root or str(Path(__file__).resolve().parents[1])
    sys.path.insert(0, str(Path(root) / "python" / "src"))


_import_paths()

from trezorlib import (  # noqa: E402
    evolu,
    exceptions,
    ward,
    ward_adversarial,
    ward_relay,
)
from trezorlib.client import get_default_client  # noqa: E402
from trezorlib.debuglink import DebugLink  # noqa: E402
from trezorlib.transport.udp import UdpTransport  # noqa: E402

if t.TYPE_CHECKING:
    from trezorlib.client import Session

APP_ID = "stack_app"
# the freshness warning without the WM, as `Screens.take` squashes it: dated by the WM's timestamp
# for the head the read proves against ("Not reflecting changes since <date> UTC, nor user reverts.")
WARNING = "notreflectingchangessince"


def switch_wm(run_dir: Path, down: bool, timeout: float = 60) -> bool:
    """Ask the stack to take the WM down (or bring it back) and wait until it has."""
    request = run_dir / "wm.down"
    if down:
        request.touch()
    else:
        request.unlink(missing_ok=True)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if (run_dir / "wm.stopped").exists() == down:
            return True
        time.sleep(0.2)
    return False


def evolu_node(session: "Session") -> bytes:
    """The device's Evolu node, which owns wardd's persistent replica. `EvoluGetNode` wants a
    proof of the delegated identity: its key, from the device, signs the request header (as the
    Evolu device tests do; codec wallet channel)."""
    from hashlib import sha256

    from ecdsa import NIST256p, SigningKey

    from trezorlib.tools import compact_size

    key = evolu.get_delegated_identity_key(session).private_key
    header = b"EvoluGetNode"
    digest = sha256(compact_size(len(header)) + header).digest()
    proof = SigningKey.from_string(key, curve=NIST256p).sign_digest(digest)
    return evolu.get_node(session, proof=proof, node_rotation_index=0)


class Screens:
    """Confirms every screen over debuglink and keeps what it showed.

    `answers` declines chosen screens: a list of yes/no per ButtonRequest name, used in order;
    every other screen is confirmed.
    """

    def __init__(self, debug: DebugLink, delay: float) -> None:
        self.debug = debug
        self.delay = delay
        self.seen: list[str] = []
        self.answers: dict[str, list[bool]] = {}

    def _read(self) -> str:
        layout = self.debug.read_layout()
        return f"{layout.title()} {layout.text_content()}"

    def _record(self) -> str:
        try:
            shown = self._read()
        except Exception as e:  # a screen we cannot read is still confirmed
            shown = f"<unreadable: {e}>"
        self.seen.append(shown)
        return shown

    def _next_page(self, current: str) -> None:
        """Swipe, then wait until the page has actually changed: with the display shown the
        next page animates in, and paging stays within one layout, so nothing else waits."""
        self.debug.swipe_up()
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            try:
                if self._read() != current:
                    return
            except Exception:
                return
            time.sleep(0.05)

    def __call__(self, br: object) -> None:
        # a long screen is several pages; read each before confirming the last
        for _ in range((getattr(br, "pages", None) or 1) - 1):
            self._next_page(self._record())
        self._record()
        if self.delay:
            time.sleep(self.delay)
        queued = self.answers.get(getattr(br, "name", None) or "")
        if queued and not queued.pop(0):
            self.debug.press_no()
        else:
            self.debug.press_yes()

    def take(self) -> str:
        shown, self.seen = " | ".join(self.seen), []
        return "".join(shown.split())  # wrapped values gain spaces; compare without them


def wait_files(run_dir: Path, names: tuple[str, ...], timeout: float = 120) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if all((run_dir / name).exists() for name in names):
            return True
        time.sleep(0.5)
    return False


def wait_replica(client: ward_relay.WarddClient, counter: int, timeout: float = 90) -> dict:
    """Poll a wardd until its replica reaches `counter` and holds the WM's attestation of it (both
    fill from the relay, as separate rows): `catch_up` goes only as far as a kept attestation."""
    deadline = time.monotonic() + timeout
    st = ward_relay.status(client)
    while time.monotonic() < deadline and (
        st.get("counter") != counter or st.get("attestedCounter") != counter
    ):
        time.sleep(1)
        st = ward_relay.status(client)
    return st


def count_lines(path: Path, needle: str) -> int:
    try:
        return sum(needle in line for line in path.read_text().splitlines())
    except OSError:
        return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=int(os.environ.get("TREZOR_UDP_PORT", 21324)))
    ap.add_argument("--wardd", default=os.environ.get("WARDD_URL", ward_relay.WARDD_DEFAULT_URL))
    ap.add_argument(
        "--token-file",
        type=Path,
        default=Path(os.environ.get("WARD_TOKEN_FILE", ward_relay.DEFAULT_TOKEN_FILE)),
    )
    ap.add_argument(
        "--confirm-delay",
        type=float,
        default=float(os.environ.get("WARD_CONFIRM_DELAY", 0)),
        help="seconds to leave each screen up before confirming it",
    )
    args = ap.parse_args()

    failures = 0

    def step(label: str, ok: bool, detail: str = "") -> None:
        nonlocal failures
        print(f"  {'ok  ' if ok else 'FAIL'} {label}{f' -- {detail}' if detail else ''}", flush=True)
        if not ok:
            failures += 1

    debug = DebugLink(UdpTransport(f"127.0.0.1:{args.port + 1}"), auto_interact=True)
    screens = Screens(debug, args.confirm_delay)
    try:
        client = get_default_client(
            "ward-stack-adapter",
            UdpTransport(f"127.0.0.1:{args.port}"),
            button_callback=screens,
        )
        session = client.get_session(passphrase="")
        token = args.token_file.read_text().strip()
        with ward_relay.WarddClient(token, args.wardd) as wardd:
            provider = ward_relay.WarddProvider(wardd)

            def write(call: t.Callable[[ward_relay.WarddProvider], t.Any]) -> int:
                result = call(provider)
                provider.apply_result(result)
                return ward_relay.sync(session, wardd)["counter"]

            def read(identifier: bytes) -> str:
                ward.get_entry(session, APP_ID, identifier, provider)
                return screens.take()

            print("== WARD stack: one session through wardd", flush=True)
            opened = ward_relay.open_store(session, wardd, evolu_node=evolu_node(session))
            step("store opened", "counter" in opened, f"counter={opened.get('counter')}")
            synced = ward_relay.sync(session, wardd)
            base = synced.get("counter", 0)
            step("synced with the WM", "counter" in synced, str(synced))

            counter = write(lambda p: ward.set_entry(session, APP_ID, b"addr1", b"label_one", p))
            step("entry written and adopted", counter == base + 1, f"counter={counter}")
            shown = read(b"addr1")
            step("entry read back on screen", "label_one" in shown, shown)
            step(
                "the WM attested this session's head: no freshness warning",
                WARNING not in shown.lower(),
                shown,
            )

            counter = write(lambda p: ward.set_pointer(session, APP_ID, b"alias", b"addr1", p))
            step("pointer written and adopted", counter == base + 2, f"counter={counter}")
            shown = read(b"alias")
            step(
                "pointer read follows one hop to the target's value",
                "label_one" in shown and "Pointstoaddr1" in shown,
                shown,
            )

            counter = write(lambda p: ward.set_entry(session, APP_ID, b"addr1", b"label_two", p))
            step("entry updated and adopted", counter == base + 3, f"counter={counter}")
            shown = read(b"alias")
            step("pointer sees the update", "label_two" in shown, shown)

            for i in range(3):
                ward.queue_set_entry(session, APP_ID, b"q%d" % i, b"queued_%d" % i)
            screens.take()
            flushed = ward_relay.flush(session, wardd, max_batch=8)
            # ONE transition carrying three changes: the counter moves by three, published once
            step(
                "three queued changes flushed as one batch",
                flushed.get("counter") == base + 6 and flushed.get("published") == 1,
                str(flushed),
            )
            ward_relay.sync(session, wardd)

            counter = write(lambda p: ward.delete_entry(session, APP_ID, b"addr1", p))
            step("entry deleted and adopted", counter == base + 7, f"counter={counter}")
            shown = read(b"alias")
            step("pointer to a deleted entry reads as not found", "notfound" in shown.lower(), shown)

            st = ward_relay.status(wardd)
            step(
                "replica and WM agree",
                st.get("counter") == st.get("wmCounter") == base + 7 and not st.get("behind"),
                str(st),
            )

            run_dir = os.environ.get("WARD_STACK_RUN_DIR")
            if run_dir is None:
                print("  skip the WM steps: no WARD_STACK_RUN_DIR", flush=True)
            else:
                print("== WARD stack: the same device with the WM down", flush=True)
                step("WM taken down", switch_wm(Path(run_dir), down=True))
                st = ward_relay.status(wardd)
                step("wardd reports the WM unavailable", st.get("wmAvailable") is False, str(st))
                # A NEW SESSION starts with no attested head: only a sync could give it one
                offline = client.get_session(passphrase="")
                try:
                    ward_relay.sync(offline, wardd)
                    step("sync without the WM fails", False, "it succeeded")
                except ward_relay.WarddError as e:
                    step("sync without the WM fails", e.code == "wm_unavailable", str(e))
                ward.get_entry(offline, APP_ID, b"q0", provider)
                shown = screens.take()
                step(
                    "read proves against the last adopted head, with the warning",
                    "queued_0" in shown and WARNING in shown.lower(),
                    shown,
                )

                conflicts(
                    step,
                    Path(run_dir),
                    args,
                    token,
                    client,
                    offline,
                    wardd,
                    provider,
                    screens,
                    base,
                )
    except ward_relay.WarddError as e:
        step("wardd answered", False, f"{e.code}: {e}")
    except Exception as e:
        step("the session ran", False, f"{type(e).__name__}: {e}")
    finally:
        debug.close()

    print(
        "== WARD stack: all steps passed" if not failures else f"== WARD stack: {failures} FAILED",
        flush=True,
    )
    return 0 if not failures else 1


def conflicts(
    step: t.Callable[..., None],
    run_dir: Path,
    args: argparse.Namespace,
    token: str,
    client: t.Any,
    a: "Session",
    wardd_a: ward_relay.WarddClient,
    provider_a: ward_relay.WarddProvider,
    screens_a: Screens,
    base: int,
) -> None:
    """Two devices of one wallet queue different values for the same entries while the WM is
    down; the second resolves them at its flush. `a` is the first device's offline session."""
    print("== WARD stack: a second device, and conflicting changes queued offline", flush=True)
    (run_dir / "second.ready").touch()
    step(
        "second device started: its own wardd and emulator",
        wait_files(run_dir, ("wardd2.ready", "emulator2.ready")),
    )
    port_b = int(os.environ.get("TREZOR_UDP_PORT2", args.port + 8))
    debug_b = DebugLink(UdpTransport(f"127.0.0.1:{port_b + 1}"), auto_interact=True)
    screens_b = Screens(debug_b, args.confirm_delay)
    try:
        client_b = get_default_client(
            "ward-stack-adapter-2",
            UdpTransport(f"127.0.0.1:{port_b}"),
            button_callback=screens_b,
        )
        b = client_b.get_session(passphrase="")
        url_b = os.environ.get("WARDD2_URL", "ws://127.0.0.1:21331")
        with ward_relay.WarddClient(token, url_b) as wardd_b:
            provider_b = ward_relay.WarddProvider(wardd_b)

            # THE SECOND DEVICE JOINS WITH THE WM DOWN: its wardd fills from the relay, and the
            # device follows the wallet's own chain up to that head, for this session only
            ward_relay.open_store(b, wardd_b, evolu_node=evolu_node(b))
            st_b = wait_replica(wardd_b, base + 7)
            step(
                "device 2's wardd filled its replica from the relay, without the WM",
                st_b.get("counter") == base + 7 and st_b.get("wmAvailable") is False,
                str(st_b),
            )
            caught = ward_relay.catch_up(b, wardd_b)
            step("device 2 caught up without the WM", caught.get("counter") == base + 7, str(caught))
            ward.get_entry(b, APP_ID, b"q0", provider_b)
            shown = screens_b.take()
            step(
                "device 2 reads what it caught up to, under the warning",
                "queued_0" in shown and WARNING in shown.lower(),
                shown,
            )

            # the same entry_key -- same wallet, domain and identifier -- different values
            for name, value in ((b"contact1", b"alice_from_A"), (b"contact2", b"bob_from_A")):
                ward.queue_set_entry(a, APP_ID, name, value)
            for name, value in ((b"contact1", b"alice_from_B"), (b"contact2", b"bob_from_B")):
                ward.queue_set_entry(b, APP_ID, name, value)
            screens_a.take()
            screens_b.take()
            step("both devices queued contact1 and contact2 offline, with different values", True)

            stored_before = count_lines(run_dir / "relay.log", "[store] message")
            step("WM back up", switch_wm(run_dir, down=False))
            ward_relay.sync(a, wardd_a)
            flushed = ward_relay.flush(a, wardd_a, max_batch=8)
            step(
                "device 1 flushed its queue: one transition with both contacts",
                flushed.get("counter") == base + 9 and flushed.get("published") == 1,
                str(flushed),
            )
            st = ward_relay.status(wardd_a)
            step(
                "the WM accepted it",
                st.get("counter") == st.get("wmCounter") == base + 9,
                str(st),
            )
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                if count_lines(run_dir / "relay.log", "[store] message") > stored_before:
                    break
                time.sleep(0.5)
            step(
                "the relay stored it (Evolu)",
                count_lines(run_dir / "relay.log", "[store] message") > stored_before,
            )

            st_b = wait_replica(wardd_b, base + 9)
            step(
                "device 2's wardd received device 1's transition from the relay",
                st_b.get("counter") == st_b.get("wmCounter") == base + 9,
                str(st_b),
            )
            synced = ward_relay.sync(b, wardd_b)
            step("device 2 synced to the WM head", synced.get("counter") == base + 9, str(synced))

            # contact1 first: decline "keep yours", confirm "keep published"; contact2: keep yours
            screens_b.answers = {"ward_conflict_keep_new": [False, True]}
            flushed = ward_relay.flush(b, wardd_b, max_batch=8)
            shown = screens_b.take()
            step(
                "device 2 was shown both conflicts",
                shown.count("Conflictingchange") >= 2
                and "alice_from_A" in shown
                and "alice_from_B" in shown
                and "bob_from_B" in shown,
                shown,
            )
            step(
                "contact1 resolved KEEP ORIGINAL, contact2 KEEP NEW: one transition",
                flushed.get("counter") == base + 10 and flushed.get("published") == 1,
                str(flushed),
            )

            def read(
                session: "Session",
                wardd_provider: ward_relay.WarddProvider,
                screens: Screens,
                name: bytes,
            ) -> str:
                ward.get_entry(session, APP_ID, name, wardd_provider)
                return screens.take()

            shown = read(b, provider_b, screens_b, b"contact1")
            step("device 2 reads contact1 = alice_from_A (original kept)", "alice_from_A" in shown, shown)
            shown = read(b, provider_b, screens_b, b"contact2")
            step("device 2 reads contact2 = bob_from_B (new kept)", "bob_from_B" in shown, shown)
            copy = ward.queue_get_entry(b, APP_ID, b"contact1")
            screens_b.take()
            step(
                "device 2's queued contact1 became an offline copy of the original",
                copy.value == b"alice_from_A" and not copy.pending,
                f"value={copy.value!r} pending={copy.pending}",
            )

            ward_relay.sync(a, wardd_a)
            shown = read(a, provider_a, screens_a, b"contact1")
            step("device 1 reads contact1 = alice_from_A", "alice_from_A" in shown, shown)
            shown = read(a, provider_a, screens_a, b"contact2")
            step(
                "device 1 reads contact2 = bob_from_B, fresh",
                "bob_from_B" in shown and WARNING not in shown.lower(),
                shown,
            )
            st_a, st_b = ward_relay.status(wardd_a), ward_relay.status(wardd_b)
            # A BACKUP OF THE WM'S REGISTER at this head, restored at the end of the session
            wm_backup = run_dir / "wm-backup.json"
            wm_backup.write_bytes((run_dir / "wm" / "wm.json").read_bytes())
            step(
                "both wardd replicas and the WM agree",
                st_a.get("counter") == st_b.get("counter") == st_a.get("wmCounter") == base + 10
                and st_a.get("root") == st_b.get("root"),
                f"{st_a} / {st_b}",
            )

            print("== WARD stack: device 1 moves on; device 2 without the WM", flush=True)
            result = ward.set_entry(a, APP_ID, b"contact3", b"carol_from_A", provider_a)
            provider_a.apply_result(result)
            counter = ward_relay.sync(a, wardd_a)["counter"]
            screens_a.take()
            step("device 1 progressed: contact3 written", counter == base + 11, f"counter={counter}")
            step("WM taken down", switch_wm(run_dir, down=True))

            b2 = client_b.get_session(passphrase="")
            st_b = wait_replica(wardd_b, base + 11)
            step("device 2's wardd received it from the relay", st_b.get("counter") == base + 11, str(st_b))
            caught = ward_relay.catch_up(b2, wardd_b)
            step(
                "device 2 caught up #%d -> #%d without the WM" % (base + 10, base + 11),
                caught.get("counter") == base + 11,
                str(caught),
            )
            ward.get_entry(b2, APP_ID, b"contact3", provider_b)
            shown = screens_b.take()
            step(
                "device 2 reads contact3, dated by the WM's last attestation",
                "carol_from_A" in shown and WARNING in shown.lower(),
                shown,
            )

            # ADVERSARIAL TESTS: device 2's wardd (`--adversarial-tests`) turns hostile and serves
            # device 2 (stored head #base+10) an OLDER state, two ways. Both must be refused.
            print("== WARD stack: adversarial tests (wardd serves an older state)", flush=True)
            older = base + 7
            b3 = client_b.get_session(passphrase="")
            try:
                ward_adversarial.adversarial_catch_up_to_older_head(b3, wardd_b, older)
                step("ADVERSARIAL: an older head (#%d) is refused" % older, False, "it was accepted")
            except ward_relay.WarddError as e:
                step(
                    "ADVERSARIAL: an older head (#%d) is refused" % older,
                    e.code == "device_failure" and "older than" in str(e),
                    str(e),
                )
            try:
                ward.get_entry(
                    b3, APP_ID, b"q0", ward_adversarial.AdversarialOlderTreeProvider(wardd_b, older)
                )
                step("ADVERSARIAL: a read from the older tree is refused", False, "it was shown")
            except exceptions.TrezorFailure as e:
                step(
                    "ADVERSARIAL: a read answered from the tree at #%d is refused" % older,
                    "trusted root" in str(e),
                    str(e),
                )
            screens_b.take()
            step("WM back up", switch_wm(run_dir, down=False))

            # ADD, THEN DELETE: the tree depends on what it holds, not on what it once held
            print("== WARD stack: add an entry, then delete it", flush=True)
            # THE WM RESTARTED, and its sessions are volatile: a write device 1 authorises in the
            # session it synced before the restart is refused, so it syncs before it writes
            # (docs/ward/ward_transitions.md, sessions)
            stale = ward.set_entry(a, APP_ID, b"temp", b"stale", provider_a)
            try:
                provider_a.apply_result(stale)
                step("a write from the session before the WM restart is refused", False, "it landed")
            except ward_relay.WarddError as e:
                step(
                    "a write from the session before the WM restart is refused",
                    "no session" in str(e),
                    str(e),
                )
            ward_relay.sync(a, wardd_a)
            root_before = ward_relay.status(wardd_a).get("root")
            result = ward.set_entry(a, APP_ID, b"temp", b"short_lived", provider_a)
            provider_a.apply_result(result)
            added = ward_relay.sync(a, wardd_a)
            step(
                "entry added: the root moved",
                added.get("counter") == base + 12 and added.get("root") != root_before,
                str(added),
            )
            result = ward.delete_entry(a, APP_ID, b"temp", provider_a)
            provider_a.apply_result(result)
            deleted = ward_relay.sync(a, wardd_a)
            screens_a.take()
            step(
                "entry deleted: device 1 adopted the root from before the add",
                deleted.get("counter") == base + 13 and deleted.get("root") == root_before,
                f"{deleted} vs before {root_before}",
            )
            st_b = wait_replica(wardd_b, base + 13)
            step(
                "device 2's replica rebuilt the same root from the relay",
                st_b.get("root") == root_before,
                str(st_b),
            )

            # THE WM IS RESTORED FROM A BACKUP: its register goes back to #10 and its sessions are
            # gone. Device 1 detects it during its sync, the user approves, the device signs the
            # changes the WM accepted since again for this session, and finally shows when the WM
            # accepted the last of them (docs/ward/ward_transitions.md, roll-forward)
            print("== WARD stack: the WM restored from a backup, rolled forward", flush=True)
            restored_to = base + 10
            switch_wm(run_dir, down=True)
            (run_dir / "wm" / "wm.json").write_bytes(wm_backup.read_bytes())
            up = switch_wm(run_dir, down=False)
            st = ward_relay.status(wardd_a)
            step(
                "WM restored from the backup at #%d" % restored_to,
                up and st.get("wmCounter") == restored_to,
                str(st),
            )
            screens_a.take()
            rolled = ward_relay.sync(a, wardd_a)
            shown = screens_a.take()
            outcome = rolled.get("rolledForward") or {}
            step(
                "device 1 detected the restored WM during sync, and the user approved",
                "RestoreWARDhistory" in shown,
                shown,
            )
            step(
                "device 1 signed #%d -> #%d again; the WM accepted them"
                % (restored_to, base + 13),
                outcome.get("steps") == 3 and outcome.get("toCounter") == base + 13,
                str(rolled),
            )
            accepted = outcome.get("lastTimestamp") or 0
            day = time.strftime("%Y-%m-%d", time.gmtime(accepted))
            step(
                "device 1 showed when the WM accepted the last restored change (%s UTC)"
                % time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(accepted)),
                "WARDhistoryrestored" in shown and "Lastchangeaccepted" in shown and day in shown,
                shown,
            )
            st_a = ward_relay.status(wardd_a)
            step(
                "the WM is back at #%d, and the replica agrees" % (base + 13),
                st_a.get("wmCounter") == st_a.get("counter") == base + 13
                and st_a.get("wmRoot") == st_a.get("root") == root_before,
                str(st_a),
            )
            step(
                "device 1 adopted it: the next sync just reconciles",
                ward_relay.sync(a, wardd_a).get("counter") == base + 13,
            )
    finally:
        debug_b.close()


if __name__ == "__main__":
    sys.exit(main())
