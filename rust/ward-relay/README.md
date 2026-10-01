# ward-relay

The Rust binding of the **wardd relay**: it carries a WARD conversation between `wardd`, the local
WARD service, and a Trezor on the session a Rust host already holds. wardd holds all of the WARD
logic: the replica (in Evolu), the WM, and the order of every sync, catch-up and flush. This crate
holds none of it. It implements the same contract as the Connect, Python
(`trezorlib.ward_relay`) and Java bindings: `packages/ward-core/relay.md` in trezor-suite,
version 1.x.

## Using it

1. **Implement `WardPipe` on your transport.** Put a message, named and with a JSON body (bytes as
   hex), on the device and return what it answered. Handle button requests, PIN and passphrase as
   you always do. Return WARD pulls (`WardEntryRequest`, `WardChainRequest`) unanswered, because
   they belong to wardd's conversation.
2. **Connect and pick the wallet:** `WarddClient::connect(url, token)`, then `open_store`.
3. **Run the operation:** `sync`, `flush` or `status`. Each one is a single conversation on a single
   session.

## The `codec` feature

The `codec` feature supplies a ready pipe. It encodes messages by name from the firmware's own
`common/protob/*.proto`, parsed at build time with pure Rust (no `protoc`). It frames them as codec
v1 over any `FrameIo`, with a UDP transport for the emulator:

```text
cargo run --features codec --example emulator -- sync|flush|status [--batch N] [--rejoin]
```

**THP devices (T3W1):** these need the host's own THP channel. Write the pipe on that channel and
reuse `codec::encode` / `codec::decode` for the bodies.

## Hosts

- **BHWI:** implement `WardPipe` on its Trezor transport. If the transport only offers typed calls,
  it needs a raw-frame hook: a type id and bytes, which is what `codec::encode` produces.
- **async-hwi:** it has no Trezor backend yet, so one has to be contributed first. `WardPipe` then
  sits behind a `ward` feature there.

## Tests

`cargo test --features codec` runs against a scripted wardd. Set `WARDD_SUITE_DIR` to the
trezor-suite checkout to also run against the real wardd.
