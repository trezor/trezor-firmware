#!/usr/bin/env python3
"""Prototype: screen hashes computed on the device vs. emulator screenshots.

While screen recording is on, the firmware hashes every distinct painted frame
in the byte layout the emulator's PNGs decode to, and reports the hashes plus a
running digest in DebugLinkState. This script drives a small seed-free scenario
(two button-protected pings) and collects what the device reports.

  emulator self-check (starts a headless T3W1 emulator from the local build):
      python core/tools/screen_hashes_proto.py --emulator [--save run.json]
  hardware:
      python core/tools/screen_hashes_proto.py --path <transport> --expect run.json

The emulator run also records PNGs and checks the device hashes against them,
which validates the transform; the hardware run compares against a saved
emulator run, which validates rendering fidelity.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

PULL_DIR: Path | None = None

from PIL import Image  # noqa: E402

from trezorlib import messages  # noqa: E402
from trezorlib.debuglink import TrezorTestContext  # noqa: E402
from trezorlib.transport import get_transport  # noqa: E402


def run_scenario(ctx: TrezorTestContext, record_dir: str) -> tuple[list[str], str]:
    debug = ctx.debug
    hashes: list[str] = []
    digest = [""]

    # Every state query drains the device ring, including the ones trezorlib
    # makes on its own while auto-confirming, so collect at the source.
    orig_state = debug.state

    def state(*args, **kwargs):
        st = orig_state(*args, **kwargs)
        hashes.extend(h.hex() for h in st.screen_hashes)
        if st.screens_digest:
            digest[0] = st.screens_digest.hex()
        return st

    debug.state = state  # type: ignore[method-assign]

    session = ctx.get_seedless_session()

    def ping(message: str) -> None:
        session.call(
            messages.Ping(message=message, button_protection=True),
            expect=messages.Success,
        )

    debug.start_recording(record_dir)
    debug.state()
    ping("one")
    debug.state()
    ping("two")
    debug.state()
    if PULL_DIR is not None:
        screen = debug.read_screen()
        if screen.mode not in ("RGB", "RGBA"):
            print(f"experiment flags: {screen.mode}")
            screen.mode = "RGBA" if len(screen.data) == screen.width * screen.height * 4 else "RGB"
        print(
            f"pulled {screen.width}x{screen.height} {screen.mode}, "
            f"{len(screen.data)} bytes, consistent={screen.consistent}, "
            f"hash {screen.hash.hex()[:16]} (last reported {hashes[-1][:16]})"
        )
        Image.frombytes(screen.mode, (screen.width, screen.height), screen.data).save(
            PULL_DIR / "pulled.png"
        )
    debug.stop_recording()
    return hashes, digest[0]


def hold_menu(ctx: TrezorTestContext) -> None:
    """Open a confirm dialog, hold a touch on the menu button so the pressed
    state stays on screen, and pull it. Diagnoses the transient frame the
    device tests cannot capture."""
    assert PULL_DIR is not None
    debug = ctx.debug
    session = ctx.get_seedless_session()
    debug.start_recording("hold")
    resp = session.call_raw(messages.Ping(message="hold", button_protection=True))
    assert isinstance(resp, messages.ButtonRequest), resp
    session.write(messages.ButtonAck())
    debug.read_layout()

    with debug.hold_touch(debug.screen_buttons.menu()):
        reported = debug.state().screen_hashes
        screen = debug.read_screen()
        print(
            f"held menu press: reported {[h.hex()[:12] for h in reported]}, "
            f"pulled hash {screen.hash.hex()[:12]} consistent={screen.consistent}"
        )
        Image.frombytes(screen.mode, (screen.width, screen.height), screen.data).save(
            PULL_DIR / "menu_pressed.png"
        )
    # the release completes the tap and opens the menu: close it and confirm
    debug.read_layout()
    debug.click(debug.screen_buttons.menu())
    debug.press_yes()
    resp = session.read()
    assert isinstance(resp, messages.Success), resp
    debug.stop_recording()


def png_hashes(record_dir: Path) -> tuple[list[str], str]:
    files = sorted(record_dir.glob("*.png"))
    running = hashlib.sha256()
    per_frame = []
    for f in files:
        data = Image.open(f).tobytes()
        per_frame.append(hashlib.sha256(data).hexdigest())
        running.update(data)
    return per_frame, running.hexdigest()


def report(name: str, got: list[str], got_digest: str, exp: list[str], exp_digest: str) -> bool:
    ok = got == exp and got_digest == exp_digest
    print(f"{name}: {'MATCH' if ok else 'MISMATCH'}")
    width = max(len(got), len(exp))
    for i in range(width):
        g = got[i][:16] if i < len(got) else "-" * 16
        e = exp[i][:16] if i < len(exp) else "-" * 16
        print(f"  frame {i:2d}  device {g}  expected {e}  {'ok' if g == e else '<<'}")
    print(f"  digest    device {got_digest[:16]}  expected {exp_digest[:16]}")
    return ok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--emulator", action="store_true", help="start a headless T3W1 emulator")
    ap.add_argument("--path", help="transport path of a hardware device with debuglink")
    ap.add_argument("--save", type=Path, help="write the collected hashes to this JSON file")
    ap.add_argument("--expect", type=Path, help="compare against hashes from a saved run")
    ap.add_argument("--pull", type=Path, help="also pull the final screen's pixels into this directory")
    ap.add_argument("--hold-menu", action="store_true", help="hold the menu button pressed and pull that screen (needs --pull)")
    args = ap.parse_args()

    global PULL_DIR
    if args.pull:
        args.pull.mkdir(parents=True, exist_ok=True)
        PULL_DIR = args.pull

    record_dir = Path(tempfile.mkdtemp(prefix="screen-hashes-"))
    ok = True

    if args.hold_menu:
        if PULL_DIR is None:
            ap.error("--hold-menu needs --pull")
        if args.emulator:
            from tests.emulators import (
                TROPIC_MODEL_CURRENT_CONFIG,
                EmulatorWrapper,
                get_tropic_model_port,
            )
            from trezorlib._internal.emulator import TropicModel

            port = get_tropic_model_port(0)
            with tempfile.TemporaryDirectory(prefix="tropic-model-") as tropic_dir:
                with TropicModel(
                    profile_dir=tropic_dir, configfile=TROPIC_MODEL_CURRENT_CONFIG, port=port
                ) as tropic:
                    tropic.start()
                    with EmulatorWrapper("T3W1", tropic_model_port=port) as emu:
                        hold_menu(emu.client)
        else:
            if not args.path:
                ap.error("--path or --emulator is required")
            hold_menu(TrezorTestContext(get_transport(args.path)))
        return 0

    if args.emulator:
        from tests.emulators import (
            TROPIC_MODEL_CURRENT_CONFIG,
            EmulatorWrapper,
            get_tropic_model_port,
        )
        from trezorlib._internal.emulator import TropicModel

        port = get_tropic_model_port(0)
        with tempfile.TemporaryDirectory(prefix="tropic-model-") as tropic_dir:
            with TropicModel(
                profile_dir=tropic_dir, configfile=TROPIC_MODEL_CURRENT_CONFIG, port=port
            ) as tropic:
                tropic.start()
                with EmulatorWrapper("T3W1", tropic_model_port=port) as emu:
                    hashes, digest = run_scenario(emu.client, str(record_dir))
        exp, exp_digest = png_hashes(record_dir)
        ok &= report("device vs emulator PNGs", hashes, digest, exp, exp_digest)
    else:
        if not args.path:
            ap.error("--path or --emulator is required")
        ctx = TrezorTestContext(get_transport(args.path))
        hashes, digest = run_scenario(ctx, str(record_dir))
        print(f"device reported {len(hashes)} frames, digest {digest[:16]}")

    if args.expect:
        saved = json.loads(args.expect.read_text())
        ok &= report("device vs saved run", hashes, digest, saved["hashes"], saved["digest"])

    if args.save:
        args.save.write_text(json.dumps({"hashes": hashes, "digest": digest}, indent=1))
        print(f"saved to {args.save}")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
