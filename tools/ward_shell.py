#!/usr/bin/env python3
"""Drive a running WARD stack by hand, from a Python shell.

    python -i tools/ward_shell.py RUN_DIR [--manual]

RUN_DIR is the directory `tools/ward_stack.py` printed. The shell connects to device 1 (`d1`)
through its wardd and, once the stack has started it, to device 2 (`d2`) through the second wardd.
Every screen is confirmed over debuglink and printed; with `--manual` you confirm on the emulator
display yourself.

    d1.sync()                      # WardSync and adoption of the WM's head
    d1.put("contact", "alice")     # WardSetEntry, stored and published by wardd, then synced
    d1.get("contact")              # WardGetEntry: what the screen showed
    d1.delete("contact")
    d1.queue("contact", "bob")     # WardQueueSetEntry: held on the device
    d1.flush()                     # publish the queue (conflicts are asked on the device)
    d1.status()                    # wardd's replica head and the WM's
    wm_down(); wm_up()             # stop / start the WARD Manager
    start_second()                 # start device 2 and its wardd (if the adapter has not)
    d2.catch_up()                  # WardCatchUp: up to the newest WM-attested head, no WM
    d1.new_session()               # a fresh session: no attested head yet

    # ADVERSARIAL TESTS, through device 2's wardd (started with --adversarial-tests):
    d2.new_session()               # an older head is offered as a catch-up: no attested head yet
    d2.adversarial_older_head(7)   # offer an older head: the device must refuse
    d2.adversarial_read("q0", 7)   # answer a read from the tree at #7: the device must refuse

Decline the next conflict question with `d2.answer("ward_conflict_keep_new", False)`.
"""

from __future__ import annotations

import json
import os
import sys
import typing as t
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python" / "src"))

from tools.ward_stack_adapter import (  # noqa: E402
    APP_ID,
    Screens,
    evolu_node,
    switch_wm,
    wait_files,
)
from trezorlib import exceptions, ward, ward_adversarial, ward_relay  # noqa: E402
from trezorlib.client import get_default_client  # noqa: E402
from trezorlib.debuglink import DebugLink  # noqa: E402
from trezorlib.transport.udp import UdpTransport  # noqa: E402


def _b(text: "str | bytes") -> bytes:
    return text if isinstance(text, bytes) else text.encode()


class Device:
    """One emulator, its wardd, and a session on it."""

    def __init__(self, name: str, port: int, wardd_url: str, token: str, manual: bool) -> None:
        self.name = name
        self.debug = DebugLink(UdpTransport(f"127.0.0.1:{port + 1}"), auto_interact=True)
        self.screens = Screens(self.debug, 0.0)
        callback = None if manual else self._confirm
        self.client = get_default_client(
            f"ward-shell-{name}", UdpTransport(f"127.0.0.1:{port}"), button_callback=callback
        )
        self.session = self.client.get_session(passphrase="")
        self.wardd = ward_relay.WarddClient(token, wardd_url)
        self.wardd.__enter__()
        self.provider = ward_relay.WarddProvider(self.wardd)
        opened = ward_relay.open_store(self.session, self.wardd, evolu_node=evolu_node(self.session))
        print(f"{name}: store opened at counter {opened.get('counter')}")

    def _confirm(self, br: t.Any) -> None:
        self.screens(br)
        for page in self.screens.seen:
            print(f"  [{self.name} screen] {page}")
        self.screens.seen = []

    def _call(self, what: str, fn: t.Callable[[], t.Any]) -> t.Any:
        try:
            result = fn()
        except (ward_relay.WarddError, exceptions.TrezorFailure) as e:
            print(f"{self.name}: {what} REFUSED -- {e}")
            return None
        return result

    def answer(self, br_name: str, yes: bool) -> None:
        """Answer the next screen named `br_name` with yes or no (default: yes)."""
        self.screens.answers.setdefault(br_name, []).append(yes)

    def new_session(self) -> None:
        """A fresh session: it holds no WM-attested head until it syncs."""
        self.session = self.client.get_session(passphrase="")

    def sync(self) -> t.Any:
        return self._call("sync", lambda: ward_relay.sync(self.session, self.wardd))

    def catch_up(self) -> t.Any:
        return self._call("catch-up", lambda: ward_relay.catch_up(self.session, self.wardd))

    def status(self) -> dict:
        return ward_relay.status(self.wardd)

    def _write(self, what: str, call: t.Callable[[t.Any], t.Any]) -> t.Any:
        def run() -> dict:
            result = call(self.provider)
            applied = self.provider.apply_result(result, self.session)
            return applied.get("synced") or ward_relay.sync(self.session, self.wardd)

        return self._call(what, run)

    def put(self, identifier: "str | bytes", value: "str | bytes") -> t.Any:
        return self._write(
            "put", lambda p: ward.set_entry(self.session, APP_ID, _b(identifier), _b(value), p)
        )

    def point(self, identifier: "str | bytes", target: "str | bytes") -> t.Any:
        return self._write(
            "pointer",
            lambda p: ward.set_pointer(self.session, APP_ID, _b(identifier), _b(target), p),
        )

    def delete(self, identifier: "str | bytes") -> t.Any:
        return self._write(
            "delete", lambda p: ward.delete_entry(self.session, APP_ID, _b(identifier), p)
        )

    def get(self, identifier: "str | bytes") -> t.Any:
        return self._call(
            "get",
            lambda: ward.get_entry(self.session, APP_ID, _b(identifier), self.provider),
        )

    def queue(self, identifier: "str | bytes", value: "str | bytes") -> t.Any:
        return self._call(
            "queue",
            lambda: ward.queue_set_entry(self.session, APP_ID, _b(identifier), _b(value)),
        )

    def local(self, identifier: "str | bytes") -> t.Any:
        """WardQueueGetEntry: the device's own copy, no host involved."""
        return self._call(
            "local read", lambda: ward.queue_get_entry(self.session, APP_ID, _b(identifier))
        )

    def flush(self, max_batch: int = 8) -> t.Any:
        return self._call(
            "flush", lambda: ward_relay.flush(self.session, self.wardd, max_batch=max_batch)
        )

    # --- ADVERSARIAL TESTS: device 2's wardd serves an older state on purpose -------------

    def adversarial_older_head(self, counter: int) -> t.Any:
        """ADVERSARIAL TEST: wardd offers this device the older head `counter`."""
        return self._call(
            "ADVERSARIAL older head",
            lambda: ward_adversarial.adversarial_catch_up_to_older_head(
                self.session, self.wardd, counter
            ),
        )

    def adversarial_read(self, identifier: "str | bytes", counter: int) -> t.Any:
        """ADVERSARIAL TEST: wardd answers this read from the tree at the older head `counter`."""
        return self._call(
            "ADVERSARIAL read",
            lambda: ward.get_entry(
                self.session,
                APP_ID,
                _b(identifier),
                ward_adversarial.AdversarialOlderTreeProvider(self.wardd, counter),
            ),
        )


def main() -> None:
    global d1, d2, run_dir, config, manual  # the shell's names
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    run_dir = Path(sys.argv[1])
    manual = "--manual" in sys.argv[2:]
    config = json.loads((run_dir / "config.json").read_text())
    env = config["environment"]
    token = (run_dir / "token").read_text().strip()
    d1 = Device("d1", int(env["TREZOR_UDP_PORT"]), env["WARDD_URL"], token, manual)
    d2 = None
    if (run_dir / "emulator2.ready").exists() and (run_dir / "wardd2.ready").exists():
        _connect_second(token)
    else:
        print("device 2 is not running yet: start_second() starts it")


def _connect_second(token: str) -> None:
    global d2
    env = config["environment"]
    d2 = Device("d2", int(env["TREZOR_UDP_PORT2"]), env["WARDD2_URL"], token, manual)


def start_second() -> None:
    """Start device 2 and its wardd, as the adapter does when the WM goes down."""
    (run_dir / "second.ready").touch()
    if not wait_files(run_dir, ("wardd2.ready", "emulator2.ready")):
        print("device 2 did not start; see wardd2.log and emulator2.log")
        return
    _connect_second((run_dir / "token").read_text().strip())


def wm_down() -> bool:
    """Stop the WARD Manager (as Enter in its terminal does)."""
    return switch_wm(run_dir, down=True)


def wm_up() -> bool:
    return switch_wm(run_dir, down=False)


if __name__ == "__main__":
    os.environ.setdefault("PYTHONPATH", str(Path(__file__).resolve().parents[1] / "python" / "src"))
    main()
