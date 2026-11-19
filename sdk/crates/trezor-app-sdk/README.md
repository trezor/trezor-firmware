# trezor-app-sdk

`trezor-app-sdk` is the `no_std` Rust library for writing Trezor apps:
programs that Trezor Core loads and runs on the device in their own task.
It gives an app access to Core's UI, crypto, host communication (wire) and
logging over a stable, [`stabby`](https://crates.io/crates/stabby)-based ABI,
and provides the app's runtime: the entry point, the global allocator and error
handling.

> ⚠️ Work in progress: the SDK is under active development, and its API can
> change at any time.

## Requirements

- A nightly Rust toolchain. The app entry point uses `extern_item_impls`.
- A `build.rs` that calls `trezor_app_build::link()` from the companion
  `trezor-app-build` crate, which sets up the app's linker script.
- The `trezor-app-tool` cargo subcommand (`cargo app-tool`) to build the app.
  It compiles the app for the target device model and turns the ELF into the
  image format Core loads.

## A Minimal App

`Cargo.toml` declares the SDK, the app's identity and resources, the
features the build selects, and the two profiles `cargo app-tool` builds with:

```toml
cargo-features = ["panic-immediate-abort"]

[package]
name = "hello"
version = "0.1.0"
edition = "2024"

[package.metadata.trezor]
id = "hello.example.com"
name = "Hello"
vendor = "Example"
stack-size = 16384
heap-size = 32768
app-ring = 2
curves = ["secp256k1"]
paths = ["m/44'/1'/account'/change/address_index/**"]

[dependencies]
trezor-app-sdk = "0.1"

[build-dependencies]
anyhow = "1"
trezor-app-build = "0.1"

[features]
model_t3t1 = []
model_t3w1 = []
# one per language the app is translated to
lang_en = []
log_level_error = ["trezor-app-sdk/log_level_error"]
log_level_warn = ["trezor-app-sdk/log_level_warn"]
log_level_info = ["trezor-app-sdk/log_level_info"]
log_level_debug = ["trezor-app-sdk/log_level_debug"]
emulator = []
debug = ["trezor-app-sdk/debug"]
test = ["trezor-app-sdk/test"]
dev_keys = []

[workspace]

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
```

`build.rs`:

```rust,ignore
fn main() -> anyhow::Result<()> {
    trezor_app_build::link()
}
```

`src/main.rs`. Core starts the app for each host request; the app reads the
request, answers it and returns:

```rust,ignore
#![cfg_attr(not(test), no_std)]
#![cfg_attr(not(test), no_main)]

extern crate alloc;

use trezor_app_sdk::{Result, ResultExt, wire_receive};

#[trezor_app_sdk::app]
fn app() -> Result<()> {
    let (id, data) = wire_receive().c()?;
    handle(id, data.as_ref()).c()
}
```

An app has exactly one `#[trezor_app_sdk::app]` function; a missing one is a
compile error.

## Talking to the Host

The SDK does not pick a serializer. An app implements `WireDecode` and
`WireEncode` for its message types on a codec type of its own, for example
with [`prost`](https://crates.io/crates/prost):

```rust,ignore
use trezor_app_sdk::{Error, Result, WireDecode, WireEncode, wire_handler};

struct ProstCodec;

impl<T: prost::Message + Default> WireDecode<T> for ProstCodec {
    fn decode(data: &[u8]) -> Result<T> {
        T::decode(data).map_err(|_| Error::InvalidMessage)
    }
}

impl<T: prost::Message> WireEncode<T> for ProstCodec {
    fn encode(val: &T) -> alloc::vec::Vec<u8> {
        val.encode_to_vec()
    }
}

// `handle_sign_tx(data)` decodes a `SignTx`, calls `sign_tx` and sends its
// result as `MessageType::TxSignature`, or sends the error it returned.
wire_handler!(handle_sign_tx, ProstCodec, SignTx, MessageType::TxSignature, sign_tx);

fn handle(id: u16, data: &[u8]) -> Result<()> {
    match id {
        x if x == MessageType::SignTx as u16 => handle_sign_tx(data),
        _ => Err(Error::InvalidMessage),
    }
}
```

The wire functions at the crate root are:

| Function | Purpose |
| -------- | ------- |
| `wire_receive` | Wait for the next message from the host |
| `wire_send` | Send a message to the host |
| `wire_call` | Send a message and wait for the host's answer, mid-flow |
| `wire_error` | Send an error to the host |
| `wire_request` | Typed `wire_call`; pair request and response types with `wire_request_type!` |

## Modules

| Module | Contents |
| ------ | -------- |
| `modui` | Screens: one typed function per decision an app asks, from a review to a progress bar; a refusal is `Err(Error::Cancelled)` |
| `crypto` | Key derivation and signing (done by Core), plus hashing, HMAC, Base58, signature verification and CoSi (done locally) |
| `log` | The `error!`, `warn!`, `info!` and `debug!` macros |
| `error` | The `Error` and `Result` types, and `ResultExt` for call-site context |
| `util` | Small helpers, such as `Timeout` and `systick_ms` |
| `structs`, `traits` | The types and interfaces shared with Core |
| `mock` | Mock implementations of Core's services (`test` feature) |

## UI

An app names the facts and the steps; Core draws them. `modui` turns one
call into one request, and Core owns the rest: how each kind of fact looks on
each model, the extras menu, the paging, whether a yes is a tap, a hold, or a
deliberate detour, and where the way out sits. The app never picks a style, a
font or a screen.

| Call | Asks the person | Answer |
| ---- | --------------- | ------ |
| `review(step, title, &fields).confirm()` | to read facts and say yes | `Result<()>` |
| `review(…).confirm_strong()` | the same, with a strong yes | `Result<()>` |
| `review(…).confirm_danger()` | to go on with something risky | `Result<()>` |
| `review(…).details()` | to accept the short version, or see the details | `Result<Details>` |
| `summary(step, title).amount(…).fee(…).confirm_strong()` | to sign a transfer: its amount and fee, with the values of core's own summary | `Result<()>` |
| `verify_address(step, address, account, path)` | to check one of their own addresses | `Result<()>` |
| `verify_pubkey(step, pubkey, account, path)` | to check one of their own public keys | `Result<()>` |
| `done(step, text)` | nothing: the flow has ended | — |
| `progress(label, total, work)` | nothing: the app is working | what `work` returns, or the start's error |

Facts are `Field`s, named by what the value *is* rather than by how it
should look: `text`, `amount`, `address`, `data`, `data_source`, `note` and
`warning`; `data` and `data_source` are two ways to hand over the same kind,
so one list may mix all six kinds. A review can also offer extras, each a label
and its own facts, passed as one `.extras(&[Extra::new(label, &fields), ...])`
call; an extra with no facts is not offered, and the menu's room for extras
depends on the answer (see `Review::extras`).

```rust
use trezor_app_sdk::modui::{self, Extra, Field};

fn confirm_send(recipient: &str, amount: &str) -> trezor_app_sdk::Result<()> {
    let account = [Field::text("Account", "TRX #1")];
    modui::review("send", "Send", &[Field::address("Recipient", recipient)])
        .extras(&[Extra::new("Account info", &account)])
        .confirm()?;
    modui::summary("summary", "Send")
        .amount("Amount", amount, "TRX")
        .account("Account info", &account)
        .confirm_strong()
}
```

`data` takes bytes the app already holds. `data_source` takes a `DataSource`
and the total length instead, for bytes the app hands out one range at a time,
hashing them on the way out, say. The bytes come from the app itself, not from
the host; see `DataSource` for how core reads it and why.

A refusal is `Err(Error::Cancelled)`, so `?` ends the flow on it. `details`
answers `Details::Show` when the person picks "Show all", and `Details::Skip`
when they accept without the details. Every call that waits takes a step name relative
to the app; Core prefixes the app's identity, its image ID, so `"send"` reaches
the host as `"tron.trezor.com/send"` in the `ButtonRequest`.

See the [`modui` rustdoc](src/modui/mod.rs) for the full contract: layouts,
facts, extras, long content and progress.

## Logging

Values passed to the log macros must implement `ufmt::uDebug`; for a `String`,
log `s.as_str()`:

```rust,ignore
use trezor_app_sdk::{debug, info};

info!("Application started");
debug!("Address: {}", address.as_str());
```

The log level is chosen at build time with one of the `log_level_*` features
(`cargo app-tool build --log-level <level>` sets it). Each level includes the
ones above it, and lower levels are compiled out. Without any of them, all log
output is compiled out.

## Features

| Feature | Effect |
| ------- | ------ |
| `app` (default) | Everything an app needs. Without it, only `structs` and `traits` are available, for code that shares the ABI types with apps |
| `nightly` (default) | Nightly-only language features used by the panic and abort machinery |
| `log_level_error` / `_warn` / `_info` / `_debug` | Compile in log output up to that level |
| `debug` | Error context chains via `ResultExt` and file/line panic messages, at the cost of binary size |
| `test` | Mock implementations of Core's services, for host-side unit tests (implies `app`) |

## Unit Tests

With the `test` feature, the SDK runs on the host with mocked Core services.
Call `trezor_app_sdk::mock::sdk_init()` at the start of a test that uses
SDK functions backed by Core.

## License

GPL-3.0-only.
