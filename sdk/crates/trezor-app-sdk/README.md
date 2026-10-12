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
| `modui` | Screens: confirmations, notices and progress, one function per layout; backing out is `Err(Error::Cancelled)` |
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
