# WARD service interface and wallet fallback

Universal emulator builds on `petrsusil/ward-service-channel` include the service
interface automatically; no emulator parameter or WARD build flag is needed.
Hardware builds opt in with `--enable-ward-service-channel`, which also includes
WARD. This adds a dedicated codec-v1 USB interface on every model,
including THP wallets; it does not add a THP channel or borrow wallet buffers.
Bitcoin-only builds reject this option. Split kernel/firmware hardware builds
must enable it in both projects.

The interface is appended after existing USB interfaces. Its identity is vendor
class `FF`, subclass `57`, protocol `01`; hosts discover it by descriptor rather
than by interface index. The emulator uses the wallet UDP port plus seven.
Windows receives a WinUSB-compatible descriptor for the extra interface.

## Routing and conversations

A daemon announces itself with `WARDServiceOpen(protocol_version=1)`. The device
then initiates every application exchange. The listener never dispatches host
messages as wallet workflows. It accepts only the response types expected by the
current sync, proof, listing, or publication exchange.

Each wallet workflow selects its route once. A bound service handles backend
traffic; without a binding, the existing wallet protocol handles it. Connecting a
service during a workflow does not change the selected route. A service error
fails the current operation; it does not retry a partially completed mutation on
the wallet interface. Graceful daemon close releases the binding, enabling wallet
fallback on the next operation. An abrupt disappearance is detected by the next
RPC's timeout. The binding survives event-loop/session restarts; it contains no
wallet keys or authenticated head. Every service workflow synchronizes in its
current wallet context.

The service uses the existing signed attestation, chain, proof and finalization
handlers. Sync starts with a device-produced `WARDSyncAck`, followed by attestation
and chain verification/reconciliation. Publication starts with a device-produced
batch/revert candidate and completes only after the existing WM confirmation
handler verifies and installs it. `WARDServiceDone` closes the conversation; it
cannot authorize adoption. Single-edit publication uses a one-leaf batch.

Service synchronization requires a reconstructable replica. Recovery from missing
replica data remains available through the wallet protocol: close the service
binding before starting that recovery flow.

The matching Connect/wardd code on `petrsusil/ward-service-channel` recognizes
`WARDSyncAck.service_bound`, requests `WARDServiceSync`, and honors the
`service_applied` candidate flag. The wallet receives the result without backend
leaves. A separate service queue allows a wallet call to wait on a reverse RPC to
the same wardd process without holding its backend queue lock.

## Buffer sizing and streaming

The service codec owns **one 64-byte report buffer**, reused for sending and
receiving by one listener task. The USB interface requires 64-byte reports, so
this is its minimum report-buffer size. Fields and varints may cross report
boundaries; no proof element needs to fit in one report. USB's native interface
also has its own 64-byte receive buffer. Neither allocation is shared with the
wallet. The binding record occupies five payload bytes plus the cache's presence
byte.

A trie proof has at most 256 hops: split bits must strictly increase from root to
leaf within a 256-bit key. Each hop is 34 bytes. Consequently:

| Representation | Size |
| --- | ---: |
| Raw maximum-depth path | 256 × 34 = 8,704 bytes |
| Protobuf repeated path, before leaf data | 256 × (1-byte tag + 1-byte length + 34) = 9,216 bytes |
| Tested 256-hop membership with a small encrypted leaf | 9,433 bytes |
| Private wire report buffer | 64 bytes |

Incoming protobuf is decoded field by field directly from reports. Unknown fields
are discarded incrementally. There is no allocation for a complete encoded proof
or message. Outgoing protobuf is encoded into report-sized windows. The native
window encoder scans the message for each window, trading CPU work for memory;
large outputs therefore cost additional traversal work.

The existing trie verifier still retains the decoded proof path. Leaf values,
nested messages and batch candidates retain their application data. Their memory
cost scales with proof depth and leaf size, independently of the 64-byte wire
buffer. On the 64-bit T3T1 emulator, the codec object including its report allocated
352 bytes; this is not the total decoded-proof cost or a hardware RAM measurement.

The parser bounds a message to 65,536 bytes, a bytes/string field to 8,192 bytes,
a repeated field to 256 values, and nesting to 16 messages. These are independent
of the wire buffer. Continuation reports have a 500 ms gap limit, and the whole
RPC has a 30-second deadline. Malformed or oversized input terminates the service
exchange without advancing the wallet head. Host-side encoding can still use its
ordinary full-message buffer.

## Run the components

Use matching firmware and Suite checkouts on `petrsusil/ward-service-channel`.
From the firmware checkout, with Nix and uv dependencies active:

```sh
uv run xtask build firmware -e -m T3W1 -p test-live
uv run python core/emu.py --executable core/build/artifacts/T3W1/firmware-emu \
    -h -t -P 37904
```

In separate terminals, start the development manager and wardd:

```sh
# Firmware checkout
uv run python tools/ward_manager.py --debug-key --memory

# Matching Suite checkout: connect wardd directly to the emulator service interface.
yarn workspace @trezor/wardd start --memory --data-dir /tmp/ward-service-demo \
    --wm-url http://127.0.0.1:21330 --service-channel udp:127.0.0.1:37904
```

For hardware use `--service-channel usb` (one attached device) or
`--service-channel usb:SERIAL`. wardd claims only the dedicated service interface.
Without this option the daemon retains its existing wallet relay behavior.
With it, wardd connects directly to the service interface and opens no WebSocket
adapter relay port. Add `--wallet-relay` explicitly to expose that relay as well.
Wallet callers can use `trezorlib.ward_wallet.WardWalletClient` to issue ordinary
wallet requests without connecting to wardd or supplying backend messages.

The multi-terminal launcher selects the direct connection with one runtime flag:

```sh
uv run python tools/ward_stack.py --suite /path/to/matching/trezor-suite \
    --model T3W1 --service-channel --extra-long --full-log --once
```

The launcher waits for the emulator before wardd binds, then starts the wallet
driver. Shutdown releases the binding before stopping the emulator. This mode
currently supports one device; multi-device recovery uses the wallet relay.
The emulator UI is visible by default. Confirmations are approved automatically
after two seconds; set `--confirm-delay SECONDS` to change this. Use `--headless`
explicitly to hide the emulator and run all components without terminal windows.

Alternatively, start wardd without `--service-channel` and attach the independent
backend from the firmware checkout using wardd's generated token:

```sh
uv run python tools/ward_service.py --path udp:127.0.0.1:37904 \
    --token-file /tmp/ward-service-demo/token
```

The wallet app continues using its ordinary transport. The service connection owns
only the second interface. Stop wardd (or the external adapter) cleanly to release
its binding and use wallet fallback. Keep the manager history and encrypted replica
together.

## Verification

`core/tests/test_trezor.wire.ward_streaming.py` exercises maximum-depth proofs,
report-boundary splits, bounded output encoding, malformed lengths, duplicate
fields, repetition limits and the private allocation size. Cache tests verify
that session resets preserve only the transport binding, not WARD trust state.

The device integration test uses a real wardd with both mock and HTTP managers,
over both service and wallet routes. It asserts that no backend proof crosses
the wallet while the service is selected, and exercises reads, writes, deletion,
address-label display, proof tampering and graceful fallback:

```sh
WARDD_SUITE_DIR=/path/to/matching/trezor-suite uv run python core/emu.py \
    --executable core/build/artifacts/T3W1/firmware-emu -h -t -P 37904 -q \
    -c uv run pytest tests/device_tests/misc/test_ward_service_channel.py -v
```
