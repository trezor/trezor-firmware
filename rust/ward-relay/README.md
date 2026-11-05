# Shared WARD adapter

This crate is the common Rust relay engine used by Liana (`liana_gui::ward`,
feature `ward`) and Jade's Python host library (`jadepy.ward`). The Python
package wraps this same engine through PyO3; it does not implement another relay.

The HWI owns the single Trezor channel, session, protobuf encoding, PINs and
confirmations. The adapter opens only a WebSocket to wardd and has no USB, HID,
serial or device-UDP transport. It never signs for the WARD Manager or builds
Merkle proofs. Jade firmware is unchanged.

## Handoff

The step API is identical in Rust and Python:

1. `start("sync" | "lookup" | "update" | "status", params)` returns either
   `{"deviceCall":{"name":...,"message":...}}` or a final `result`/`error`.
2. The HWI puts the named protobuf on its existing Trezor session, then passes
   the named response to `resume(name, message)`. Repeat until complete.
3. For a `WARDProofRequest` received during ordinary HWI operations such as
   address display, `answer_ward_request` obtains `WARDProofAck` from wardd;
   the HWI forwards that protobuf back to the same device channel.

`resume` also handles a proof pull inside an active WARD conversation without
completing the enclosing call. In Python, `answer_ward_request` returns the
named message directly; the Rust return value contains it under `deviceCall`.
Python also provides `call(method, params, device_call)` to run the step loop
with an HWI-owned callback. Bodies are JSON protobufs with bytes encoded as hex.

The engine allows only encrypted-protocol WARD commands from wardd. A non-WARD
device command is rejected before it reaches the HWI. Calls on a single adapter
are sequential. Use the hardware-wallet worker rather than blocking a GUI loop.

Timestamped JSON logs go to stderr by default, with operation IDs and timings.
They omit tokens, keys, protobuf bodies, addresses and labels. `set_logging(false)`
disables them. Both host bindings use the same logger.

## Build and import

From the firmware checkout's Nix environment:

```sh
cargo test --manifest-path rust/ward-relay/Cargo.toml
# Clear Nix's other Python's sysconfig path for this native-extension build.
env -u PYTHONPATH uv pip install --python .venv/bin/python ./rust/ward-relay
env -u PYTHONPATH uv pip install --python .venv/bin/python -e ../wallets/Jade
```

Python:

```python
from jadepy.ward import WardAdapter  # or: from ward_relay import WardAdapter

with WardAdapter(token=token, url="ws://127.0.0.1:21329") as adapter:
    step = adapter.start("sync", {})
    # The HWI forwards each step on its existing session and calls resume().
```

Liana's optional import is enabled with:

```sh
cd ../wallets/liana
cargo check -p liana-gui --features ward
```

It exposes `liana_gui::ward::WardAdapter` with the same step API. The local path
dependency assumes `trezor-firmware` and `wallets` are siblings in this checkout.
This provides the handoff library; it does not add Trezor enumeration to async-hwi
or route ordinary Jade CBOR commands into a Trezor session.

## Run all parts

The single-command launcher opens four terminal windows, each in its own
`nix-shell`, and shares ports and the token path automatically:

```sh
./tools/ward_stack.py
```

Add `--gui` (alias `--emulator-gui`) to show the emulator display:

```sh
./tools/ward_stack.py --gui
```

Use `--delays` to pause one second before forwarding calls and responses, so
the sequence can be followed across the terminals:

```sh
./tools/ward_stack.py --gui --delays
```

Add `--full_log` (alias `--full-log`) to merge all four components' stdout and
stderr into one file while keeping the separate logs and terminal output:

```sh
./tools/ward_stack.py --gui --delays --full_log
```

The launcher prints the combined file path, `/tmp/ward-stack-*/full.log`.
Each line has a UTC collection timestamp and a source label (`[manager]`,
`[wardd]`, `[emulator]`, or `[hwi]`), including lines from multiline messages.
Use `tail -f /tmp/ward-stack-<run>/full.log` to follow the combined sequence.
The timestamps reflect when output is collected; component timestamps remain
in the message. Nix shell setup diagnostics remain in the launching terminals.

Each paused hop logs `forward.delay` before waiting. This is disabled by default;
the launcher exports `WARD_DELAYS=1` to enable pacing in the HWI, wardd and WM.
A complete delayed write/lookup takes longer, so the automatic confirmation wait
is extended in this mode.

The emulator is headless by default. `--headless` controls the terminal windows
separately; `--headless --gui` shows only the emulator GUI and keeps service
output in the launching terminal. GUI mode requires a graphical display.

Configure the ports through environment variables (CLI flags take precedence):

```sh
WARD_MANAGER_PORT=38330 WARDD_PORT=38329 TREZOR_UDP_PORT=38344 \
  ./tools/ward_stack.py
```

The manager accepts `WARD_MANAGER_PORT` or `--port`; wardd accepts `WARDD_PORT`
and uses `WARD_MANAGER_URL` or `WARD_MANAGER_PORT`. The emulator and HWI both
use `TREZOR_UDP_PORT`. The launcher exports these values into all four shells.

Use `--prepare` to install the Python bindings and build the emulator first,
or `--suite /path/to/trezor-suite` to select another Suite checkout. GNOME
Terminal, Konsole and xterm are detected automatically. The launcher waits for
services and device initialization before starting the HWI.

In the HWI window, Enter repeats the demo and `q` stops the stack. Ctrl+C in the
launcher also stops all four components. A stop command, an `env.sh` file, and
logs/state are printed under a fresh `/tmp/ward-stack-*` directory for each run.
`--headless --once` runs the same four Nix shells without windows and stops
after one successful write/lookup; `--once` also works with graphical terminals.

For manual startup instead:

Use separate terminals. In the firmware checkout, first build the emulator:

```sh
uv run xtask build firmware --emulator -m T3T1 -p test-live
```

**Terminal 1 — WARD Manager, with timestamped request/response logs:**

```sh
cd /home/psusil/GitHub_authdb/trezor-firmware
uv run --no-sync python tools/ward_manager.py --debug-key --memory
```

**Terminal 2 — wardd with Evolu and the REST manager:**

```sh
cd /home/psusil/GitHub_authdb/trezor-suite-petrsusil/.worktrees/ward-poc-encrypted
WARD_DATA_DIR=$(mktemp -d /tmp/ward-demo.XXXXXX)
echo "Token file for terminal 4: $WARD_DATA_DIR/token"
yarn workspace @trezor/wardd start --data-dir "$WARD_DATA_DIR" \
  --wm-url http://127.0.0.1:21330 --verbose
```

Omit `--memory` on wardd to exercise Evolu. Its console shows UTC timestamps,
Evolu lookup hits/misses and row counts, and WM HTTP calls, statuses and timings.
`--verbose` additionally shows the device conversation and proof diagnostics.

The verbose trie trace includes the following events:

- `wm.head`: the counter and MAC actually returned by the REST manager.
- `trie.head`: the replica's root hash and checkpoint. The WM does not return the
  root hash; Trezor checks its binding to the WM-attested MAC.
- `trie.lineage`, `trie.transition`, `trie.genesis`: the selected history from the
  exact `(counter, root)` checkpoint back to counter 0, including encrypted leaves.
- `trie.replay.step`: genesis-to-head replay with a computed root check per batch.
- `trie.entry`: every final encrypted leaf used to reconstruct the trie, including
  its opaque entry key and both encoded parts, without host labels or addresses.
- `trie.rebuild.complete`: computed root, expected root, and whether they match.
- `proof.outgoing`: the complete outgoing `WARDProofAck` JSON protobuf, including
  every path element, witness, and any leaf content/identity sent to Trezor.

The production proof path now uses this verified transition replay. Missing,
ambiguous or corrupted lineage fails instead of producing a proof from a partial
snapshot. Providers without transition support are explicitly logged as a
current-entry snapshot fallback. Repeated roots and deletion back to empty are
resolved by counter as well as root; an empty checkpoint at a positive counter
does not end the walk early.

**Terminal 3 — one headless Trezor emulator:**

```sh
cd /home/psusil/GitHub_authdb/trezor-firmware
uv run --no-sync python core/emu.py --executable core/build/artifacts/T3T1/firmware-emu \
  -h -t -s -P 37744 -q
```

**Terminal 4 — development HWI using the shared adapter:**

```sh
cd /home/psusil/GitHub_authdb/trezor-firmware
# Substitute the token-file path printed by terminal 2.
uv run --no-sync python rust/ward-relay/examples/trezor_hwi.py \
  --path udp:127.0.0.1:37744 --token-file /tmp/ward-demo.XXXXXX/token \
  --jade-host --label "WARD demo"
```

The example confirms the write on the debug emulator and looks the entry up.
Omit `--label` for a read, or omit `--jade-host` to import the Python package
directly. Only the example HWI owns device I/O. Ctrl+C stops each foreground
service; use a fresh manager and Evolu data directory together for a new demo.

Connect does not need the WebSocket adapter. It can import the same implementation
and give all components the same logger:

```ts
import {
  Wardd,
  EvoluWardStorage,
  HttpWm,
  createConsoleLog,
} from "@trezor/wardd";

const log = createConsoleLog();
const storage = await EvoluWardStorage.open({ dataDir, log });
const wm = new HttpWm("http://127.0.0.1:21330", log);
const wardd = new Wardd({ storage, wm, log });
await TrezorConnect.init({ ...existingSettings, wardd });
```

This uses the same service, storage and WM code in-process, with the same logs.
