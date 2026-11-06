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
from jadepy.ward import WardAdapter  # a re-export of ward_relay.WardAdapter

with WardAdapter(token=token, url="ws://127.0.0.1:21329") as adapter:
    with adapter.session(existing_trezor_session) as ward:
        ward.call("sync", {})
        # Existing session.call(...) calls also answer nested WARD proof requests.
```

The shared adapter handles protobuf conversion, proof callbacks and forwarding.
It restores the previous proof callback on exit and never opens or closes the
borrowed Trezor session. Jade's integration is only an import and re-export.

Liana's optional import is enabled with:

```sh
cd ../wallets/liana
cargo check -p liana-gui --features ward
```

Liana also only re-exports the shared adapter and its session helpers:

```rust,ignore
use liana_gui::ward::Hwi;
let mut ward = Hwi::new(&mut adapter, &mut existing_trezor_session);
ward.call("sync", serde_json::json!({}))?;
ward.forward("GetAddress", request)?;
```

The caller's session implements the shared `DeviceSession` transport interface;
it retains its existing protobuf I/O, PIN and confirmation handling. All WARD
conversation steps and proof responses live in `ward-relay`, with no wallet-local
forwarding implementation. This interface does not implement a native Trezor
transport for Liana.

The local path
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

Add `--full_log` (alias `--full-log`) to merge all components' stdout and
stderr into one file while keeping the separate logs and terminal output:

```sh
./tools/ward_stack.py --gui --delays --full_log
```

Run two devices with the same SLIP-14 test seed against one wardd/Evolu replica
and one HTTP manager:

```sh
./tools/ward_stack.py --devices 2 --model T3T1 --headless --once --full-log
```

This runs real-device synchronization, per-device offline queues, reconnect
publication, same-entry collisions, signed rollback and attestation replay tests.
The launcher supports up to eight devices with distinct profiles and UDP
port blocks. T3W1 devices also get separate Tropic model TCP ports.
Multi-device mode runs separately from `--long`, `--extra_long` and `--adversarial`.
Results are saved as `multi-device-results.json` in the printed run directory.
Omit `--headless --once` to keep separate terminals open for interactive reruns
and manual pause controls.

With `--devices 3`, the driver additionally runs three publication races:

```sh
./tools/ward_stack.py --devices 3 --model T3T1 --headless --once --full-log
./tools/ward_stack.py --devices 3 --model T3W1 --headless --once --full-log
```

Device-1 queues A and B without advancing WM; device-2 prepares its own A,
and device-3 prepares C from the same trusted head. Publication is paused after
receiving the real device candidate and before wardd sends it to WM. The driver
cross-delivers genuine WM confirmations in both directions, retargets the MAC,
substitutes wallet signatures, and replays delayed confirmations. Each rejection
must preserve the recipient's counter, root and complete pending queue.

A third round submits all three signed successors concurrently to the real HTTP
manager. Exactly one may be accepted; the others must return conflicts. All
queued intents are then published against fresh state, including B, and all three
devices must converge with empty queues. Exact publication retries must not add
history records. Timestamped `race.*` events and named results are included in the
HWI and combined logs. These checks bind confirmations to a particular authorized
transition; devices sharing a seed intentionally share wallet signing authority.

The full multi-device run also tests rollback after deleting the Evolu journal
row containing the latest published leaf. Run this case alone with:

```sh
./tools/ward_stack.py --devices 3 --model T3T1 --scenario recovery --headless --once --full-log
```

The debug channel's `DROP_TRANSITION` fault removes the selected journal row;
`RECONSTRUCT` starts a fresh walk from the WM head backward to genesis, replays
forward, and rebuilds the trie from available leaf data. It reports the last
verified prefix without treating it as the authoritative head. Ordinary sync
must refuse the damaged head. The authenticated transition metadata remains in WM.

Recovery uses `sync` with `recover: true` and the cached confirmation in
`cachedConfirmation: { counter, mac, wm_signature }`. The device verifies that
receipt before establishing the stuck head. It then requires a separate user
confirmation for the revert. Cancellation must leave WM unchanged; successful
recovery restores the complete immediate predecessor at a higher counter.
Deeper data gaps fail closed. Reverted leaf data can remain unavailable: wardd
uses WM's authenticated commit/revert history to rebuild the restored state,
and another device verifies both links before catching up. The test also checks
that new writes work afterward. Fault injection is available only through an
explicitly enabled, token-protected debug listener.

wardd exposes an opt-in, separate loopback TCP debug channel (`--debug-port`,
`WARDD_DEBUG_PORT`; the launcher defaults to 21331). Every newline-delimited JSON
request requires the pairing token, a `deviceId` and `command: "PAUSE"` or
`command: "CONTINUE"`. The response acknowledges the selected device's state.
The channel is disabled when wardd is started without a debug port. Debug controls
are separate from the device's protobuf transport.

Use the run directory printed by the launcher to control one device:

```sh
./tools/ward_stack.py --run-dir /path/to/ward-stack-run --pause device-1
./tools/ward_stack.py --run-dir /path/to/ward-stack-run --continue device-1
```

`PAUSE` prevents subsequent WM requests for that device; other devices keep
working. It does not stop the emulator or the local Evolu store. Host callers bind
their endpoint by passing `debugDeviceId` in their conversation parameters; the
multi-device driver does this automatically. Ordinary single-device callers use
`device-1`. `CONTINUE` restores WM access; the next sync drains the device's queue
against fresh proofs. A publication conflict preserves the queued intent for retry.
When two authorized intents address the same entry, they are applied in publication
order with increasing counters; unrelated entries remain intact. Pausing does not
revoke WM requests that were already in flight.

To run the integration test through pytest:

```sh
WARD_STACK_INTEGRATION=1 pytest tests/test_ward_multidevice.py -v
```

Add `--long` to write ten distinct demo entries, then verify all ten by lookup:

```sh
./tools/ward_stack.py --gui --long --full_log
```

`--long` also works directly on `examples/trezor_hwi.py`. It uses numbered
addresses and labels and fails on a commit conflict, cache error, or incorrect
lookup result. Combine it with `--delays` to watch every forwarding step; ten
complete write/lookup rounds take substantially longer with pacing enabled.

Use `--extra_long` (alias `--extra-long`) for bounded operation-combination
coverage through depth 10. It takes precedence over `--long` and requires a
fresh wallet and manager. The model uses two keys, each absent, empty-valued or
labelled, with nine operations: sync and lookup/write-empty/write-label/delete
for each key. It exercises insertion, replacement, repeated writes, deletion,
absent deletion, reinsertion, and membership/non-membership proofs.

Equivalent logical states at the same depth share suffix exploration. This covers
all 702 reachable state/operation edges, rather than enumerating billions of
literal histories or all possible byte values. The longest explored operation
sequence is 10; the real counter continues increasing during authenticated
restoration writes between branches. Every operation checks the counter; writes
also check both keys' device proof verdicts, and label writes check the actual
Trezor display. Restoration operations are logged separately. A successful run
ends with `extra_long.complete` and matching `coveredEdges`/`expectedEdges`.

Run against either supported test model:

```sh
./tools/ward_stack.py --model T3T1 --extra_long --headless --once --full_log
./tools/ward_stack.py --model T3W1 --extra_long --headless --once --full_log
```

`--model` selects the emulator artifact and the model built by `--prepare`.
T3W1 uses the Tropic model server. The launcher assigns an independent port to
each instance; standalone emu.py defaults to 28992 unless --tropic-emulator-port
is supplied.
This tests the current daemon operations; batch/revert/recovery workflows not
exposed by wardd are outside this model's coverage. Expect a substantially longer
run than `--long`, especially with `--delays`.

Use `--adversarial` for attack/rejection tests, separately from the long modes:

```sh
./tools/ward_stack.py --model T3T1 --adversarial --headless --once --full_log
./tools/ward_stack.py --model T3W1 --adversarial --headless --once --full_log
```

The mode runs on the launcher's disposable emulator and wipes it between device
tests. It checks modified/replayed attestations, signed timestamp/counter
regression, positive-counter empty heads, same-counter root substitution,
incomplete/reordered/forged authorization chains, invalid terminal root MACs,
WM confirmations without device candidates, malformed pushed proofs, altered
encrypted leaf parts, wrong namespaces and relabelled non-membership proofs.
Negative device tests check that the trusted head remains unchanged and honest
operations still work. Proof-specific tests use debug-only root setup; the normal
authenticated write path is covered separately by the long modes.

Manager tests cover transition signature operands, CAS races, generation nonces,
immutable history and SQLite write failure. Host tests cover transition storage
failure before WM publication, reconstruction/lineage checks, immutable records,
and rejection of forged cached metadata. Rust adapter protocol tests check the
single-session forwarding boundary and rejection of non-WARD device commands.

Each group must finish successfully with executed tests. Skipped tests, failures
and timeouts fail the mode. XML/JSON reports and `summary.json` are saved under
the run's `adversarial/` directory. Console events include timestamps and group
results. This is evidence for these specific attacks, not a proof of protocol
security; unimplemented recovery/backup workflows and remote availability remain
outside its claims.

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

## TypeScript / Node.js adapter and Connect

`node/` exposes the same Rust `Client` through a Node-API addon. Its asynchronous
methods run blocking WebSocket work on Node's worker pool. The HWI still owns the
only Trezor channel. Rust's timestamped relay logs go to stderr as in Python.

Build the native addon on the machine that will run it:

```sh
nix-shell --run "node rust/ward-relay/node/build.mjs"
```

Add the resulting local `rust/ward-relay/node` package to the application's
dependencies as `@trezor/ward-relay`. It contains JavaScript and TypeScript
declarations. The `.node` artifact is specific to the build OS and architecture;
prebuilt binaries are not distributed.

Connect's separate `ward` entry point adapts it to the existing `wardd` setting:

```ts
import TrezorConnect from '@trezor/connect';
import { RustWardRelay } from '@trezor/connect/lib/ward.js';
import { WardAdapter } from '@trezor/ward-relay';

await TrezorConnect.init({
  ...existingSettings,
  wardd: new RustWardRelay({
    connect: () => WardAdapter.connect({ url: 'ws://127.0.0.1:21329', token }),
  }),
});
await TrezorConnect.wardInit({});
```

The bridge forwards calls and mid-call proof requests using Connect's current
device session, maps relay errors, and awaits native cleanup. A fresh adapter
connection is opened per Connect WARD operation. This is an opt-in Node/Electron
path to a running wardd. The in-process `new Wardd(...)` option above continues
to work without IPC; it does not load the native addon. Browser and React Native
bindings are not provided by this Node-API package.

Outside Connect, use `await adapter.call(method, params, deviceCallback)`, or
`start`/`resume` for explicit protobuf handoff. `answerWardRequest` returns the
named `WARDProofAck` for a proof pull. Always `await adapter.close()` afterward.
