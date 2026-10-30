# Trezor App SDK

`trezor-app-sdk` is the `no_std` Rust library that Trezor modular apps
("extapps") link against. It gives an app access to Trezor Core's UI, crypto,
wire and logging services over a stable, `stabby`-based ABI, and provides the
app's runtime: the `applet_main` entry point, the global allocator and error
handling.

> ⚠️ Work in progress: the SDK is under active development, and its API can
> change at any time.

For building, testing and debugging an app, see the SDK documentation in
[`sdk/doc/`](../../doc/README.md). The [`tron`](../../apps/tron) app is the
working reference.

## Modules

| Module | Contents |
| ------ | -------- |
| `modui` | Screens: one typed function per decision an app asks, from a review to a progress bar; a refusal is `Err(Error::Cancelled)` |
| `crypto` | Key derivation and signing (done by Core), plus hashing, HMAC, Base58, signature verification and CoSi (done locally) |
| `log` | The `error!`, `warn!`, `info!` and `debug!` macros |
| `error` | The SDK's `Error` and `Result` types, and `ResultExt` for call-site context |
| `structs`, `traits` | The types and interfaces shared with Core |

The wire functions (`wire_receive_wire_start`, `wire_request`, ...) and the
`wire_handler!` macro are exported at the crate root.

## Entry Point

An app exports an `app()` function. The SDK's `applet_main` calls it once the
runtime is set up, and the app loops over host requests:

```rust
#[unsafe(no_mangle)]
pub fn app() -> Result<()> {
    loop {
        let (id, data) = wire_receive_wire_start().c()?;
        handle_wire_message(id as i32, &data).c()?;
    }
}
```

See [App Entry Point](../../doc/development.md#app-entry-point) for how
`handle_wire_message` dispatches and answers requests.

## UI

An app names the facts and the steps; Core draws them. `modui` turns one
call into one request, and Core owns the rest: how each kind of fact looks on
each model, the extras menu, the paging, whether a yes is a tap, a hold, or a
deliberate detour, and where the way out sits. The app never picks a style, a
font or a screen.

| Call | Asks the person | Answer |
| ---- | --------------- | ------ |
| `review(step, title, &fields).confirm()` | to read facts and say yes | `Result<()>` |
| `review(…).confirm_final()` | the same, as the last yes before signing | `Result<()>` |
| `review(…).confirm_danger()` | to go on with something risky | `Result<()>` |
| `details(step, title, &fields)` | whether to see the details | `Result<Details>` |
| `verify_address(step, address, account, path)` | to check one of their own addresses | `Result<()>` |
| `verify_pubkey(step, pubkey, account, path)` | to check one of their own public keys | `Result<()>` |
| `done(step, text)` | nothing: the flow has ended | — |
| `progress(label, total, work)` | nothing: the app is working | what `work` returns |

Facts are `Field`s, named by what the value *is* rather than by how it
should look: `text`, `amount`, `address`, `data`, `data_source`, `note` and
`warning`. One list may mix all seven. A review can also offer extras, each a
label and its own facts, passed as one
`.extras(&[Extra::new(label, &fields), ...])` call; an extra with no facts is
not offered.

```rust
use trezor_app_sdk::modui::{self, Extra, Field};

fn confirm_send(recipient: &str, amount: &str) -> trezor_app_sdk::Result<()> {
    let account = [Field::text("Account", "TRX #1")];
    modui::review("send", "Send", &[Field::address("Recipient", recipient)])
        .extras(&[Extra::new("Account info", &account)])
        .confirm()?;
    modui::review("summary", "Send", &[Field::amount("Amount", amount, "TRX")])
        .confirm_final()
}
```

`data` takes bytes the app already holds. `data_source` takes a `DataSource`
and the total length instead, for bytes the app hands out one range at a time —
a host stream it hashes on the way out, say. Core reads the source in order,
from the start, each range once, and stops when the person reaches the end or
refuses; a source whose read fails ends the review as refused, and the app gets
that source's own error back rather than `Cancelled`. A `data_source` field may
not sit in an extra, because an extra can be opened again and its bytes would be
read again.

A refusal is `Err(Error::Cancelled)`, so `?` ends the flow on it. A `details`
answers `Details::Show` when the person wants the details, and `Details::Skip`
when they accept without them. Every call that waits takes a step name relative
to the app; Core prefixes the app's identity, its image ID, so `"send"` reaches
the host as `"tron.trezor.com/send"` in the `ButtonRequest`.

See the [`modui` rustdoc](src/modui/mod.rs) for the full contract: layouts,
facts, extras, long content and progress.

## Logging

Values passed to the log macros must implement `ufmt::uDebug`:

```rust
use trezor_app_sdk::{debug, error, info, warn};

info!("Application started");
debug!("Value: {}", value.as_str());
```

The log level is chosen at build time with `cargo app-tool build --log-level
<level>`; lower levels are compiled out. See
[Logging](../../doc/logging.md).

## Features

| Feature | Effect |
| ------- | ------ |
| `app` (default) | Everything an app needs. Core builds without it and only uses `structs` and `traits` |
| `nightly` (default) | Nightly-only items, used together with `debug` |
| `log_level_error` / `_warn` / `_info` / `_debug` | Compile in log output up to that level |
| `debug` | Error context chains via `ResultExt` and file/line panic messages, at the cost of binary size |
| `test` | Mock implementations of Core's services, for host-side unit tests |

When an app is built with `cargo app-tool`, these are set from its command-line
flags; see [Cargo Features](../../doc/development.md#cargo-features).
