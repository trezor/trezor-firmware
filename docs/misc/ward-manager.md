# WARD Manager development service

The encrypted WARD Manager is a REST service in `tools/ward_manager.py`.
It stores each ward's authoritative counter and root MAC in SQLite and signs
freshness attestations and accepted commits with Ed25519. Its endpoints match
`HttpWm` in trezor-suite's `packages/wardd/src/wm.ts`.

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

Keep the manager's checkpoints and wardd's replica together between runs. If a
persistent manager has advanced while a new in-memory wardd starts at genesis,
sync returns HTTP 409 until the replica is restored. The manager does not reset
its authoritative head to match a missing replica.

## API

POST requests use `Content-Type: application/json`. `wardId`, `nonce`, and
nonempty `mac` values are 32 bytes encoded as hex. Counters are unsigned 32-bit
integers. A missing, null, or all-zero MAC denotes an empty tree.

| Method | Path             | Request                                                  | Response                                        |
| ------ | ---------------- | -------------------------------------------------------- | ----------------------------------------------- |
| GET    | `/health`        | —                                                        | `status`, signing `publicKey`                   |
| GET    | `/ward/{wardId}` | —                                                        | `wardId`, `counter`, optional `mac`             |
| POST   | `/ward/attest`   | `wardId`, `nonce`; optional expected `counter` and `mac` | Stored `counter`, optional `mac`, `signature`   |
| POST   | `/ward/commit`   | `wardId`, next `counter`, optional `mac`                 | Accepted `counter`, optional `mac`, `signature` |

A ward starts at counter 0 with an empty tree. Attestations always sign the
stored head. If an expected checkpoint is supplied, it must match; an invented
or stale checkpoint receives HTTP 409 with the current head and no signature.

Commits must advance the counter by exactly one. The check and update happen in
one SQLite transaction, before returning the signature. Two different writers
at the same counter cannot both win. Retrying the identical current checkpoint
returns the same signature without advancing again. A conflict returns
`{"error":"checkpoint_conflict","counter":...,"mac":...}`; `mac` is omitted
for an empty tree. Invalid requests receive HTTP 400, and storage failures
receive HTTP 503 without a signature.

The signing domains match the encrypted firmware: `WARD ATTEST v1` (version 1,
nonce, ward ID, counter, MAC) and `WARD FINAL v1` (ward ID, counter, MAC).
The manager never receives plaintext labels, addresses, leaves, or device keys.

This development service does not authenticate callers or verify a device's
transition signature: the existing commit interface supplies only the ward ID,
counter and MAC. It binds to localhost by default. A custom signing key alone
does not add caller authorization.

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
