# WARD Manager development service

The encrypted WARD Manager is a REST service in `tools/ward_manager.py`.
It stores each ward's authoritative counter, root, root MAC, head nonce and
timestamp in SQLite, together with append-only signed transition history. It signs
freshness attestations and accepted commits with Ed25519. Its endpoints match
`HttpWm` in trezor-suite's `packages/wardd/src/wm.ts`.

## Selected architecture

The WARD Manager is root-aware. It verifies wallet-signed transitions, compares
their predecessor counter, root and head nonce against its current head, and
atomically appends each accepted transition while advancing that head. History
returned by the manager contains accepted transitions; locally persisted candidate
transitions can also contain rejected branches. The manager sees roots and
transition metadata, but receives no plaintext records or device secret keys.

Chain discovery runs **backward**, starting at the WM-selected head and following
predecessors toward the device's trusted `(counter, root)` anchor. The host also
reconstructs encrypted state from genesis and checks every resulting root.

The `WARDVerifyChain.links` wire ordering is **oldest first**, from the device
anchor toward the WM head. After discovering the lineage backward, the host
reverses the required suffix for transmission. The device verifies every link's
contiguity and wallet authorization, checks the terminal state against the fresh
WM attestation, and adopts the head only after the entire chain passes. Host
discovery direction and device verification ordering are distinct; successful
verification of a partial prefix does not authorize partial head adoption.

These choices supersede the export's root-private WM variant and its alternative
newest-first device-verification example. They match the current host/device
implementation; this decision does not change the protobuf ordering.

## Run it

From the firmware checkout, with `nix-shell` active and `uv sync` completed:

```sh
uv run python tools/ward_manager.py --debug-key
```

It listens on `http://127.0.0.1:21330` and stores checkpoints in
`~/.trezor-ward-manager/heads.sqlite3`. Use `--db /path/to/heads.sqlite3` to choose
another database, or `--memory` for a fresh, temporary manager. Stop with Ctrl+C.

Set `WARD_MANAGER_PORT` to choose a port, or pass `--port` to override it.
`tools/ward_stack.py` opens all four components in separate Nix-shell terminals
and passes the same port configuration to each. `WARDD_PORT` selects wardd's
WebSocket port, and `TREZOR_UDP_PORT` is shared by the emulator and HWI.

`tools/ward_stack.py --gui --delays` enables a one-second pause at forwarding
boundaries across the stack. For the manager alone, use `--delays` or
`WARD_DELAYS=1` to pause before every HTTP response. The wait is logged, and
response timing includes the injected delay.

Select a signing key explicitly: `--debug-key` uses the well-known key accepted
by debug firmware; `--key-file /path/to/seed.hex` reads a 32-byte hex seed. The
database records the public key and refuses to reopen with a different key.
The seed is never included in HTTP responses or logs.

For a temporary development setup, run the manager with `--memory` and start
wardd in the Suite checkout in a second terminal:

```sh
yarn workspace @trezor/wardd start --memory --wm-url http://127.0.0.1:21330
```

Keep the manager's history and wardd's encrypted replica together between runs.
Sync reads the manager's current head and catches up using complete encrypted
history. If the replica lacks that history, reconstruction fails until it is
restored. The manager does not reset its authoritative head to match a missing
replica.

## API

POST requests use `Content-Type: application/json`. `wardId`, `nonce`, and
nonempty `mac` values are 32 bytes encoded as hex. Counters are unsigned 32-bit
integers. Roots use an empty string for the empty tree. Only genesis at counter
zero has no root MAC; positive-counter empty states require a real wallet MAC.

| Method | Path             | Request                                                  | Response                                        |
| ------ | ---------------- | -------------------------------------------------------- | ----------------------------------------------- |
| GET    | `/health`        | —                                                        | `status`, signing `publicKey`                   |
| GET    | `/ward/{wardId}` | — | `wardId`, current head |
| GET    | `/ward/{wardId}/history` | — | `wardId`, current head, ordered `transitions` |
| POST   | `/ward/attest` | `wardId`, `nonce`; optional expected `counter` and `mac` | Current head and `signature` |
| POST   | `/ward/commit` | `wardId`, `fromCounter`, `fromRoot`, `counter`, `root`, `mac`, `authCommit`, `signature`, `kind`, `headNonce` | Accepted head and `signature` |

A head contains `counter`, `root`, optional `mac`, `headNonce` and `timestamp`.
`wardId` is the wallet's K_sig Ed25519 public key. History is ordered by increasing
counter. Transition signatures bind both endpoints, kind, resulting MAC, AuthCommit
and the predecessor head nonce.

A ward starts at counter 0 with an empty tree. Attestations always sign the
stored head. If an expected checkpoint is supplied, it must match; an invented
or stale checkpoint receives HTTP 409 with the current head and no signature.

Commits must advance the counter by exactly one. The check and update happen in
one SQLite transaction, before returning the signature. Two different writers
at the same counter cannot both win. Retrying the identical current checkpoint
returns the same signature without advancing again. A conflict returns
`{"error":"checkpoint_conflict",...}` with the current head; `mac` is omitted
only at genesis. Malformed requests receive HTTP 400, invalid wallet signatures
receive HTTP 403, and storage failures receive HTTP 503 without a signature.

The signing domains match the encrypted firmware: `WARD ATTEST v2` (version 2,
nonce, ward ID, counter, MAC, timestamp, head nonce), `WARD WM TRANSITION v2`
(wallet authorization), and `WARD FINAL v1` (ward ID, counter, MAC).
The manager never receives plaintext labels, addresses, leaves, or device keys.

The manager verifies the wallet's transition signature before advancing state.
It binds to localhost by default. This authorization does not provide transport
encryption or authenticate unrelated HTTP operations.

## Live request and response log

Console output is immediate, one JSON event per line. Every request, parsed
request body, and response share an ID, also returned as `X-Request-ID`.
Responses include status, body, and elapsed milliseconds. Conflicts and invalid
requests appear in the same stream. Unknown request fields and invalid JSON
are rejected before their bodies are logged.

In a second terminal, try:

```sh
curl -s http://127.0.0.1:21330/health
curl -s http://127.0.0.1:21330/ward/attest \
  -H 'Content-Type: application/json' \
  -d '{"wardId":"cdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcd","nonce":"abababababababababababababababababababababababababababababababab"}'
```

To retain the stream, launch with `2>&1 | tee /tmp/ward-manager.log`.

## Verification

```sh
uv run pytest tests/test_ward_manager.py
```

The real-daemon device tests run with both this HTTP manager and the existing
in-process mock. Set `WARDD_SUITE_DIR` to the encrypted Suite checkout and use
a debuglink emulator on an isolated port:

```sh
WARDD_SUITE_DIR=/path/to/trezor-suite uv run python core/emu.py \
  --executable core/build/artifacts/T3T1/firmware-emu -h -t -P 37632 -q \
  -c uv run pytest tests/device_tests/misc/test_ward_relay.py
```
