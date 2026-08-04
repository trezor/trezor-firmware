# Modular App Development

A modular app is a `no_std` binary — it does not link the standard library — but it does use `alloc` for heap-allocated types like `String` and `Vec`, backed by the heap described [below](#heap-size).

## Example App

[`trezor-modular-app`](https://github.com/bieleluk/trezor-modular-app) (branch `bieleluk/build-system`) is intended to be the default example — a minimal, working modular app ("Funnycoin") that exercises every piece described below. It is not ready yet, though, so for now it's better to use the in-repo [`tron`](../apps/tron) app under `sdk/apps` as the functional reference, and create your new app alongside it in the same workspace. The rest of this document walks through the example's parts one by one, starting with the `Cargo.toml` metadata.

## App Metadata

Every modular app must declare its metadata in `Cargo.toml` under `[package.metadata.trezor]`:

```toml
[package.metadata.trezor]
id = "tron.trezor.com"
name = "Tron"
vendor = "SatoshiLabs"
stack-size = 16384
heap-size = 8192
app-ring = 2
curves = ["secp256k1"]
paths = [
    # BIP-44 for basic (legacy) Bitcoin accounts, and widely used for other currencies:
    # https://github.com/bitcoin/bips/blob/master/bip-0044.mediawiki
    "m/44'/coin_type'/account'/change/address_index/**",
]
slip44-id = 195
```

| Field | Description |
| ------- | ------------- |
| `id` | Unique reverse-domain identifier of the app |
| `name` | Human-readable app name shown in the UI |
| `vendor` | App vendor name |
| `stack-size` | Stack memory allocated for the app in bytes |
| `heap-size` | Heap memory allocated for the app in bytes |
| `app-ring` | Privilege ring level; `0` is the most privileged |
| `curves` | List of elliptic curves the app is permitted to use |
| `paths` | Allowed BIP32 derivation path patterns (see below) |
| `slip44-id` | [SLIP-44](https://github.com/satoshilabs/slips/blob/master/slip-0044.md) coin type identifier |

### Stack size

`stack-size` is the minimum stack space, in bytes, reserved for the app. It is capped at 256 KiB and is embedded in the app binary header at build time.

At load time, Core checks that the app's RAM arena is large enough to hold the read-write segment, the stack, and the heap together. If it isn't, the app is rejected outright and never runs — there is no partial or degraded startup.

### Heap Size

`heap-size` is the minimum heap space, in bytes, reserved for the app's allocator, also capped at 256 KiB. Like `stack-size`, it's counted against the app's RAM arena at load time, and loading fails if the arena can't fit `rw-size + stack-size + heap-size`.

The exact amount of heap the app receives depends on the target:

- On real hardware, the kernel reserves exactly `heap-size` bytes (rounded up for alignment) for the app in the RAM arena — no more, no less.
- On the Unix emulator, the app instead receives *all* remaining arena memory, regardless of `heap-size`.

> ⚠️ Today the SDK's Rust global allocator does not actually consume that kernel-reserved region — `applet_main` hardcodes a fixed 16 KiB heap in the app's own static memory, independent of `heap-size`. Until this is wired up, treat `heap-size` as reserving kernel-side RAM for the app rather than sizing the allocator you actually get.

### Application privilege

`app-ring` selects which of three trust rings the app is loaded into:

| Ring | Trust level | Status |
| ------ | ------------- | -------- |
| `0` | Most trusted | Not implemented yet |
| `1` | Privileged | Not implemented yet |
| `2` | Least trusted — normal apps | Available; UI and Crypto services are provided |

Each ring has its own root of trust: an app is only allowed to run if it proves membership (via a Merkle proof) in a signed "root packet" published for its ring. Core recomputes the Merkle root from the app's header and proof and compares it against the ring's expected root before starting the app.

Ring `2` is available today and follows the normal app review process. Rings `0` and `1` are intended to grant extra capabilities — for example, access to a public key scoped to a specific derivation path — but that functionality does not exist yet. If your app genuinely needs privileged access, contact us with your reasoning before building against it.

### Curves

`curves` lists the elliptic curves the app is permitted to use for key derivation and signing. The recognized values are:

- `secp256k1`
- `nist256p1`
- `ed25519`
- `curve25519`
- `bip340`

The list is packed into the app binary as null-terminated strings, capped at 64 bytes total. It's enforced at runtime by Core when the app calls into the `Crypto` service: a request for a curve not on the list is rejected.

> ⚠️ Today exactly **one** curve must be declared — even though `curves` is an array, Core currently requires `len(curves) == 1` and refuses to load apps that declare more or fewer.

### Derivation Path Patterns and slip44 id

The `paths` field restricts which BIP32 paths the app may derive keys for. It takes one or more pattern strings; the following are commonly used:

| Pattern | Description |
| --------- | ------------- |
| `m/44'/coin_type'/0'/0/account` | BIP-44 for account-based currencies (e.g. ETH) |
| `m/44'/coin_type'/account'/change/address_index/**` | BIP-44 for UTXO-based currencies |
| `m/44'/coin_type'/account'` | SEP-0005 for non-UTXO currencies (Stellar, etc.) |
| `m/44'/coin_type'/0'/account` | SEP-0005 Ledger Live legacy path |
| `m/45'/coin_type/account/change/address_index` | CASA multisig path |

`slip44-id` is a single [SLIP-44](https://github.com/satoshilabs/slips/blob/master/slip-0044.md) coin type integer. At runtime, Core substitutes it for every `coin_type` placeholder across all of the app's `paths` patterns before matching an incoming request — so one `slip44-id` applies uniformly to every pattern the app declares.

> Note: `paths` and `slip44-id` are two separate fields today, but this is expected to change — a future revision will likely fold them into a single field (e.g. patterns with the coin type baked in directly) rather than keeping two values that have to stay in sync.

### App Dependencies

A modular app depends on two crates: `trezor-app-sdk`, the runtime library linked into the app, and `modular-xtask`, the build tool used to compile and package it. Both are currently consumed as local, relative-path dependencies out of a `trezor-firmware` checkout; once the SDK is published, they'll move to versioned crates.io dependencies instead.

#### trezor-app-sdk

The app depends on the SDK itself, declared like any other crate dependency:

```toml
[dependencies]
trezor-app-sdk = { path = "../trezor-firmware/sdk/crates/trezor-app-sdk" }
```

> For now, `trezor-app-sdk` is pulled in via a relative path into a local `trezor-firmware` checkout. Once the SDK is published, this will become a version pin against `trezor-app-sdk` on [crates.io](https://crates.io/) instead.

#### modular-xtask

Building and running the app is driven by `modular-xtask`, a `cargo` subcommand aliased in `.cargo/config.toml`:

```toml
[alias]
xtask = "run --manifest-path ../trezor-firmware/sdk/crates/modular-xtask/Cargo.toml --"
```

> Same story as `trezor-app-sdk`: `modular-xtask` is invoked via a relative path into a local `trezor-firmware` checkout for now, and will move to crates.io once it's published.

It's technically possible to build the app with plain `cargo build` instead, but this is highly discouraged: `xtask` is what turns the compiled ELF into the app binary format Core actually loads — packing the header, relocation tables, and `[package.metadata.trezor]` fields — and a raw `cargo build` output skips all of that.

### Cargo Features

Assuming `modular-xtask` is used to build the app (see above), the app's `[features]` are not set by hand — `xtask` derives them from its own CLI flags:

```toml
[features]
# --------------------------------------------------------------------------
# Model features
# --------------------------------------------------------------------------
model_t3t1 = []
model_t3w1 = []

# --------------------------------------------------------------------------
# Language features
# --------------------------------------------------------------------------
lang_en = []
lang_cs = []

# --------------------------------------------------------------------------
# Log level features
# --------------------------------------------------------------------------
log_level_error = ['trezor-app-sdk/log_level_error']
log_level_warn = ['trezor-app-sdk/log_level_warn']
log_level_info = ['trezor-app-sdk/log_level_info']
log_level_debug = ['trezor-app-sdk/log_level_debug']

# --------------------------------------------------------------------------
# Selectable features
# --------------------------------------------------------------------------
emulator = []
test = ["dev_keys", 'trezor-app-sdk/test', 'trezor-app-sdk/log_level_debug']
debug = ['trezor-app-sdk/debug']

# --------------------------------------------------------------------------
# Automatically derived features (do not enable from outside)
# --------------------------------------------------------------------------
dev_keys = []
```

| Flag | Feature enabled |
| ------ | ------------------ |
| `-m`/`--model <t3t1\|t3w1>` | `model_t3t1` / `model_t3w1` — which model the app is built for |
| `--lang <en\|cs>` | `lang_en` / `lang_cs` — same idea, for the app's language |
| `--log-level <error\|warn\|info\|debug>` | `log_level_error` / `log_level_warn` / `log_level_info` / `log_level_debug` |
| `-e`/`--emulator` | `emulator` — builds for a different target triple (the host, instead of the hardware `thumbv8m.main-none-eabihf` target) |
| `-d`/`--debug` | `debug` — forwarded into `trezor-app-sdk`; enables backtraces and debug info for app errors, which makes debugging possible but significantly bloats the binary size |
| `xtask unit-tests` | `test` — forwarded into `trezor-app-sdk` for unit tests, along with the `debug` feature and the highest log level (`log_level_debug`) |

### Cargo Profiles

`xtask` also hardcodes which Cargo profile it builds with, so the app's `Cargo.toml` (or the workspace's, if the app is a workspace member) must define profiles under these exact names:

```toml
[profile.debug-fw]
inherits = "dev"
split-debuginfo = "off"
debug = 2
strip = "none"
panic = "abort"

[profile.release-fw]
inherits = "release"
opt-level = "z"
lto = "fat"
codegen-units = 1
split-debuginfo = "off"
debug = 0
debug-assertions = false
overflow-checks = false
incremental = false
panic = "immediate-abort"

[profile.test]
split-debuginfo = "off"
debug = 2
```

| Profile | Used when |
| --------- | ----------- |
| `debug-fw` | `-d`/`--debug` is passed to `xtask build` |
| `release-fw` | `xtask build` is run without `-d`/`--debug` |
| `test` | `xtask unit-tests` runs the app's test suite |

`debug-fw` and `release-fw` are passed to `cargo` via `--profile`, so they must exist under exactly those names — `xtask` does not let you pick a different profile name for a debug or release build. `test` is cargo's built-in profile used for `cargo test`; it's overridden here mainly to disable `split-debuginfo`.

---

## Allocation

Unit tests build the app with `#[cfg(not(test))]` off, i.e. `std` available, since `xtask unit-tests` runs on the host rather than under `no_std`/`no_main` (see the [`test`](#cargo-features) feature). This means allocated types like `String` and `Vec` have to come from `alloc` in a normal build but from `std` when compiled for tests — the two aren't interchangeable at the type level, so app code can't just `use alloc::string::String` unconditionally and expect it to also compile for tests.

The common fix is a small `alloc_types` module that re-exports the right path for each configuration, so the rest of the app imports from one place regardless of build mode:

```rust
#[cfg(not(test))]
pub(crate) use alloc::{
    string::{String, ToString},
    vec,
    vec::Vec,
};
#[cfg(test)]
pub(crate) use std::{
    string::{String, ToString},
    vec,
    vec::Vec,
};
```

---

## App Entry Point

Every app must export an `app()` function as its entry point:

```rust
#[unsafe(no_mangle)]
pub fn app() -> Result<()> {
    loop {
        let (id, data) = wire_receive_wire_start().c()?;
        handle_wire_message(id as i32, &data).c()?
    }
}
```

The function runs an infinite loop that drives the app's message handling:

1. **Wait** — `wire_receive_wire_start()` blocks until Trezor Core sends a `WireStart` message carrying a new protobuf request from the host. Anything else received on that service is rejected with `Error::InvalidMessage`.
2. **Handle** — `handle_wire_message()` is called to process the request.

This runs indefinitely, for the lifetime of the app — the loop has no exit condition of its own. The only way out is `handle_wire_message()` returning an `Err` (via `.c()?`), which unwinds `app()` and terminates the app.

Because returning `Err` here is fatal, `handle_wire_message()` must only do so for irreversible problems — e.g. the IPC channel itself failing. Anything the host can recover from (a malformed request, a business-logic failure such as a bad derivation path) is a **non-critical error**: it must be caught and reported back to Core over the `WireError` service instead, so `handle_wire_message()` returns `Ok(())` and the loop continues waiting for the next request.

### Wire Message Handling

When a `WireStart` message is received, `handle_wire_message()` is responsible for:

1. **Dispatching** to the appropriate handler function based on the message type, generated per-message by the `wire_handler!` macro.
2. **Deserializing** the incoming protobuf payload from the message data.
3. **Responding** — the result is serialized and sent back to Core:
   - On success → response is sent via the `WireEnd` service.
   - On non-critical error (including a deserialization failure) → the error is sent via the `WireError` service, and `handle_wire_message()` still returns `Ok(())`.

A message type that isn't recognized, or a failure while sending the `WireEnd`/`WireError` response itself, is treated as irreversible: `handle_wire_message()` returns `Err`, which — per above — terminates the app.

```sh
Host  ──WireStart──►  app()
                        │
                   deserialize
                        │
                   handler fn
                        │
              ┌─────────┴─────────┐
           response              error
              │                   │
          serialize           serialize
              │                   │
         WireEnd            WireError
              │                   │
Host  ◄───────┴───────────────────┘
```

### Protobuf Messages

Requests and responses exchanged with the host are plain protobuf messages, defined in a `protob/` directory alongside the app:

- `messages.proto` declares the `MessageType` enum — the wire identifier for every message that can travel over `WireStart`/`WireEnd` directly. Only top-level requests and their responses get an entry here (e.g. `GetPublicKey` / `PublicKey`); helper or inner message types that only ever appear *embedded inside* another message (e.g. `HDNodeType`, or the `Success`/`Failure`/`ButtonRequest` types shared across apps) are not listed — they have no wire identifier of their own.
- The app's own `.proto` file (e.g. `funnycoin.proto`) defines the actual request/response message bodies, importing shared helper types from `common.proto`.

`wire_handler!` (see [Wire Message Handling](#wire-message-handling)) doesn't hardcode how these messages are encoded — it works against any codec type that implements the SDK's `WireDecode`/`WireEncode` traits:

```rust
trait WireDecode<T> {
    fn decode(data: &[u8]) -> Result<T>;
}
trait WireEncode<T> {
    fn encode(val: &T) -> Vec<u8>;
}
```

Every app today implements these using [`prost`](https://docs.rs/prost). Messages are compiled to Rust in `build.rs`:

```rust
// build.rs
fn build_protobufs() {
    let mut config = prost_build::Config::new();
    config
        .compile_protos(
            &["protob/common.proto", "protob/funnycoin.proto", "protob/messages.proto"],
            &["protob/"],
        )
        .expect("Failed to compile protobufs");
}
```

`prost-build` (a build-dependency) generates the Rust structs for every message at build time; the app depends on `prost` itself (with default features off, for `no_std`) to encode/decode them via a small codec type (`ProstCodec`) implementing `WireDecode`/`WireEncode` on top of `Message::decode`/`encode_to_vec()`. The generated code lands in `OUT_DIR` and is pulled into the crate with `include!`, one module per `.proto` package.

In `handle_wire_message()`, the incoming message's numeric ID is matched against `MessageType` to find which request it is, the payload bytes are decoded into the corresponding request struct via the codec, and the handler's return value is encoded back to bytes the same way before being sent out via `WireEnd`/`WireError` — the deserialize/dispatch/respond steps from the diagram above.

### Translations

> ⚠️ This part of the setup is still in flux and likely to change.

UI strings aren't hardcoded — they're pulled from the same JSON translation files (`en.json`, `cs.json`, ...) that Trezor Core itself uses, keyed by string like `"words__title_done"` and (for strings that vary by layout) by model layout name (`Eckhart`, `Delizia`, ...) within each key.

`build.rs` picks the JSON file matching the `lang_*` feature and the layout matching the `model_*` feature (see [Cargo Features](#cargo-features)), and turns it into a `tr!` macro — one arm per translation key, expanding to that key's resolved string literal — written to `OUT_DIR` and pulled into the crate with `include!`, the same way generated protobuf code is. An unknown key is a compile error rather than a runtime lookup failure.

```rust
tr!("words__title_done")   // => "Done" (or whatever the active lang/layout resolves to)
```

## Services

While handling a wire message, the app can call into other Core services via IPC:

| Service | Description |
| --------- | ------------- |
| `UI` | Display screens, request user confirmation, show progress |
| `Progress` | Report progress of long-running operations |
| `WireContinue` | Request additional data chunks from the host when the payload is too large to fit in a single message |
| `Crypto` | Seed-based cryptographic operations (key derivation, signing) |
| `CryptoDirect` | Cryptographic functions that do **not** access the seed (hashing, encoding, etc.) |

These calls are synchronous — the app blocks until Core responds.

Which services an app may use is a function of its [`app-ring`](#application-privilege). Ring `2` — the only ring available today — gets `UI` and the seed-based `Crypto` service, matching the `[package.metadata.trezor]` table above. Privileged rings are meant to unlock additional services beyond this table, but since ring 0/1 support isn't implemented yet, every app that can currently load runs at ring `2` and sees the full service set listed here.

---

## App Lifecycle

The real entry point of every modular app is `applet_main`, provided by the SDK. The user-defined `app()` function is called only after the SDK has fully initialized the environment. The initialization sequence is strictly ordered — functionality is not available before its initialization step completes.

### Initialization Sequence

#### 1. API Version Check

The SDK verifies that the API version required by the app is available on the running firmware. If the version is not supported, the app crashes immediately. This check is handled automatically by `trezorlib` — no user code is needed.

> ⚠️ No SDK functionality is available before this point.

#### 2. IPC Buffer Initialization

The IPC buffer used for communication with Trezor Core is set up. Its size is configured via the `static_service!` macro and must be large enough to hold the largest message the app sends to Core.

> ⚠️ No communication with Core (UI, Crypto, WireContinue, etc.) is available before this point.

#### 3. Heap Initialization

The heap allocator is initialized with the memory region defined by `heap-size` in `Cargo.toml`. The default heap is 16 KiB.

> ⚠️ No allocated types (`Box`, `Vec`, `String`, etc.) can be used before this point.

#### 4. User App

The user-defined `app()` function is called. From this point, the full SDK is available.

### Termination

`applet_main()` reacts to `app()`'s result:

- **`Ok(())`** — exits cleanly via `system_exit()`. A conforming app never actually takes this branch, though: as covered in [App Entry Point](#app-entry-point), `app()`'s loop has no exit condition of its own, so it has no way to produce `Ok(())`. This arm exists as `applet_main`'s general contract, not something `app()` is expected to hit.
- **`Err(e)`** — the error type, code, and message are logged, and the app exits with `system_exit_error()`, reporting the failure to Core. This is the only way `app()` is expected to return, and only for an irreversible issue.

### Sequence Diagram

```sh
applet_main()
    │
    ├─ 1. init API version
    │       └─ incompatible → crash (handled by trezorlib)
    │
    ├─ 2. init IPC buffer (CORE_SERVICE)
    │       └─ no Core communication before this
    │
    ├─ 3. init heap (HEAP)
    │       └─ no alloc types before this
    │
    └─ 4. call app()  (loops forever; never returns Ok)
            │
            ├─ Ok(())   → system_exit()            [unreachable in practice]
            └─ Err(e)   → log error → system_exit_error()  [irreversible issue]
```
