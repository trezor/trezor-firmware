# Trezor App SDK

The SDK for Trezor apps written in Rust: `no_std`, one crate.

## Modules

```
trezor-app-sdk/
├── modui   - UI building blocks (confirm::value, notice::show, progress::run, ...)
├── crypto  - hashing, HMAC, signing, base58
├── log     - error!/warn!/info!/debug!, filtered at compile time
└── wire    - wire_handler! and friends: the host's requests in, replies out
```

## Writing an app

The SDK provides the entry point and calls the app's `app()`:

```rust
use trezor_app_sdk::modui::{Commitment, confirm, notice};
use trezor_app_sdk::{Error, Result, info};

#[unsafe(no_mangle)]
pub fn app() -> Result<()> {
    let params = confirm::Action::new(
        "Title", "Confirm?", None, None, Commitment::Step, "app/confirm", &[],
    );
    match confirm::action(params) {
        Ok(()) => {}
        Err(Error::Cancelled) => {
            info!("Cancelled");
            return Ok(());
        }
        Err(e) => return Err(e),
    }
    notice::show(notice::Notice::new(
        notice::Severity::Done, "Done", "All set", "app/done", &[], false,
    ))
}
```

A real app loops on the host's requests; see `sdk/apps/tron/src/main.rs`.

## `modui`

Confirmations and notices return `Result<()>`; the person backing out is
`Err(Error::Cancelled)`, so `?` stops the flow on it.

- `confirm::action(params)` - confirm an action
- `confirm::value(params)` - confirm one value (address, amount, ...)
- `confirm::data(params)` - confirm raw bytes, shown as hex
- `confirm::properties(params)` - confirm a key-value list
- `confirm::summary(params)` - confirm amount and fee
- `notice::show(params)` - tell the person something (info, warning, done, ...)
- `progress::run(label, total, work)` - show progress while `work` runs

The module docs (`cargo doc`) are the full reference.

## Log levels

Pick one Cargo feature: `log_level_error`, `log_level_warn`, `log_level_info`
or `log_level_debug`; each includes the levels above it. Without one, logging
compiles out. `cargo xtask build --log-level info` sets it for you.

## License

See parent LICENSE
